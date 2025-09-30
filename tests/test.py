import unittest
from PySide6.QtWidgets import QApplication, QMainWindow
from customqt.windows import WindowsStyler

# Ensure there is one QApplication instance for all tests
app = QApplication.instance() or QApplication([])

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empty Test Window")
        self.resize(400, 300)
        self.windowsStyler = WindowsStyler(self)
        self.windowsStyler.init()

class TestWindowsStyler(unittest.TestCase):
    def setUp(self):
        # Create a fresh window before each test
        self.window = TestWindow()

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), "Empty Test Window")

    def test_window_size(self):
        width = self.window.width()
        height = self.window.height()
        self.assertEqual((width, height), (400, 300))

    def test_windows_styler_initialized(self):
        # Check if the styler object exists
        self.assertIsNotNone(self.window.windowsStyler)

if __name__ == "__main__":
    unittest.main()
