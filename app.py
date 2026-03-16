import tkinter as tk

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

        self.current_screen = None

        self.show_tutorial()

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