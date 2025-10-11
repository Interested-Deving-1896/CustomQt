from __future__ import annotations

from PySide6.QtCore import QTimer, QByteArray, QPoint
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt

import sys
import ctypes
from ctypes import wintypes
from typing import Callable, Optional, Tuple, cast, Union

from . import constants
import time

class WindowsStyler:
    def __init__(
        self,
        window: QWidget,
        hittest_callback: Optional[Callable[[QPoint], Optional[Tuple[bool, int]]]] = None,
        border_width: int = 8,
        titlebar_fallback: bool = True,
        titlebar_fallback_height: int = 30,
        round_corner_radius: int = 15
    ) -> None:
        # Only allow usage on Windows platform
        if sys.platform != 'win32':
            raise RuntimeError('WindowsStyler can only be used on Windows.')
        
        self.window: QWidget = window
        # Store original nativeEvent handler for fallback
        self._orig_native: Callable[[QByteArray, int], Tuple[bool, int]] = cast(Callable[[QByteArray, int], Tuple[bool, int]], window.nativeEvent)

        # Optional custom titlebar hit-test hook
        self._titlebar_hook: Optional[
            Callable[[QPoint], Optional[Tuple[bool, int]]]
        ] = hittest_callback
        self.hwnd: Optional[int] = None

        # Window style parameters
        self.BORDER_WIDTH = border_width
        self.TITLE_BAR_FALLBACK_HEIGHT = titlebar_fallback_height
        self.TITLE_BAR_FALLBACK = titlebar_fallback
        self.ROUND_CORNER_RADIUS = round_corner_radius

        # Maximize button reference for state updates
        self._titlebar_maximize_button: Optional[QPushButton] = None
        
        # Debounce timer for corner application
        self._corner_timer: Optional[QTimer] = None
        self._last_corner_apply = 0.0
        
        # Track if running on Windows 11 for API compatibility
        self._is_windows_11 = self._check_windows_11()
        
        # Track cursor state for maximize button
        self._original_cursor = None
        
        # Set initial window flags for frameless style
        self._setWindowFlags()

    def _check_windows_11(self) -> bool:
        """Check if running on Windows 11 or later."""
        try:
            version = sys.getwindowsversion()
            # Windows 11 is build 22000 or higher
            return version.major >= 10 and version.build >= 22000
        except Exception:
            return False

    def init(self) -> None:
        """Call this after window is created but before showing it."""
        if sys.platform != "win32":
            return
        # Schedule post-init setup after event loop starts
        QTimer.singleShot(0, self._post_init)
        
    def _setWindowFlags(self) -> None:
        # Set frameless window with system menu buttons
        # Type annotation to fix pylance warning
        flags = cast(Qt.WindowType, ( #type: ignore
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        ))
        self.window.setWindowFlags(flags) #type: ignore

    def _post_init(self) -> None:
        """Setup native window handle and monkey-patch nativeEvent."""
        self.hwnd = int(self.window.winId())
        
        # Validate hwnd before proceeding
        if not self.hwnd:
            raise RuntimeError("Failed to get valid window handle")
            
        # Monkey patch nativeEvent and state functions for custom handling
        setattr(self.window, "nativeEvent", self.nativeEvent)
        setattr(self.window, "showMaximized", self.showMaximized)
        setattr(self.window, "showNormal", self.showNormal)
        setattr(self.window, "isMaximized", self.isMaximized)

        # Apply Win32 frame styles and effects
        self.setup_win32_frame()
        self._debounced_apply_corners()
        self.enable_acrylic_blur()
        

    def setup_win32_frame(self) -> None:
        """Set window styles and disable default DWM non-client rendering."""
        if not self.hwnd:
            return
            
        # Modify window style to enable resizing and disable caption
        style: int = constants.Windows.user32.GetWindowLongW(self.hwnd, constants.Windows.GWL_STYLE)
        style |= constants.Windows.WS_THICKFRAME
        style &= ~constants.Windows.WS_CAPTION
        constants.Windows.user32.SetWindowLongW(self.hwnd, constants.Windows.GWL_STYLE, style)
        # Notify Windows that frame has changed
        constants.Windows.user32.SetWindowPos(
            self.hwnd,
            0,
            0,
            0,
            0,
            0,
            constants.Windows.SWP_NOMOVE | constants.Windows.SWP_NOSIZE | constants.Windows.SWP_FRAMECHANGED,
        )
        # Disable DWM non-client rendering for custom frame
        constants.Windows.dwmapi.DwmSetWindowAttribute(
            self.hwnd,
            constants.Windows.DWMWA_NCRENDERING_POLICY,
            ctypes.byref(ctypes.c_int(constants.Windows.DWMNCRP_DISABLED)),
            ctypes.sizeof(ctypes.c_int),
        )

    def nativeEvent(
        self, eventType: Union[QByteArray, bytes, bytearray], message: int
    ) -> Tuple[bool, int]:
        """
        Custom native event handler intercepting Windows messages.
        """
        if eventType == b"windows_generic_MSG":
            msg: wintypes.MSG = wintypes.MSG.from_address(int(message))
            
            # Block default non-client painting and activation
            if msg.message in (constants.Windows.WM_NCPAINT, constants.Windows.WM_NCACTIVATE):
                return True, 0

            # Handle cursor changes for maximize button
            if msg.message == constants.Windows.WM_SETCURSOR:
                ht = int(msg.lParam) & 0xFFFF
                if ht == constants.Windows.HTMAXBUTTON:
                    # Set hand cursor when hovering maximize button
                    if not self._original_cursor:
                        self._original_cursor = constants.Windows.user32.GetCursor()
                    hcur = constants.Windows.user32.LoadCursorW(0, constants.Windows.IDC_HAND)
                    if hcur:
                        constants.Windows.user32.SetCursor(hcur)
                        return True, 1
                else:
                    # Restore original cursor when not on maximize button
                    if self._original_cursor:
                        constants.Windows.user32.SetCursor(self._original_cursor)
                        self._original_cursor = None
            
            # Block default non-client calculations and painting
            if msg.message in (constants.Windows.WM_NCCALCSIZE, constants.Windows.WM_NCPAINT, constants.Windows.WM_NCACTIVATE):
                return True, 0

            # Handle maximize button mouse events
            if msg.message in (constants.Windows.WM_NCLBUTTONDOWN, constants.Windows.WM_NCLBUTTONUP, constants.Windows.WM_NCLBUTTONDBLCLK):
                try:
                    ht = int(msg.wParam)
                except (ValueError, OverflowError):
                    ht = None

                if ht == constants.Windows.HTMAXBUTTON:
                    if msg.message == constants.Windows.WM_NCLBUTTONDOWN:
                        # Block default maximize button press
                        return True, 0
                    if msg.message in (constants.Windows.WM_NCLBUTTONUP, constants.Windows.WM_NCLBUTTONDBLCLK):
                        # Toggle maximized state on button release/double-click
                        old_maximized = self.isMaximized()
                        if old_maximized:
                            constants.Windows.user32.ShowWindow(self.hwnd, constants.Windows.SW_RESTORE)
                        else:
                            constants.Windows.user32.ShowWindow(self.hwnd, constants.Windows.SW_MAXIMIZE)
                        
                        # Update maximize button appearance
                        self._update_maximize_button_state(not old_maximized)
                        self._debounced_apply_corners()
                        return True, 0
            
            # Enforce minimum/maximum window sizing
            if msg.message == constants.Windows.WM_GETMINMAXINFO:
                return self._handle_getminmax(msg)
            
            # Custom hit-testing for resize/drag
            elif msg.message == constants.Windows.WM_NCHITTEST:
                return self._handle_hittest()

            # Schedule rounded corners update on resize/move/snap/DPI change
            elif msg.message in (
                constants.Windows.WM_SIZE,
                constants.Windows.WM_WINDOWPOSCHANGED,
                constants.Windows.WM_EXITSIZEMOVE,
                constants.Windows.WM_DPICHANGED,
            ):
                self._debounced_apply_corners()

        # Fallback to original handler if not handled
        return cast(Tuple[bool, int], self._orig_native(eventType, message)) #type: ignore

    def _handle_getminmax(self, msg: wintypes.MSG) -> Tuple[bool, int]:
        """Adjust maximized window size to the working area and enforce Qt minimum size."""
        # Validate message structure
        if not msg.lParam:
            return False, 0
            
        try:
            # Define POINT and MINMAXINFO structures for sizing
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            class MINMAXINFO(ctypes.Structure):
                _fields_ = [
                    ("ptReserved", POINT),
                    ("ptMaxSize", POINT),
                    ("ptMaxPosition", POINT),
                    ("ptMinTrackSize", POINT),
                    ("ptMaxTrackSize", POINT),
                ]

            info: MINMAXINFO = MINMAXINFO.from_address(msg.lParam)
            
            # Get monitor info for correct maximized sizing
            if not self.hwnd:
                return False, 0
                
            monitor = constants.Windows.user32.MonitorFromWindow(
                self.hwnd, constants.Windows.MONITOR_DEFAULTTONEAREST
            )
            if not monitor:
                return False, 0

            # Define MONITORINFOEX structure for monitor details
            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32),
                ]

            monitor_info = MONITORINFOEX()
            monitor_info.cbSize = ctypes.sizeof(MONITORINFOEX)
            
            if not constants.Windows.user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
                return False, 0

            work = monitor_info.rcWork
            full = monitor_info.rcMonitor

            # Set maximized window size and position to working area
            info.ptMaxPosition.x = work.left - full.left
            info.ptMaxPosition.y = work.top - full.top
            info.ptMaxSize.x = work.right - work.left
            info.ptMaxSize.y = work.bottom - work.top

            # Enforce Qt minimum window size
            min_width = max(self.window.minimumWidth(), 200)  # Reasonable minimum
            min_height = max(self.window.minimumHeight(), 100)
            info.ptMinTrackSize.x = min_width
            info.ptMinTrackSize.y = min_height

            return True, 0
            
        except (OSError, ValueError) as e:
            # Log error but don't crash
            print(f"Error in _handle_getminmax: {e}")
            return False, 0

    def _handle_hittest(self) -> Tuple[bool, int]:
        """Handle window hit-test for resizing and dragging."""
        try:
            # Get global and local mouse position
            pt: QPoint = cast(QPoint, QCursor.pos()) #type: ignore
            local: QPoint = cast(QPoint, self.window.mapFromGlobal(pt)) #type: ignore
            x: int = int(local.x())
            y: int = int(local.y())
            
            w: int = self.window.width()
            h: int = self.window.height()
            
            # Get current DPI ratio for accurate border width
            dpr: float = float(self.window.devicePixelRatio()) #type: ignore
            bw: int = int(self.BORDER_WIDTH * dpr)

            # If maximized, allow dragging only via title bar fallback
            if self.isMaximized():
                return self._dispatch_titlebar(pt, y)

            # Corners resize areas
            if x < bw and y < bw:
                return True, constants.Windows.HTTOPLEFT
            if x > w - bw and y < bw:
                return True, constants.Windows.HTTOPRIGHT
            if x < bw and y > h - bw:
                return True, constants.Windows.HTBOTTOMLEFT
            if x > w - bw and y > h - bw:
                return True, constants.Windows.HTBOTTOMRIGHT

            # Edges resize areas
            if y < bw:
                return True, constants.Windows.HTTOP
            if y > h - bw:
                return True, constants.Windows.HTBOTTOM
            if x < bw:
                return True, constants.Windows.HTLEFT
            if x > w - bw:
                return True, constants.Windows.HTRIGHT

            # Title bar area for dragging
            return self._dispatch_titlebar(pt, y)
            
        except Exception as e:
            print(f"Error in hittest: {e}")
            return False, 0

    def _dispatch_titlebar(self, global_pos: QPoint, y: int) -> Tuple[bool, int]:
        """Determine if the point is on title bar for dragging."""
        # Use custom titlebar hook if provided
        if self._titlebar_hook is not None:
            try:
                result = self._titlebar_hook(global_pos)
                if result is not None:
                    return result
            # Catch specific exceptions only
            except (AttributeError, TypeError, ValueError) as e:
                print(f"Error in titlebar hook: {e}")
                # Fall through to fallback

        # Fallback: treat area within TITLE_BAR_FALLBACK_HEIGHT as draggable
        if self.TITLE_BAR_FALLBACK and y < self.TITLE_BAR_FALLBACK_HEIGHT:
            return True, constants.Windows.HTCAPTION

        return False, 0

    def _update_maximize_button_state(self, is_maximized: bool) -> None:
        """Update maximize button appearance based on state."""
        if self._titlebar_maximize_button:
            try:
                # Update button text/icon based on state
                if hasattr(self._titlebar_maximize_button, 'setIcon'):
                    # Would need actual icons here
                    pass
                if hasattr(self._titlebar_maximize_button, 'setToolTip'):
                    tooltip = "Restore" if is_maximized else "Maximize"
                    self._titlebar_maximize_button.setToolTip(tooltip)
            except Exception as e:
                print(f"Error updating maximize button: {e}")

    def setTitlebarMaximizeButton(self, button: QPushButton) -> None:
        """Set the maximize button for custom titlebar."""
        self._titlebar_maximize_button = button
        self._update_maximize_button_state(self.isMaximized())

    def _debounced_apply_corners(self) -> None:
        """Debounce corner application to avoid rapid calls."""
        current_time = time.time()
        
        # Cancel existing timer
        if self._corner_timer:
            self._corner_timer.stop()
            
        # If last apply was recent, delay this one (minimum 50ms)
        time_since_last = current_time - self._last_corner_apply
        delay = max(0, 50 - int(time_since_last * 1000))  # 50ms minimum delay
        
        self._corner_timer = QTimer()
        self._corner_timer.singleShot(delay, self._apply_corners_now)

    def _apply_corners_now(self) -> None:
        """Apply corners and update timestamp."""
        self._last_corner_apply = time.time()
        self.apply_rounded_corners()

    def showMaximized(self) -> None:
        """Show window maximized, removing rounded corners."""
        if not self.hwnd:
            return
        constants.Windows.user32.ShowWindow(self.hwnd, constants.Windows.SW_MAXIMIZE)
        self._update_maximize_button_state(True)
        self._debounced_apply_corners()

    def showNormal(self) -> None:
        """Restore window, applying rounded corners."""
        if not self.hwnd:
            return
        constants.Windows.user32.ShowWindow(self.hwnd, constants.Windows.SW_RESTORE)
        self._update_maximize_button_state(False)
        self._debounced_apply_corners()

    def isMaximized(self) -> bool:
        """Check if window is maximized."""
        if not self.hwnd:
            return False
        return bool(constants.Windows.user32.IsZoomed(self.hwnd))

    def apply_rounded_corners(self) -> None:
        """Apply or remove rounded corners based on window maximized state."""
        if not self.hwnd:
            return
            
        try:
            if self.isMaximized():
                # Remove region clipping and disable rounding when maximized
                constants.Windows.user32.SetWindowRgn(self.hwnd, 0, True)
                if self._is_windows_11:
                    self._set_dwm_corner_preference(constants.Windows.DWMWCP_DONOTROUND)
            else:
                # Try native Windows 11 rounded corners first
                if self._is_windows_11:
                    try:
                        self._set_dwm_corner_preference(constants.Windows.DWMWCP_ROUND)
                        return
                    except Exception:
                        pass  # Fall back to manual method
                
                # Fallback to manual rounded region for older Windows
                radius = int(self.ROUND_CORNER_RADIUS * float(self.window.devicePixelRatio())) #type: ignore
                self._set_rounded_region(radius)
                
        except Exception as e:
            print(f"Error applying rounded corners: {e}")

    def _set_rounded_region(self, radius: int) -> None:
        """Apply a manual rounded rectangle region with proper resource management."""
        if not self.hwnd:
            return
            
        rect = wintypes.RECT()
        if not constants.Windows.user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return

        width = rect.right - rect.left
        height = rect.bottom - rect.top

        region = None
        try:
            # Create a rounded rectangle region for the window
            region = constants.Windows.gdi32.CreateRoundRectRgn(
                0, 0, width, height, radius, radius
            )
            if region:
                # SetWindowRgn takes ownership of the region, so we don't delete it
                constants.Windows.user32.SetWindowRgn(self.hwnd, region, True)
                region = None  # Don't delete - ownership transferred
        except Exception as e:
            print(f"Error setting rounded region: {e}")
        finally:
            # Only delete if we still own the region
            if region:
                constants.Windows.gdi32.DeleteObject(region)

    def _set_dwm_corner_preference(self, preference: int) -> None:
        """Set Windows 11 DWM corner preference with version check."""
        if not self._is_windows_11 or not self.hwnd:
            raise RuntimeError("DWM corner preference not supported on this Windows version")
            
        val = ctypes.c_int(preference)
        hr = constants.Windows.dwmapi.DwmSetWindowAttribute(
            self.hwnd,
            constants.Windows.DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(val),
            ctypes.sizeof(val),
        )
        if hr != 0:
            raise ctypes.WinError(hr)

    # Remove the duplicate DWM_BB_ENABLE definition since it's now in constants
    class DWM_BLURBEHIND(ctypes.Structure):
        _fields_ = [
            ("dwFlags", wintypes.DWORD),
            ("fEnable", wintypes.BOOL),
            ("hRgnBlur", wintypes.HRGN),
            ("fTransitionOnMaximized", wintypes.BOOL),
        ]

    # DWM_BB_ENABLE is now defined in constants module

    def enable_acrylic_blur(self) -> None:
        """Enable acrylic blur effect behind the window."""
        if not self.hwnd:
            return
            
        try:
            blur = self.DWM_BLURBEHIND()
            blur.dwFlags = constants.Windows.DWM_BB_ENABLE
            blur.fEnable = True
            blur.hRgnBlur = 0
            blur.fTransitionOnMaximized = False
            hr = constants.Windows.dwmapi.DwmEnableBlurBehindWindow(self.hwnd, ctypes.byref(blur))
            if hr != 0:
                print(f"Warning: Failed to enable blur effect (HRESULT: 0x{hr:08x})")
        except Exception as e:
            print(f"Error enabling acrylic blur: {e}")

    def cleanup(self) -> None:
        """Cleanup resources when window is destroyed."""
        if self._corner_timer:
            self._corner_timer.stop()
        if self._original_cursor:
            constants.Windows.user32.SetCursor(self._original_cursor)