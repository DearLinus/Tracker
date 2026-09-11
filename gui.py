import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path
from version import APP_VERSION
import json
import urllib.request
import subprocess
import os
import sys
import tempfile

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates



class DailyTrackerGUI:
    
    GITHUB_OWNER = "DearLinus"
    GITHUB_REPO = "Tracker"

    GITHUB_API_URL = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    )
    # Set this to a raw GitHub URL (or another HTTPS URL) that returns:
    # {"version": "1.1.0", "url": "...", "notes": "..."}
    # The Settings page uses this URL for Check for Updates.
    UPDATE_MANIFEST_URL = ""

    def __init__(self, root, logic):
        self.root = root
        self.logic = logic
        self.settings_path = Path(__file__).with_name("tracker_settings.json")
        self.theme_mode = self.load_theme()
        self.effective_theme = self.get_effective_theme()

        # -----------------------------
        # Window
        # -----------------------------
        self.root.title("Daily Tracker")
        self.root.geometry("1180x760")
        self.root.minsize(980, 650)

        # -----------------------------
        # Theme
        # -----------------------------
        self.set_theme_colors()
        self.root.configure(bg=self.bg)

        # References to dynamic UI elements
        self.stat_value_labels = {}
        self.content = None
        self.current_page = None

        self.setup_styles()
        self.build_ui()

        self.show_overview()

    # =========================================================
    # THEME & SETTINGS
    # =========================================================

    def get_effective_theme(self):
        """Return the actual light/dark theme to use."""
        if self.theme_mode != "system":
            return self.theme_mode

        # KDE Plasma
        try:
            result = subprocess.run(
                ["kreadconfig6", "--group", "General", "--key", "ColorScheme"],
                capture_output=True, text=True, timeout=1
            )
            scheme = result.stdout.strip().lower()
            if scheme:
                dark_names = ("dark", "breeze dark", "breeze-dark")
                return "dark" if any(name in scheme for name in dark_names) else "light"
        except (OSError, subprocess.SubprocessError):
            pass

        # GNOME / GTK-compatible desktops
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=1
            )
            scheme = result.stdout.strip().lower()
            if "prefer-dark" in scheme:
                return "dark"
            if "prefer-light" in scheme:
                return "light"
        except (OSError, subprocess.SubprocessError):
            pass

        # Common desktop/environment fallback.
        desktop = os.environ.get("GTK_THEME", "").lower()
        if "dark" in desktop:
            return "dark"

        return "light"

    def set_theme_colors(self):
        self.effective_theme = self.get_effective_theme()
        if self.effective_theme == "dark":
            self.bg = "#0f1117"
            self.sidebar_bg = "#0b0d12"
            self.card_bg = "#171a21"
            self.text = "#f3f4f6"
            self.secondary_text = "#9ca3af"
            self.accent = "#818cf8"
            self.border = "#2a2f3a"
            self.danger = "#f87171"
        else:
            self.bg = "#f3f5f9"
            self.sidebar_bg = "#171b24"
            self.card_bg = "#ffffff"
            self.text = "#171a21"
            self.secondary_text = "#687080"
            self.accent = "#6366f1"
            self.border = "#e2e6ee"
            self.danger = "#ef4444"

    def load_theme(self):
        try:
            if self.settings_path.exists():
                data = json.loads(self.settings_path.read_text(encoding="utf-8"))
                theme = data.get("theme")
                if theme in ("light", "dark", "system"):
                    return theme
        except (OSError, json.JSONDecodeError):
            pass
        return "light"

    def save_theme(self):
        try:
            self.settings_path.write_text(
                json.dumps({"theme": self.theme_mode}, indent=2),
                encoding="utf-8"
            )
        except OSError:
            pass

    def apply_theme(self, theme):
        if theme not in ("light", "dark", "system"):
            return

        # Clicking the already-active option should do absolutely nothing.
        if theme == self.theme_mode:
            return

        self.theme_mode = theme
        self.save_theme()
        self.set_theme_colors()
        self.root.configure(bg=self.bg)

        for widget in self.root.winfo_children():
            widget.destroy()

        self.stat_value_labels = {}
        self.content = None
        self.setup_styles()
        self.build_ui()

        if self.current_page == "Statistics":
            self.show_statistics(force=True)
        elif self.current_page == "History":
            self.show_history(force=True)
        elif self.current_page == "Settings":
            self.show_settings(force=True)
        else:
            self.show_overview(force=True)

    def show_settings(self, force=False):
        if not force and self.current_page == "Settings":
            return
        self.current_page = "Settings"
        self.clear_content()
        self.build_header("Settings")

        card = tk.Frame(
            self.content,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )
        card.pack(fill="x", padx=35, pady=(0, 18))

        tk.Label(
            card, text="Appearance", bg=self.card_bg, fg=self.text,
            font=("DejaVu Sans", 15, "bold")
        ).pack(anchor="w", padx=24, pady=(22, 4))

        tk.Label(
            card, text="Choose how Daily Tracker looks.", bg=self.card_bg,
            fg=self.secondary_text, font=("DejaVu Sans", 10)
        ).pack(anchor="w", padx=24, pady=(0, 18))

        theme_var = tk.StringVar(value=self.theme_mode)
        options = tk.Frame(card, bg=self.card_bg)
        options.pack(fill="x", padx=20, pady=(0, 24))

        for value, title, subtitle in (
            ("system", "System", "Use your system appearance"),
            ("light", "Light", "Bright interface"),
            ("dark", "Dark", "Comfortable in low light"),
        ):
            option = tk.Frame(
                options, bg=self.bg,
                highlightbackground=self.border, highlightthickness=1
            )
            option.pack(side="left", fill="both", expand=True, padx=5)

            radio = tk.Radiobutton(
                option, text=title, variable=theme_var, value=value,
                bg=self.bg, fg=self.text, activebackground=self.bg,
                activeforeground=self.text, selectcolor=self.card_bg,
                font=("DejaVu Sans", 10, "bold"),
                command=lambda v=value: self.apply_theme(v)
            )
            radio.pack(anchor="w", padx=14, pady=(12, 2))

            tk.Label(
                option, text=subtitle, bg=self.bg, fg=self.secondary_text,
                font=("DejaVu Sans", 8)
            ).pack(anchor="w", padx=38, pady=(0, 12))

        update_card = tk.Frame(
            self.content,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )
        update_card.pack(fill="x", padx=35, pady=(0, 18))

        tk.Label(
            update_card, text="Updates", bg=self.card_bg, fg=self.text,
            font=("DejaVu Sans", 15, "bold")
        ).pack(anchor="w", padx=24, pady=(22, 4))

        tk.Label(
            update_card,
            text=f"Current version: {APP_VERSION}",
            bg=self.card_bg, fg=self.secondary_text,
            font=("DejaVu Sans", 10)
        ).pack(anchor="w", padx=24, pady=(0, 14))

        self.update_status_label = tk.Label(
            update_card, text="", bg=self.card_bg, fg=self.secondary_text,
            font=("DejaVu Sans", 9), wraplength=650, justify="left"
        )
        self.update_status_label.pack(anchor="w", padx=24, pady=(0, 14))

        update_buttons = tk.Frame(update_card, bg=self.card_bg)
        update_buttons.pack(anchor="w", padx=24, pady=(0, 22))

        ttk.Button(
            update_buttons, text="Check for Updates", style="Accent.TButton",
            command=self.check_for_updates
        ).pack(side="left")

        self.update_now_button = ttk.Button(
            update_buttons, text="Update Now", style="Accent.TButton",
            command=self.start_update, state="disabled"
        )
        self.update_now_button.pack(side="left", padx=(10, 0))

        self.available_update = None

        info = tk.Frame(
            self.content, bg=self.card_bg,
            highlightbackground=self.border, highlightthickness=1
        )
        info.pack(fill="x", padx=35)

        tk.Label(
            info, text="Daily Tracker", bg=self.card_bg, fg=self.text,
            font=("DejaVu Sans", 11, "bold")
        ).pack(anchor="w", padx=24, pady=(18, 3))
        tk.Label(
            info, text="Settings are saved automatically on this computer.",
            bg=self.card_bg, fg=self.secondary_text,
            font=("DejaVu Sans", 9)
        ).pack(anchor="w", padx=24, pady=(0, 18))

    def check_for_updates(self):
        self.update_status_label.config(
            text="Checking for updates...",
            fg=self.secondary_text
        )
        self.root.update_idletasks()

        try:
            request = urllib.request.Request(
                self.GITHUB_API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "DailyTracker"
                }
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

            latest_version = payload["tag_name"].lstrip("v")
            release_name = payload.get("name", "")
            release_notes = payload.get("body", "")
            release_page = payload.get("html_url", "")

            download_url = None
            expected_sha256 = None

            for asset in payload.get("assets", []):
                if asset.get("name") == f"DailyTracker-v{latest_version}.zip":
                    download_url = asset.get("browser_download_url")
                    digest = asset.get("digest") or ""
                    if digest.startswith("sha256:"):
                        expected_sha256 = digest.split(":", 1)[1].strip().lower()
                    break

            if self.compare_versions(latest_version, APP_VERSION) > 0:
                if not download_url:
                    raise ValueError(
                        "A ZIP file for this release could not be found."
                    )

                message = f"New version available: {latest_version}"

                if release_name:
                    message += f"\n\n{release_name}"

                if release_notes:
                    message += f"\n\n{release_notes}"

                self.available_update = {
                    "version": latest_version,
                    "download_url": download_url,
                    "sha256": expected_sha256,
                    "release_page": release_page,
                }
                self.update_now_button.config(state="normal")

                if expected_sha256:
                    message += "\n\nSHA-256 verification is available for this release."
                else:
                    message += "\n\nWarning: this release has no SHA-256 digest in GitHub."

                self.update_status_label.config(
                    text=message,
                    fg=self.accent
                )
            else:
                self.available_update = None
                self.update_now_button.config(state="disabled")
                self.update_status_label.config(
                    text="You are using the latest version.",
                    fg="#22c55e"
                )

        except Exception as error:
            self.available_update = None
            self.update_now_button.config(state="disabled")
            self.update_status_label.config(
                text=f"Could not check for updates: {error}",
                fg=self.danger
            )

    def start_update(self):
        """Download the selected release and hand the replacement work to updater.py."""
        if not self.available_update:
            return

        update = self.available_update
        latest_version = update["version"]
        download_url = update["download_url"]
        expected_sha256 = update.get("sha256")

        if not download_url:
            messagebox.showerror("Update", "No download file was found for this release.")
            return

        if not expected_sha256:
            proceed = messagebox.askyesno(
                "Update verification",
                "GitHub did not provide a SHA-256 digest for this release.\n\n"
                "The ZIP will still be checked for integrity, but its authenticity "
                "cannot be cryptographically verified.\n\nContinue?"
            )
            if not proceed:
                return

        self.update_now_button.config(state="disabled")
        self.update_status_label.config(
            text=f"Downloading version {latest_version}...\n0%",
            fg=self.accent
        )
        self.root.update_idletasks()

        try:
            temp_file = tempfile.NamedTemporaryFile(
                prefix="daily_tracker_update_",
                suffix=".zip",
                delete=False
            )
            temp_path = Path(temp_file.name)
            temp_file.close()

            request = urllib.request.Request(
                download_url,
                headers={
                    "User-Agent": "DailyTracker",
                    "Accept": "application/octet-stream",
                }
            )

            with urllib.request.urlopen(request, timeout=30) as response, open(temp_path, "wb") as output:
                total_size = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = int(downloaded * 100 / total_size)
                        self.update_status_label.config(
                            text=f"Downloading version {latest_version}...\n{percent}%",
                            fg=self.accent
                        )
                        self.root.update_idletasks()

            self.update_status_label.config(
                text="Download complete. Starting updater...",
                fg=self.accent
            )
            self.root.update_idletasks()

            updater_path = Path(__file__).resolve().with_name("updater.py")
            if not updater_path.exists():
                raise FileNotFoundError(f"updater.py was not found next to the application.")

            subprocess.Popen([
                sys.executable,
                str(updater_path),
                "--zip", str(temp_path),
                "--app-dir", str(Path(__file__).resolve().parent),
                "--pid", str(os.getpid()),
                "--expected-sha256", expected_sha256 or "",
            ])

            self.root.after(150, self.root.destroy)

        except Exception as error:
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            self.update_status_label.config(
                text=f"Update failed: {error}",
                fg=self.danger
            )
            self.update_now_button.config(state="normal")

    @staticmethod
    def compare_versions(left, right):
        def parts(value):
            result = []
            for part in value.lstrip("vV").split("."):
                digits = "".join(ch for ch in part if ch.isdigit())
                result.append(int(digits or 0))
            while len(result) < 3:
                result.append(0)
            return tuple(result[:3])

        return (parts(left) > parts(right)) - (parts(left) < parts(right))

    # =========================================================
    # STYLES
    # =========================================================

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Sidebar.TButton",
            font=("DejaVu Sans", 10, "bold"),
            padding=(15, 13),
            background=self.sidebar_bg,
            foreground="#d1d5db",
            borderwidth=0
        )

        style.map(
            "Sidebar.TButton",
            background=[("active", "#2b3038")],
            foreground=[("active", "#ffffff")]
        )

        style.configure(
            "Accent.TButton",
            font=("DejaVu Sans", 10, "bold"),
            padding=(18, 10),
            background=self.accent,
            foreground="white",
            borderwidth=0
        )

        style.map(
            "Accent.TButton",
            background=[("active", "#4338ca")]
        )

        style.configure(
            "Danger.TButton",
            font=("DejaVu Sans", 9, "bold"),
            padding=(10, 6),
            background=self.danger,
            foreground="white",
            borderwidth=0
        )

        style.map(
            "Danger.TButton",
            background=[("active", "#b91c1c")]
        )

        style.configure(
            "TEntry",
            fieldbackground=self.card_bg,
            foreground=self.text,
            bordercolor=self.border,
            lightcolor=self.border,
            darkcolor=self.border
        )

        style.configure(
            "Treeview",
            font=("DejaVu Sans", 10),
            rowheight=42,
            background=self.card_bg,
            fieldbackground=self.card_bg,
            foreground=self.text
        )

        style.configure(
            "Treeview.Heading",
            font=("DejaVu Sans", 10, "bold"),
            padding=8
        )

    # =========================================================
    # MAIN UI
    # =========================================================

    def build_ui(self):
        # -----------------------------
        # Sidebar
        # -----------------------------
        sidebar = tk.Frame(
            self.root,
            bg=self.sidebar_bg,
            width=220
        )

        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo = tk.Label(
            sidebar,
            text="Daily Tracker",
            bg=self.sidebar_bg,
            fg="white",
            font=("DejaVu Sans", 18, "bold")
        )

        logo.pack(
            anchor="w",
            padx=25,
            pady=(30, 45)
        )

        self.overview_button = self.create_sidebar_button(
            sidebar,
            "Overview",
            command=self.show_overview
        )

        self.statistics_button = self.create_sidebar_button(
            sidebar,
            "Statistics",
            command=self.show_statistics
        )

        self.history_button = self.create_sidebar_button(
            sidebar,
            "History",
            command=self.show_history
        )

        self.settings_button = self.create_sidebar_button(
            sidebar,
            "Settings",
            command=self.show_settings
        )

        version = tk.Label(
            sidebar,
            text="Personal Tracker",
            bg=self.sidebar_bg,
            fg="#6b7280",
            font=("DejaVu Sans", 9)
        )

        version.pack(
            side="bottom",
            anchor="w",
            padx=25,
            pady=25
        )

        # -----------------------------
        # Main content container
        # -----------------------------
        self.content = tk.Frame(
            self.root,
            bg=self.bg
        )

        self.content.pack(
            side="left",
            fill="both",
            expand=True
        )

    # =========================================================
    # PAGE MANAGEMENT
    # =========================================================

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        self.stat_value_labels = {}

    def show_overview(self, force=False):
        if not force and self.current_page == "Overview":
            return
        self.current_page = "Overview"
        self.clear_content()

        self.build_header("Overview")

        self.build_stats_cards()

        graph_card = tk.Frame(
            self.content,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )

        graph_card.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=25
        )

        graph_header = tk.Frame(
            graph_card,
            bg=self.card_bg
        )

        graph_header.pack(
            fill="x",
            padx=25,
            pady=(20, 5)
        )

        graph_title = tk.Label(
            graph_header,
            text="Daily Frequency",
            bg=self.card_bg,
            fg=self.text,
            font=("DejaVu Sans", 15, "bold")
        )

        graph_title.pack(side="left")

        add_button = ttk.Button(
            graph_header,
            text="+ Add Record",
            style="Accent.TButton",
            command=self.add_record
        )

        add_button.pack(side="right")

        # Timeline selector lives outside the plot frame, because update_graph()
        # rebuilds the plot itself.
        self.update_stats()

        timeline_bar = tk.Frame(
            graph_card,
            bg=self.card_bg
        )
        timeline_bar.pack(fill="x", padx=25, pady=(8, 0))

        timeline_label = tk.Label(
            timeline_bar,
            text="Timeline",
            bg=self.card_bg,
            fg=self.text,
            font=("Segoe UI", 10, "bold")
        )
        timeline_label.pack(side="left", padx=(0, 10))

        # Preserve the selected timeline when the page is rebuilt.
        if not hasattr(self, "timeline_var") or self.timeline_var.get() not in (
            "Weekly", "Monthly", "3 Months", "6 Months", "1 Year"
        ):
            self.timeline_var = tk.StringVar(value="Monthly")

        timeline_values = [
            "Weekly",
            "Monthly",
            "3 Months",
            "6 Months",
            "1 Year",
        ]

        timeline_menu = tk.OptionMenu(
            timeline_bar,
            self.timeline_var,
            *timeline_values,
            command=lambda _value: self.update_graph()
        )
        timeline_menu.config(
            bg=self.card_bg,
            fg=self.text,
            activebackground=self.accent,
            activeforeground="#ffffff",
            highlightthickness=1,
            highlightbackground=self.border,
            bd=0,
            font=("Segoe UI", 9),
            padx=8,
            pady=3
        )
        timeline_menu["menu"].config(
            bg=self.card_bg,
            fg=self.text,
            activebackground=self.accent,
            activeforeground="#ffffff",
            font=("Segoe UI", 9)
        )
        timeline_menu.pack(side="left")

        self.graph_frame = tk.Frame(
            graph_card,
            bg=self.card_bg
        )
        self.graph_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(5, 15)
        )

        self.update_graph()

    def show_statistics(self, force=False):
        if not force and self.current_page == "Statistics":
            return
        # Statistics page for now uses the same core statistics,
        # but leaves room for more detailed analytics later.
        self.current_page = "Statistics"
        self.clear_content()

        self.build_header("Statistics")

        self.build_stats_cards()

        # build_stats_cards() creates the cards with placeholder values.
        # Immediately replace them with the real database statistics.
        self.update_stats()

        card = tk.Frame(
            self.content,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )

        card.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=25
        )

        title = tk.Label(
            card,
            text="Statistics",
            bg=self.card_bg,
            fg=self.text,
            font=("DejaVu Sans", 16, "bold")
        )

        title.pack(
            anchor="w",
            padx=25,
            pady=(25, 10)
        )

        records = self.logic.get_records()

        if not records:
            text = "No records available yet."
        else:
            text = (
                f"Recorded days: {len(records)}\n\n"
                f"Total count: {self.logic.get_total()}\n"
                f"Daily average: {self.logic.get_average():.1f}\n"
                f"Highest daily count: {self.logic.get_highest()}"
            )

        info = tk.Label(
            card,
            text=text,
            justify="left",
            bg=self.card_bg,
            fg=self.secondary_text,
            font=("DejaVu Sans", 11)
        )

        info.pack(
            anchor="w",
            padx=25,
            pady=10
        )

    def show_history(self, force=False):
        if not force and self.current_page == "History":
            return
        self.current_page = "History"
        self.clear_content()

        self.build_header("History")

        # -----------------------------
        # History card
        # -----------------------------
        card = tk.Frame(
            self.content,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )

        card.pack(
            fill="both",
            expand=True,
            padx=35,
            pady=(0, 25)
        )

        header = tk.Frame(
            card,
            bg=self.card_bg
        )

        header.pack(
            fill="x",
            padx=25,
            pady=(20, 10)
        )

        title = tk.Label(
            header,
            text="Recorded Entries",
            bg=self.card_bg,
            fg=self.text,
            font=("DejaVu Sans", 15, "bold")
        )

        title.pack(side="left")

        add_button = ttk.Button(
            header,
            text="+ Add Record",
            style="Accent.TButton",
            command=self.add_record
        )

        add_button.pack(side="right")

        # -----------------------------
        # Table
        # -----------------------------
        table_frame = tk.Frame(
            card,
            bg=self.card_bg
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=(5, 25)
        )

        columns = ("date", "count", "action")

        self.history_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        self.history_tree.heading(
            "date",
            text="Date"
        )

        self.history_tree.heading(
            "count",
            text="Count"
        )

        self.history_tree.heading(
            "action",
            text="Action"
        )

        self.history_tree.column(
            "date",
            width=250,
            anchor="center"
        )

        self.history_tree.column(
            "count",
            width=150,
            anchor="center"
        )

        self.history_tree.column(
            "action",
            width=200,
            anchor="center"
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.history_tree.yview
        )

        self.history_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.history_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.history_tree.bind(
            "<Double-1>",
            self.on_history_double_click
        )

        self.refresh_history()

    # =========================================================
    # HEADER
    # =========================================================

    def build_header(self, title_text):
        header = tk.Frame(
            self.content,
            bg=self.bg
        )

        header.pack(
            fill="x",
            padx=35,
            pady=(30, 20)
        )

        title = tk.Label(
            header,
            text=title_text,
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 27, "bold")
        )

        title.pack(side="left")

        today = datetime.now().strftime("%B %d, %Y")

        date_label = tk.Label(
            header,
            text=today,
            bg=self.bg,
            fg=self.secondary_text,
            font=("DejaVu Sans", 10)
        )

        date_label.pack(
            side="right",
            pady=10
        )

    # =========================================================
    # SIDEBAR BUTTON
    # =========================================================

    def create_sidebar_button(
        self,
        parent,
        text,
        command
    ):
        button = ttk.Button(
            parent,
            text=text,
            style="Sidebar.TButton",
            command=command
        )

        button.pack(
            fill="x",
            padx=15,
            pady=3
        )

        return button

    # =========================================================
    # STATISTICS CARDS
    # =========================================================

    def build_stats_cards(self):
        stats_frame = tk.Frame(
            self.content,
            bg=self.bg
        )

        stats_frame.pack(
            fill="x",
            padx=35
        )

        self.create_stat_card(
            stats_frame,
            "Total",
            "0",
            "All recorded entries"
        )

        self.create_stat_card(
            stats_frame,
            "Daily Average",
            "0.0",
            "Average per recorded day"
        )

        self.create_stat_card(
            stats_frame,
            "Highest",
            "0",
            "Highest daily count"
        )

    def create_stat_card(
        self,
        parent,
        title,
        value,
        subtitle
    ):
        card = tk.Frame(
            parent,
            bg=self.card_bg,
            highlightbackground=self.border,
            highlightthickness=1
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 14),
            pady=(0, 2)
        )

        accent_strip = tk.Frame(
            card,
            bg=self.accent if title == "Total"
            else "#22c55e" if title == "Daily Average"
            else "#f59e0b",
            height=4
        )
        accent_strip.pack(fill="x")
        accent_strip.pack_propagate(False)

        title_label = tk.Label(
            card,
            text=title,
            bg=self.card_bg,
            fg=self.secondary_text,
            font=("DejaVu Sans", 10)
        )

        title_label.pack(
            anchor="w",
            padx=20,
            pady=(18, 5)
        )

        value_label = tk.Label(
            card,
            text=value,
            bg=self.card_bg,
            fg=self.text,
            font=("DejaVu Sans", 25, "bold")
        )

        value_label.pack(
            anchor="w",
            padx=20
        )

        self.stat_value_labels[title] = value_label

        subtitle_label = tk.Label(
            card,
            text=subtitle,
            bg=self.card_bg,
            fg="#9ca3af",
            font=("DejaVu Sans", 9)
        )

        subtitle_label.pack(
            anchor="w",
            padx=20,
            pady=(2, 18)
        )

    def update_stats(self):
        if not self.stat_value_labels:
            return

        total = self.logic.get_total()
        average = self.logic.get_average()
        highest = self.logic.get_highest()

        self.stat_value_labels["Total"].config(
            text=str(total)
        )

        self.stat_value_labels["Daily Average"].config(
            text=f"{average:.1f}"
        )

        self.stat_value_labels["Highest"].config(
            text=str(highest)
        )

    # =========================================================
    # GRAPH
    # =========================================================

    def update_graph(self):
        if not hasattr(self, "graph_frame"):
            return

        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        records = self.logic.get_records()

        if not records:
            empty = tk.Label(
                self.graph_frame,
                text="No records available yet.",
                bg=self.card_bg,
                fg=self.secondary_text,
                font=("Segoe UI", 12)
            )
            empty.pack(expand=True)
            return

        if not hasattr(self, "timeline_var"):
            self.timeline_var = tk.StringVar(value="Monthly")

        timeline_days = {
            "Weekly": 7,
            "Monthly": 30,
            "3 Months": 90,
            "6 Months": 180,
            "1 Year": 365,
        }

        selected = self.timeline_var.get()
        days = timeline_days.get(selected, 30)

        all_dates = sorted(records.keys())
        latest_date = all_dates[-1]

        # The timeline is a zoom window around the data.
        # If the selected window contains no record except because all
        # data is older than the window, show the newest record rather
        # than producing an apparently broken/empty graph.
        start_date = latest_date - timedelta(days=days - 1)

        filtered = {
            d: count
            for d, count in records.items()
            if start_date <= d <= latest_date
        }

        if not filtered:
            filtered = {latest_date: records[latest_date]}

        dates = sorted(filtered.keys())
        counts = [filtered[d] for d in dates]

        fig = Figure(figsize=(9.2, 4.7), dpi=100)
        ax = fig.add_subplot(111)

        ax.set_facecolor(self.card_bg)
        fig.patch.set_facecolor(self.card_bg)

        graph_text_color = (
            "#ffffff" if self.effective_theme == "dark" else self.text
        )
        graph_secondary_color = (
            "#ffffff" if self.effective_theme == "dark"
            else self.secondary_text
        )

        line, = ax.plot(
            dates,
            counts,
            marker="o",
            markersize=7.5,
            linewidth=2.4,
            color=self.accent,
            markeredgecolor=self.accent,
            markerfacecolor=self.accent
        )

        # Every date that has a point in the selected range is a normal tick.
        ax.set_xticks(dates)
        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%b %d")
        )

        date_count = len(dates)

        if date_count <= 10:
            label_size, rotation = 9, 0
        elif date_count <= 18:
            label_size, rotation = 8, 25
        elif date_count <= 30:
            label_size, rotation = 7, 35
        else:
            label_size, rotation = 6.5, 45

        ax.tick_params(
            axis="x",
            labelsize=label_size,
            pad=8,
            colors=graph_secondary_color
        )
        ax.tick_params(
            axis="y",
            labelsize=9,
            colors=graph_secondary_color
        )

        normal_x_labels = ax.get_xticklabels()
        normal_y_labels = ax.get_yticklabels()

        for label in normal_x_labels + normal_y_labels:
            label.set_color(graph_secondary_color)
            label.set_fontweight("normal")

        from matplotlib.ticker import MaxNLocator
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        x_num = mdates.date2num(dates)

        if len(x_num) == 1:
            ax.set_xlim(x_num[0] - 1, x_num[0] + 1)
        else:
            span = x_num[-1] - x_num[0]
            padding = max(0.75, span * 0.03)
            ax.set_xlim(
                x_num[0] - padding,
                x_num[-1] + padding
            )

        max_count = max(counts)
        min_count = min(counts)

        if max_count == min_count:
            lower = max(0, min_count - 1)
            upper = max_count + 1
        else:
            padding = max(
                1,
                (max_count - min_count) * 0.12
            )
            lower = max(0, min_count - padding)
            upper = max_count + padding

        ax.set_ylim(lower, upper)

        # Normal graph grid. Hover guides below are separate and only
        # span from the hovered point to the corresponding axes.
        ax.grid(
            axis="y",
            linestyle="--",
            linewidth=0.8,
            alpha=0.20
        )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(self.border)
        ax.spines["bottom"].set_color(self.border)

        ax.set_xlabel(
            "Date",
            fontsize=10,
            fontweight="bold",
            labelpad=12,
            color=graph_text_color
        )
        ax.set_ylabel(
            "Count",
            fontsize=10,
            fontweight="bold",
            labelpad=12,
            color=graph_text_color
        )

        # Hover point.
        hover_point, = ax.plot(
            [],
            [],
            marker="o",
            markersize=10,
            linestyle="None",
            color="#ef4444",
            visible=False
        )

        # IMPORTANT:
        # These are NOT axhline/axvline. They are short segments:
        # point -> Y axis and X axis -> point.
        hover_y_guide, = ax.plot(
            [],
            [],
            linestyle=":",
            linewidth=1.5,
            color="#ef4444",
            visible=False
        )

        hover_x_guide, = ax.plot(
            [],
            [],
            linestyle=":",
            linewidth=1.5,
            color="#ef4444",
            visible=False
        )

        hover_y_label = ax.text(
            0,
            0,
            "",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            color=graph_text_color,
            fontweight="bold",
            visible=False,
            clip_on=False
        )

        hover_x_label = ax.text(
            0,
            -0.08,
            "",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            color=graph_text_color,
            fontweight="bold",
            visible=False,
            clip_on=False
        )

        hover_point_label = ax.text(
            0,
            0,
            "",
            ha="left",
            va="bottom",
            color=graph_text_color,
            fontweight="bold",
            fontsize=9,
            visible=False,
            clip_on=False
        )

        canvas = FigureCanvasTkAgg(
            fig,
            master=self.graph_frame
        )
        canvas.draw()
        canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        def clear_hover():
            changed = (
                hover_point.get_visible()
                or hover_y_guide.get_visible()
                or hover_x_guide.get_visible()
                or hover_y_label.get_visible()
                or hover_x_label.get_visible()
                or hover_point_label.get_visible()
            )

            hover_point.set_visible(False)
            hover_y_guide.set_visible(False)
            hover_x_guide.set_visible(False)
            hover_y_label.set_visible(False)
            hover_x_label.set_visible(False)
            hover_point_label.set_visible(False)

            for label in normal_x_labels:
                label.set_fontweight("normal")

            for label in normal_y_labels:
                label.set_fontweight("normal")

            if changed:
                canvas.draw_idle()

        def on_move(event):
            if (
                event.inaxes != ax
                or event.xdata is None
                or event.ydata is None
            ):
                clear_hover()
                return

            best_index = None
            best_distance = float("inf")

            for i, (xd, yd) in enumerate(zip(x_num, counts)):
                px, py = ax.transData.transform((xd, yd))
                distance = (
                    (event.x - px) ** 2
                    + (event.y - py) ** 2
                ) ** 0.5

                if distance < best_distance:
                    best_distance = distance
                    best_index = i

            if best_index is None or best_distance > 28:
                clear_hover()
                return

            d = dates[best_index]
            c = counts[best_index]
            x_value = x_num[best_index]

            hover_point.set_data([x_value], [c])
            hover_point.set_visible(True)

            # Horizontal segment: Y-axis -> hovered point.
            hover_y_guide.set_data(
                [ax.get_xlim()[0], x_value],
                [c, c]
            )
            hover_y_guide.set_visible(True)

            # Vertical segment: X-axis -> hovered point.
            y_bottom = ax.get_ylim()[0]
            hover_x_guide.set_data(
                [x_value, x_value],
                [y_bottom, c]
            )
            hover_x_guide.set_visible(True)

            # Only show temporary axis labels when the value/date does not
            # already have a normal axis tick. Otherwise the normal tick is
            # simply bolded below, preventing duplicate labels.
            y_tick_match = any(
                abs(float(tick_value) - c) < 0.001
                for tick_value in ax.get_yticks()
            )

            x_tick_match = any(
                abs(float(tick_value) - x_value) < 0.001
                for tick_value in ax.get_xticks()
            )

            if y_tick_match:
                hover_y_label.set_visible(False)
            else:
                hover_y_label.set_position((0, c))
                hover_y_label.set_text(str(c))
                hover_y_label.set_visible(True)

            if x_tick_match:
                hover_x_label.set_visible(False)
            else:
                hover_x_label.set_position((x_value, -0.02))
                hover_x_label.set_text(d.strftime("%b %d"))
                hover_x_label.set_visible(True)

            # Exact count beside the point.
            hover_point_label.set_position((x_value, c))
            hover_point_label.set_text(str(c))
            hover_point_label.set_visible(True)

            # Bold the corresponding normal X/Y ticks while hovering.
            for label in normal_x_labels:
                label.set_fontweight("normal")

            for label in normal_y_labels:
                label.set_fontweight("normal")

            for label, tick_value in zip(
                normal_x_labels,
                ax.get_xticks()
            ):
                if abs(float(tick_value) - x_value) < 0.001:
                    label.set_fontweight("bold")

            for label, tick_value in zip(
                normal_y_labels,
                ax.get_yticks()
            ):
                if abs(float(tick_value) - c) < 0.001:
                    label.set_fontweight("bold")

            canvas.draw_idle()

        canvas.mpl_connect(
            "motion_notify_event",
            on_move
        )

        canvas.mpl_connect(
            "figure_leave_event",
            lambda _event: clear_hover()
        )

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Always fetch a fresh copy from the logic/database layer.
        records = self.logic.get_records()

        for record_date, count in sorted(records.items(), reverse=True):
            self.history_tree.insert(
                "",
                "end",
                iid=record_date.isoformat(),
                values=(
                    record_date.strftime("%B %d, %Y"),
                    count,
                    "Double-click to edit"
                )
            )

    def on_history_double_click(self, event):
        item_id = self.history_tree.identify_row(event.y)

        if not item_id:
            return

        try:
            record_date = datetime.strptime(
                item_id,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            return

        count = self.logic.get_record(record_date)

        if count is None:
            return

        self.edit_record(
            record_date,
            count
        )

    def open_date_picker(self, parent, date_entry):
        """Open a small dependency-free calendar for selecting a date."""
        try:
            selected_date = datetime.strptime(
                date_entry.get().strip(), "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date = datetime.now().date()

        picker = tk.Toplevel(parent)
        picker.title("Select Date")
        picker.resizable(False, False)
        picker.configure(bg=self.card_bg)
        picker.transient(parent)
        picker.grab_set()

        state = {"year": selected_date.year, "month": selected_date.month}
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        header = tk.Frame(picker, bg=self.card_bg)
        header.pack(fill="x", padx=14, pady=(14, 8))

        month_label = tk.Label(
            header, bg=self.card_bg, fg=self.text,
            font=("DejaVu Sans", 11, "bold")
        )
        month_label.pack(side="left", expand=True)

        grid = tk.Frame(picker, bg=self.card_bg)
        grid.pack(padx=14, pady=(0, 14))

        def change_month(delta):
            month = state["month"] + delta
            year = state["year"]
            if month < 1:
                month, year = 12, year - 1
            elif month > 12:
                month, year = 1, year + 1
            state["month"], state["year"] = month, year
            render()

        prev_button = ttk.Button(
            header, text="‹", width=3, command=lambda: change_month(-1)
        )
        prev_button.pack(side="left", padx=(0, 8))
        next_button = ttk.Button(
            header, text="›", width=3, command=lambda: change_month(1)
        )
        next_button.pack(side="right", padx=(8, 0))

        def select(day):
            chosen = datetime(
                state["year"], state["month"], day
            ).strftime("%Y-%m-%d")
            date_entry.delete(0, tk.END)
            date_entry.insert(0, chosen)
            picker.destroy()
            date_entry.focus_set()

        def render():
            for widget in grid.winfo_children():
                widget.destroy()

            month_label.config(
                text=f"{month_names[state['month'] - 1]} {state['year']}"
            )

            weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for column, name in enumerate(weekdays):
                tk.Label(
                    grid, text=name, width=4, bg=self.card_bg,
                    fg=self.secondary_text, font=("DejaVu Sans", 8, "bold")
                ).grid(row=0, column=column, pady=(0, 6))

            import calendar
            calendar.setfirstweekday(calendar.MONDAY)
            weeks = calendar.monthcalendar(state["year"], state["month"])

            for row, week in enumerate(weeks, start=1):
                for column, day in enumerate(week):
                    if day == 0:
                        tk.Label(
                            grid, text="", width=4, bg=self.card_bg
                        ).grid(row=row, column=column, padx=2, pady=2)
                        continue

                    current = datetime(
                        state["year"], state["month"], day
                    ).date()
                    is_selected = current == selected_date
                    is_today = current == datetime.now().date()

                    button = tk.Button(
                        grid, text=str(day), width=3, relief="flat",
                        bd=0, cursor="hand2",
                        bg=self.accent if is_selected else self.card_bg,
                        fg="white" if is_selected else self.text,
                        font=("DejaVu Sans", 9, "bold" if is_today else "normal"),
                        activebackground=self.accent,
                        activeforeground="white",
                        command=lambda d=day: select(d)
                    )
                    button.grid(row=row, column=column, padx=2, pady=2)

        render()

        picker.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - picker.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - picker.winfo_height()) // 2)
        picker.geometry(f"+{x}+{y}")

    def edit_record(self, record_date, current_count):
        window = tk.Toplevel(self.root)

        window.title("Edit Record")
        window.geometry("400x410")
        window.resizable(False, False)
        window.configure(bg=self.bg)

        window.transient(self.root)
        window.update_idletasks()
        window.wait_visibility()
        window.grab_set()

        title = tk.Label(
            window,
            text="Edit Daily Record",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 17, "bold")
        )
        title.pack(pady=(25, 20))

        # -----------------------------
        # Date
        # -----------------------------
        date_label = tk.Label(
            window,
            text="Date",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 10)
        )
        date_label.pack()

        date_row = tk.Frame(window, bg=self.bg)
        date_row.pack(pady=8)

        date_entry = ttk.Entry(date_row, width=16)
        date_entry.insert(0, record_date.strftime("%Y-%m-%d"))
        date_entry.pack(side="left", padx=(0, 7))

        date_picker_button = ttk.Button(
            date_row, text="📅", width=4,
            command=lambda: self.open_date_picker(window, date_entry)
        )
        date_picker_button.pack(side="left")

        date_hint = tk.Label(
            window,
            text="Choose a date from the calendar or type YYYY-MM-DD",
            bg=self.bg, fg="#9ca3af", font=("DejaVu Sans", 8)
        )
        date_hint.pack()

        # -----------------------------
        # Count
        # -----------------------------
        count_label = tk.Label(
            window,
            text="Count",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 10)
        )
        count_label.pack(pady=(14, 0))

        count_entry = ttk.Entry(window, width=20)
        count_entry.insert(0, str(current_count))
        count_entry.pack(pady=8)
        count_entry.focus()
        count_entry.select_range(0, tk.END)

        def save():
            try:
                new_date = datetime.strptime(
                    date_entry.get().strip(),
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                messagebox.showerror(
                    "Invalid date",
                    "Please enter a valid date in YYYY-MM-DD format.",
                    parent=window
                )
                return

            try:
                count = int(count_entry.get().strip())
            except ValueError:
                messagebox.showerror(
                    "Invalid value",
                    "Please enter a whole number.",
                    parent=window
                )
                return

            if count < 0:
                messagebox.showerror(
                    "Invalid value",
                    "Count cannot be negative.",
                    parent=window
                )
                return

            if new_date != record_date and self.logic.get_record(new_date) is not None:
                messagebox.showerror(
                    "Date already exists",
                    "A record already exists for this date. Please choose another date.",
                    parent=window
                )
                return

            try:
                self.logic.update_record(record_date, new_date, count)
            except (TypeError, ValueError) as error:
                messagebox.showerror(
                    "Error",
                    str(error),
                    parent=window
                )
                return

            window.destroy()
            self.refresh_after_data_change()

        save_button = ttk.Button(
            window,
            text="Save Changes",
            style="Accent.TButton",
            command=save
        )
        save_button.pack(pady=(15, 8))

        delete_button = ttk.Button(
            window,
            text="Delete Record",
            style="Danger.TButton",
            command=lambda: self.delete_record(record_date, window)
        )
        delete_button.pack()

        window.bind("<Return>", lambda event: save())

    def delete_record(self, record_date, window=None):
        confirm = messagebox.askyesno(
            "Delete Record",
            (
                "Are you sure you want to delete the record for "
                f"{record_date.strftime('%B %d, %Y')}?"
            ),
            parent=window if window else self.root
        )

        if not confirm:
            return

        deleted = self.logic.delete_record(
            record_date
        )

        if deleted and window:
            window.destroy()

        if deleted:
            self.refresh_after_data_change()

    # =========================================================
    # ADD RECORD
    # =========================================================

    def add_record(self):
        window = tk.Toplevel(self.root)

        window.title("Add Record")
        window.geometry("400x350")
        window.resizable(False, False)
        window.configure(bg=self.bg)

        window.transient(self.root)
        window.update_idletasks()
        window.wait_visibility()
        window.grab_set()

        title = tk.Label(
            window,
            text="Add Daily Record",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 17, "bold")
        )
        title.pack(pady=(25, 18))

        # -----------------------------
        # Date
        # -----------------------------
        date_label = tk.Label(
            window,
            text="Date",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 10)
        )
        date_label.pack()

        date_row = tk.Frame(window, bg=self.bg)
        date_row.pack(pady=8)

        date_entry = ttk.Entry(date_row, width=16)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.pack(side="left", padx=(0, 7))

        date_picker_button = ttk.Button(
            date_row, text="📅", width=4,
            command=lambda: self.open_date_picker(window, date_entry)
        )
        date_picker_button.pack(side="left")

        date_hint = tk.Label(
            window,
            text="Choose a date from the calendar or type YYYY-MM-DD",
            bg=self.bg, fg="#9ca3af", font=("DejaVu Sans", 8)
        )
        date_hint.pack()

        # -----------------------------
        # Count
        # -----------------------------
        count_label = tk.Label(
            window,
            text="Count",
            bg=self.bg,
            fg=self.text,
            font=("DejaVu Sans", 10)
        )
        count_label.pack(pady=(12, 0))

        count_entry = ttk.Entry(
            window,
            width=20
        )
        count_entry.pack(pady=8)
        count_entry.focus()

        def save():
            try:
                record_date = datetime.strptime(
                    date_entry.get().strip(),
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                messagebox.showerror(
                    "Invalid date",
                    "Please enter a valid date in YYYY-MM-DD format.",
                    parent=window
                )
                return

            try:
                count = int(count_entry.get().strip())
            except ValueError:
                messagebox.showerror(
                    "Invalid value",
                    "Please enter a whole number.",
                    parent=window
                )
                return

            if count < 0:
                messagebox.showerror(
                    "Invalid value",
                    "Count cannot be negative.",
                    parent=window
                )
                return

            try:
                self.logic.add_record(
                    record_date,
                    count
                )
            except (TypeError, ValueError) as error:
                messagebox.showerror(
                    "Error",
                    str(error),
                    parent=window
                )
                return

            window.destroy()
            self.refresh_after_data_change()

        save_button = ttk.Button(
            window,
            text="Save Record",
            style="Accent.TButton",
            command=save
        )
        save_button.pack(pady=(15, 8))

        cancel_button = ttk.Button(
            window,
            text="Cancel",
            command=window.destroy
        )
        cancel_button.pack()

        window.bind(
            "<Return>",
            lambda event: save()
        )

    # =========================================================
    # DATA REFRESH
    # =========================================================

    def refresh_after_data_change(self):
        """
        Refresh the currently visible page after data changes.
        """

        if self.current_page == "Overview":
            self.update_stats()
            self.update_graph()

        elif self.current_page == "History":
            self.refresh_history()

        elif self.current_page == "Statistics":
            self.show_statistics(force=True)


# =============================================================
# RUN
# =============================================================

if __name__ == "__main__":
    from logic import TrackerLogic

    root = tk.Tk()
    database_path = Path(__file__).resolve().with_name("tracker.db")
    logic = TrackerLogic(db_path=str(database_path))

    app = DailyTrackerGUI(
        root,
        logic
    )

    root.mainloop()