import tkinter as tk
import ctypes
from ctypes import wintypes

from ui_tutorial import TutorialScreen
from ui_recognition import RecognitionScreen
from ui_about import AboutScreen
from utils import apply_app_window_style


class GestureFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GestureFlow")
        self.geometry("1400x900")
        self.minsize(1200, 700)

        apply_app_window_style(self)
        self._install_windows_alt_freeze_fix()

        self.current_screen = None

        self.show_tutorial()

    def _install_windows_alt_freeze_fix(self):
        """
        Prevent Alt from putting Tk into Windows menu mode, which can stall
        camera UI updates until the user clicks the window again.
        """
        try:
            if self.tk.call("tk", "windowingsystem") != "win32":
                return
        except Exception:
            return

        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080

        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(self.winfo_id())

        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_TOOLWINDOW)

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )

        def _block_alt(_event):
            return "break"

        self.bind_all("<KeyPress-Alt_L>", _block_alt)
        self.bind_all("<KeyRelease-Alt_L>", _block_alt)
        self.bind_all("<KeyPress-Alt_R>", _block_alt)
        self.bind_all("<KeyRelease-Alt_R>", _block_alt)
        self.bind_all("<Alt-KeyPress>", _block_alt)
        self.bind_all("<Alt-KeyRelease>", _block_alt)

    def clear_screen(self):
        if self.current_screen is not None:
            self.current_screen.destroy()
            self.current_screen = None

    def show_tutorial(self):
        self.clear_screen()
        self.current_screen = TutorialScreen(
            self,
            on_enter_experience=self.show_recognition
        )
        self.current_screen.pack(fill="both", expand=True)

    def show_recognition(self):
        self.clear_screen()
        self.current_screen = RecognitionScreen(
            self,
            on_show_about=self.show_about,
            on_exit_to_tutorial=self.show_tutorial
        )
        self.current_screen.pack(fill="both", expand=True)

    def show_about(self):
        self.clear_screen()
        self.current_screen = AboutScreen(
            self,
            on_back=self.show_recognition,
            on_replay_tutorial=self.show_tutorial,
            on_exit_system=self.show_tutorial
        )
        self.current_screen.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = GestureFlowApp()
    app.mainloop()
