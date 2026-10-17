"""World Clock desktop widget: shows date and time for multiple selected time zones."""
import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from zoneinfo import ZoneInfo, available_timezones

CONFIG_PATH = Path.home() / ".worldclock_widget.json"

# Friendly "Country - City" labels for common zones; any other IANA zone is also selectable.
COUNTRY_ZONES = {
    "Argentina - Buenos Aires": "America/Argentina/Buenos_Aires",
    "Australia - Sydney": "Australia/Sydney",
    "Australia - Perth": "Australia/Perth",
    "Brazil - Sao Paulo": "America/Sao_Paulo",
    "Canada - Toronto": "America/Toronto",
    "Canada - Vancouver": "America/Vancouver",
    "China - Shanghai": "Asia/Shanghai",
    "Egypt - Cairo": "Africa/Cairo",
    "France - Paris": "Europe/Paris",
    "Germany - Berlin": "Europe/Berlin",
    "Hong Kong": "Asia/Hong_Kong",
    "India - Kolkata": "Asia/Kolkata",
    "Indonesia - Jakarta": "Asia/Jakarta",
    "Ireland - Dublin": "Europe/Dublin",
    "Italy - Rome": "Europe/Rome",
    "Japan - Tokyo": "Asia/Tokyo",
    "Kenya - Nairobi": "Africa/Nairobi",
    "Malaysia - Kuala Lumpur": "Asia/Kuala_Lumpur",
    "Mexico - Mexico City": "America/Mexico_City",
    "Netherlands - Amsterdam": "Europe/Amsterdam",
    "New Zealand - Auckland": "Pacific/Auckland",
    "Nigeria - Lagos": "Africa/Lagos",
    "Pakistan - Karachi": "Asia/Karachi",
    "Philippines - Manila": "Asia/Manila",
    "Russia - Moscow": "Europe/Moscow",
    "Saudi Arabia - Riyadh": "Asia/Riyadh",
    "Singapore": "Asia/Singapore",
    "South Africa - Johannesburg": "Africa/Johannesburg",
    "South Korea - Seoul": "Asia/Seoul",
    "Spain - Madrid": "Europe/Madrid",
    "Sri Lanka - Colombo": "Asia/Colombo",
    "Sweden - Stockholm": "Europe/Stockholm",
    "Switzerland - Zurich": "Europe/Zurich",
    "Thailand - Bangkok": "Asia/Bangkok",
    "Turkey - Istanbul": "Europe/Istanbul",
    "UAE - Dubai": "Asia/Dubai",
    "United Kingdom - London": "Europe/London",
    "USA - New York": "America/New_York",
    "USA - Chicago": "America/Chicago",
    "USA - Denver": "America/Denver",
    "USA - Los Angeles": "America/Los_Angeles",
    "USA - Honolulu": "Pacific/Honolulu",
    "UTC": "UTC",
    "Vietnam - Ho Chi Minh": "Asia/Ho_Chi_Minh",
}

DEFAULT_CONFIG = {
    "clocks": [
        {"label": "India - Kolkata", "zone": "Asia/Kolkata"},
        {"label": "USA - New York", "zone": "America/New_York"},
        {"label": "United Kingdom - London", "zone": "Europe/London"},
        {"label": "Japan - Tokyo", "zone": "Asia/Tokyo"},
    ],
    "use_24h": True,
    "always_on_top": True,
    "x": 100,
    "y": 100,
}

# tzdata only has numeric abbreviations (e.g. "+08") for these zones; none observe DST.
ZONE_ABBREVIATIONS = {
    "America/Argentina/Buenos_Aires": "ART",
    "America/Sao_Paulo": "BRT",
    "Asia/Bangkok": "ICT",
    "Asia/Colombo": "SLST",
    "Asia/Dubai": "GST",
    "Asia/Ho_Chi_Minh": "ICT",
    "Asia/Kuala_Lumpur": "MYT",
    "Asia/Riyadh": "AST",
    "Asia/Singapore": "SGT",
    "Europe/Istanbul": "TRT",
}

BG = "#1e1e2e"
ROW_BG = "#2a2a3d"
FG = "#f5f5f5"
DIM = "#a0a0b8"
ACCENT = "#7aa2f7"


def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg = {**DEFAULT_CONFIG, **data}
        cfg["clocks"] = [c for c in cfg["clocks"] if c.get("zone") in available_timezones()]
        return cfg
    except (OSError, ValueError, TypeError, AttributeError):
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError as exc:
        messagebox.showerror("World Clock", f"Could not save settings:\n{exc}")


def build_choices():
    """Return dict of display text -> zone for the picker."""
    choices = {f"{label}  ({zone})": zone for label, zone in COUNTRY_ZONES.items()}
    known = set(COUNTRY_ZONES.values())
    for zone in sorted(available_timezones()):
        if zone not in known and "/" in zone and not zone.startswith(("Etc/", "SystemV/")):
            choices[zone] = zone
    return choices


def default_label(zone):
    for label, z in COUNTRY_ZONES.items():
        if z == zone:
            return label
    return zone.split("/")[-1].replace("_", " ")


class ManageDialog(tk.Toplevel):
    """Dialog to add, remove and reorder selected time zones."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Select Time Zones")
        self.geometry("720x440")
        self.attributes("-topmost", True)
        self.choices = build_choices()
        self.clocks = [dict(c) for c in app.cfg["clocks"]]

        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="Search country / city / zone:").pack(anchor="w")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.refresh_available())
        entry = ttk.Entry(left, textvariable=self.search)
        entry.pack(fill="x", pady=4)
        entry.focus_set()
        self.available = tk.Listbox(left, selectmode="extended", exportselection=False)
        self.available.pack(fill="both", expand=True)
        self.available.bind("<Double-Button-1>", lambda _: self.add())

        mid = ttk.Frame(self, padding=8)
        mid.pack(side="left", fill="y")
        for text, cmd in (("Add >>", self.add), ("<< Remove", self.remove),
                          ("Move Up", lambda: self.move(-1)), ("Move Down", lambda: self.move(1)),
                          ("Rename", self.rename)):
            ttk.Button(mid, text=text, command=cmd).pack(fill="x", pady=3)

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Shown on widget:").pack(anchor="w")
        self.selected = tk.Listbox(right, exportselection=False)
        self.selected.pack(fill="both", expand=True, pady=4)
        ttk.Button(right, text="Save", command=self.save).pack(side="right", pady=4)
        ttk.Button(right, text="Cancel", command=self.destroy).pack(side="right", padx=4, pady=4)

        self.refresh_available()
        self.refresh_selected()

    def refresh_available(self):
        term = self.search.get().strip().lower()
        self.available.delete(0, "end")
        self.visible = [k for k in self.choices if term in k.lower()]
        for key in self.visible:
            self.available.insert("end", key)

    def refresh_selected(self):
        self.selected.delete(0, "end")
        for c in self.clocks:
            self.selected.insert("end", f"{c['label']}  ({c['zone']})")

    def add(self):
        for i in self.available.curselection():
            zone = self.choices[self.visible[i]]
            if not any(c["zone"] == zone for c in self.clocks):
                self.clocks.append({"label": default_label(zone), "zone": zone})
        self.refresh_selected()

    def remove(self):
        for i in reversed(self.selected.curselection()):
            del self.clocks[i]
        self.refresh_selected()

    def move(self, step):
        sel = self.selected.curselection()
        if not sel:
            return
        i, j = sel[0], sel[0] + step
        if 0 <= j < len(self.clocks):
            self.clocks[i], self.clocks[j] = self.clocks[j], self.clocks[i]
            self.refresh_selected()
            self.selected.selection_set(j)

    def rename(self):
        sel = self.selected.curselection()
        if not sel:
            return
        i = sel[0]
        win = tk.Toplevel(self)
        win.title("Rename")
        win.attributes("-topmost", True)
        var = tk.StringVar(value=self.clocks[i]["label"])
        e = ttk.Entry(win, textvariable=var, width=40)
        e.pack(padx=10, pady=10)
        e.focus_set()

        def ok(*_):
            name = var.get().strip()
            if name:
                self.clocks[i]["label"] = name[:60]
                self.refresh_selected()
            win.destroy()

        e.bind("<Return>", ok)
        ttk.Button(win, text="OK", command=ok).pack(pady=(0, 10))

    def save(self):
        self.app.cfg["clocks"] = self.clocks
        save_config(self.app.cfg)
        self.app.build_rows()
        self.destroy()


class WorldClockWidget:
    def __init__(self):
        self.cfg = load_config()
        self.root = tk.Tk()
        self.root.title("World Clock")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", self.cfg["always_on_top"])
        self.root.attributes("-alpha", 0.94)
        self.root.geometry(f"+{self.cfg['x']}+{self.cfg['y']}")

        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=8, pady=(6, 2))
        title = tk.Label(header, text="World Clock", bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold"))
        title.pack(side="left")
        close = tk.Label(header, text="\u2715", bg=BG, fg=DIM, cursor="hand2", font=("Segoe UI", 10))
        close.pack(side="right")
        close.bind("<Button-1>", lambda _: self.quit())
        gear = tk.Label(header, text="\u2699", bg=BG, fg=DIM, cursor="hand2", font=("Segoe UI", 11))
        gear.pack(side="right", padx=6)
        gear.bind("<Button-1>", lambda _: self.open_manager())

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", padx=8, pady=(0, 8))

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Select time zones...", command=self.open_manager)
        self.fmt_var = tk.BooleanVar(value=self.cfg["use_24h"])
        self.menu.add_checkbutton(label="24-hour format", variable=self.fmt_var, command=self.toggle_format)
        self.top_var = tk.BooleanVar(value=self.cfg["always_on_top"])
        self.menu.add_checkbutton(label="Always on top", variable=self.top_var, command=self.toggle_top)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.quit)

        for w in (self.root, header, title, self.body):
            self.bind_drag(w)

        self.rows = []
        self.build_rows()
        self.tick()

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_drag)
        widget.bind("<B1-Motion>", self.do_drag)
        widget.bind("<ButtonRelease-1>", self.end_drag)
        widget.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))

    def start_drag(self, event):
        self._dx = event.x_root - self.root.winfo_x()
        self._dy = event.y_root - self.root.winfo_y()

    def do_drag(self, event):
        self.root.geometry(f"+{event.x_root - self._dx}+{event.y_root - self._dy}")

    def end_drag(self, _event):
        self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
        save_config(self.cfg)

    def build_rows(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.rows = []
        if not self.cfg["clocks"]:
            hint = tk.Label(self.body, text="Right-click or \u2699 to add time zones", bg=BG, fg=DIM,
                            font=("Segoe UI", 9))
            hint.pack(pady=10)
            self.bind_drag(hint)
        for clock in self.cfg["clocks"]:
            row = tk.Frame(self.body, bg=ROW_BG, padx=10, pady=6)
            row.pack(fill="x", pady=3)
            name = tk.Label(row, text=clock["label"], bg=ROW_BG, fg=FG, font=("Segoe UI", 10, "bold"), anchor="w")
            name.grid(row=0, column=0, sticky="w")
            date = tk.Label(row, bg=ROW_BG, fg=DIM, font=("Segoe UI", 9), anchor="w")
            date.grid(row=1, column=0, sticky="w")
            time_lbl = tk.Label(row, bg=ROW_BG, fg=FG, font=("Consolas", 18, "bold"), anchor="e")
            time_lbl.grid(row=0, column=1, rowspan=2, sticky="e", padx=(20, 0))
            row.columnconfigure(0, weight=1)
            for w in (row, name, date, time_lbl):
                self.bind_drag(w)
            self.rows.append((ZoneInfo(clock["zone"]), date, time_lbl))
        self.update_times()

    def update_times(self):
        time_fmt = "%H:%M:%S" if self.cfg["use_24h"] else "%I:%M:%S %p"
        for tz, date_lbl, time_lbl in self.rows:
            now = datetime.now(tz)
            offset = now.strftime("%z")
            abbr = now.tzname()
            if abbr[0] in "+-":
                abbr = ZONE_ABBREVIATIONS.get(tz.key, "")
            time_lbl.config(text=now.strftime(time_fmt))
            date_lbl.config(text=f"{now.strftime('%a, %d %b %Y')}  \u2022  UTC{offset[:3]}:{offset[3:]}"
                                 f"  {abbr}".rstrip())

    def tick(self):
        self.update_times()
        self.root.after(1000 - datetime.now().microsecond // 1000, self.tick)

    def toggle_format(self):
        self.cfg["use_24h"] = self.fmt_var.get()
        save_config(self.cfg)
        self.update_times()

    def toggle_top(self):
        self.cfg["always_on_top"] = self.top_var.get()
        self.root.attributes("-topmost", self.cfg["always_on_top"])
        save_config(self.cfg)

    def open_manager(self):
        ManageDialog(self)

    def quit(self):
        self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
        save_config(self.cfg)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    WorldClockWidget().run()
