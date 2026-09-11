import tkinter as tk

from logic import TrackerLogic
from gui import DailyTrackerGUI


def main():
    # Create the Tkinter application
    root = tk.Tk()

    # Create the application logic
    logic = TrackerLogic(db_path="tracker.db")

    # Create the GUI and give it access to the logic
    app = DailyTrackerGUI(
        root,
        logic
        )

    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()

