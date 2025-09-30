import ctypes

class Windows:
    user32: ctypes.WinDLL = ctypes.windll.user32
    dwmapi: ctypes.WinDLL = ctypes.windll.dwmapi
    gdi32: ctypes.WinDLL = ctypes.windll.gdi32

    # WINDOWS MESSAGES
    WM_NCMOUSEMOVE: int = 0x00A0
    WM_NCHITTEST: int = 0x0084
    WM_NCCALCSIZE: int = 0x0083
    WM_NCPAINT: int = 0x0085
    WM_NCACTIVATE: int = 0x0086
    WM_GETMINMAXINFO: int = 0x0024
    WM_SIZE: int = 0x0005
    WM_WINDOWPOSCHANGED: int = 0x0047
    WM_EXITSIZEMOVE: int = 0x0232
    WM_DPICHANGED: int = 0x02E0
    WM_NCLBUTTONDOWN: int = 0x00A1
    WM_NCLBUTTONUP: int = 0x00A2
    WM_NCLBUTTONDBLCLK: int = 0x00A3
    WM_SETCURSOR: int = 0x0020

    # HIT TEST CODES (HT*)
    HTCLIENT: int = 1
    HTCAPTION: int = 2
    HTSYSMENU: int = 3
    HTGROWBOX: int = 4
    HTSIZE: int = 4 
    HTMENU: int = 5
    HTHSCROLL: int = 6
    HTVSCROLL: int = 7
    HTMINBUTTON: int = 8
    HTMAXBUTTON: int = 9
    HTLEFT: int = 10
    HTRIGHT: int = 11
    HTTOP: int = 12
    HTTOPLEFT: int = 13
    HTTOPRIGHT: int = 14
    HTBOTTOM: int = 15
    HTBOTTOMLEFT: int = 16
    HTBOTTOMRIGHT: int = 17
    HTCLOSE: int = 20
    HTHELP: int = 21
    
    HTREDUCE: int = HTMINBUTTON
    HTZOOM: int = HTMAXBUTTON

    # WINDOW STYLES AND FLAGS (WS*, GWL*)
    GWL_STYLE: int = -16
    WS_CAPTION: int = 0x00C00000
    WS_THICKFRAME: int = 0x00040000

    # SetWindowPos flags
    SWP_NOMOVE: int = 0x0002
    SWP_NOSIZE: int = 0x0001
    SWP_FRAMECHANGED: int = 0x0020

    # SHOW WINDOW COMMANDS (SW*)
    SW_HIDE: int = 0
    SW_SHOWNORMAL: int = 1
    SW_SHOWMINIMIZED: int = 2
    SW_MAXIMIZE: int = 3
    SW_SHOWNOACTIVATE: int = 4
    SW_SHOW: int = 5
    SW_MINIMIZE: int = 6
    SW_SHOWMINNOACTIVE: int = 7
    SW_SHOWNA: int = 8
    SW_RESTORE: int = 9

    # CURSOR CONSTANTS (IDC*)
    IDC_ARROW: int = 32512
    IDC_HAND: int = 32649
    IDC_SIZEWE: int = 32644
    IDC_SIZENS: int = 32645
    IDC_SIZENWSE: int = 32642
    IDC_SIZENESW: int = 32643
    IDC_SIZEALL: int = 32646

    # MONITOR CONSTANTS
    MONITOR_DEFAULTTONULL: int = 0
    MONITOR_DEFAULTTOPRIMARY: int = 1
    MONITOR_DEFAULTTONEAREST: int = 2

    # DWM (DESKTOP WINDOW MANAGER) CONSTANTS (DWMWA*, DWMNCRP*, DWMWCP*, DWM_BB*)
    DWMWA_NCRENDERING_POLICY: int = 2
    DWMNCRP_DISABLED: int = 2
    DWMWA_WINDOW_CORNER_PREFERENCE: int = 33

    DWMWCP_DEFAULT: int = 0
    DWMWCP_DONOTROUND: int = 1
    DWMWCP_ROUND: int = 2
    DWMWCP_ROUNDSMALL: int = 3

    DWM_BB_ENABLE: int = 0x00000001
    DWM_BB_BLURREGION: int = 0x00000002
    DWM_BB_TRANSITIONONMAXIMIZED: int = 0x00000004

    # UNUSED CONSTANTS FROM ORIGINAL SNIPPET
    HWND_TOP: int = 0
    HWND_BOTTOM: int = 1
    HWND_TOPMOST: int = -1
    HWND_NOTOPMOST: int = -2
    ERROR_SUCCESS: int = 0
    ERROR_INVALID_PARAMETER: int = 87
    HKEY_LOCAL_MACHINE: int = 0x80000002