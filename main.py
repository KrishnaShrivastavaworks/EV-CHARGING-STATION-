import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import deque

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "ev_station.db"
DB_PATH.parent.mkdir(exist_ok=True)

SLOT_COUNT = 4
CHARGER_KW = 7.0
RATE_PER_KWH = 8.0
SIM_SECONDS_PER_HOUR = 12  # 12 real seconds represent 1 simulated charging hour

def db_connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db_connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_no TEXT NOT NULL,
                model TEXT NOT NULL,
                start_percent REAL NOT NULL,
                end_percent REAL NOT NULL,
                battery_kwh REAL NOT NULL,
                energy_kwh REAL NOT NULL,
                cost REAL NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL
            )
        """)

class EVChargingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EV Charging Station Simulator")
        self.root.geometry("1120x760")
        self.root.minsize(980, 680)
        self.root.configure(bg="#eef2f7")
        self.slots = [None] * SLOT_COUNT
        self.queue = deque()
        self.next_id = 1
        self.total_energy = 0.0
        self.total_revenue = 0.0
        self.completed_count = 0
        self.build_style()
        self.build_ui()
        self.refresh_all()
        self.root.after(1000, self.heartbeat)

    def build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=27, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TCombobox", padding=5)

    def build_ui(self):
        header = tk.Frame(self.root, bg="#10243a", height=88)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="⚡  EV CHARGING STATION", bg="#10243a", fg="white",
                 font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=24, pady=(14, 0))
        tk.Label(header, text="Electric vehicle charging • Slot management • Energy & billing simulation",
                 bg="#10243a", fg="#c5d5e5", font=("Segoe UI", 9)).pack(anchor="w", padx=27)

        stats = tk.Frame(self.root, bg="#eef2f7")
        stats.pack(fill="x", padx=20, pady=14)
        self.stat_labels = {}
        for key, title in [("active","ACTIVE SESSIONS"),("waiting","WAITING"),("energy","ENERGY DELIVERED"),("revenue","TOTAL REVENUE")]:
            card = tk.Frame(stats, bg="white", highlightbackground="#d9e1ea", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(card, text=title, bg="white", fg="#64748b", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=13, pady=(10,2))
            value = tk.Label(card, text="0", bg="white", fg="#10243a", font=("Segoe UI", 19, "bold"))
            value.pack(anchor="w", padx=13, pady=(0,10))
            self.stat_labels[key] = value

        body = tk.Frame(self.root, bg="#eef2f7")
        body.pack(fill="both", expand=True, padx=20, pady=(0,12))
        left = tk.Frame(body, bg="#eef2f7")
        left.pack(side="left", fill="both", expand=True, padx=(0,10))
        right = tk.Frame(body, bg="white", width=330, highlightbackground="#d9e1ea", highlightthickness=1)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(left, text="CHARGING POINTS", bg="#eef2f7", fg="#10243a",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0,8))
        self.slot_frame = tk.Frame(left, bg="#eef2f7")
        self.slot_frame.pack(fill="x")
        self.slot_cards = []
        for i in range(SLOT_COUNT):
            card = tk.Frame(self.slot_frame, bg="white", highlightbackground="#d9e1ea", highlightthickness=1)
            card.grid(row=i//2, column=i%2, sticky="nsew", padx=5, pady=5)
            self.slot_frame.grid_columnconfigure(i%2, weight=1)
            tk.Label(card, text=f"CHARGER {i+1}", bg="white", fg="#64748b",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10,2))
            status = tk.Label(card, text="AVAILABLE", bg="white", fg="#16834a",
                              font=("Segoe UI", 11, "bold"))
            status.pack(anchor="w", padx=12)
            vehicle = tk.Label(card, text="No vehicle connected", bg="white", fg="#334155",
                               font=("Segoe UI", 9))
            vehicle.pack(anchor="w", padx=12, pady=(4,2))
            progress = ttk.Progressbar(card, maximum=100, length=220)
            progress.pack(fill="x", padx=12, pady=5)
            detail = tk.Label(card, text=f"{CHARGER_KW:.0f} kW • {RATE_PER_KWH:.0f} ₹/kWh",
                              bg="white", fg="#64748b", font=("Segoe UI", 8))
            detail.pack(anchor="w", padx=12, pady=(0,10))
            self.slot_cards.append((status, vehicle, progress, detail))

        tk.Label(left, text="WAITING QUEUE", bg="#eef2f7", fg="#10243a",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(14,7))
        self.queue_tree = ttk.Treeview(left, columns=("vehicle","model","battery","target"), show="headings", height=5)
        for col, label, width in [("vehicle","Vehicle No.",120),("model","Model",130),("battery","Current Battery",120),("target","Target",90)]:
            self.queue_tree.heading(col, text=label)
            self.queue_tree.column(col, width=width, anchor="center")
        self.queue_tree.pack(fill="x")

        tk.Label(right, text="REGISTER A VEHICLE", bg="white", fg="#10243a",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16,10))
        self.entries = {}
        fields = [("Vehicle number","vehicle"),("Vehicle model","model"),("Battery capacity (kWh)","capacity"),("Current battery (%)","current"),("Target battery (%)","target")]
        defaults = {"capacity":"40","current":"25","target":"90"}
        for label, key in fields:
            tk.Label(right, text=label, bg="white", fg="#475569", font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(5,2))
            ent = ttk.Entry(right)
            ent.pack(fill="x", padx=16)
            if key in defaults:
                ent.insert(0, defaults[key])
            self.entries[key] = ent
        tk.Button(right, text="＋  Add to charging queue", command=self.add_vehicle,
                  bg="#1769aa", fg="white", activebackground="#12578f", activeforeground="white",
                  relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(fill="x", padx=16, pady=(16,8), ipady=8)
        tk.Button(right, text="Start / resume selected charger", command=self.resume_selected,
                  bg="#16834a", fg="white", activebackground="#116b3c", activeforeground="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2").pack(fill="x", padx=16, pady=4, ipady=7)
        tk.Button(right, text="Pause selected charger", command=self.pause_selected,
                  bg="#d97706", fg="white", activebackground="#b45f05", activeforeground="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2").pack(fill="x", padx=16, pady=4, ipady=7)
        tk.Button(right, text="Stop & remove selected charger", command=self.stop_selected,
                  bg="#b42318", fg="white", activebackground="#941d14", activeforeground="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), cursor="hand2").pack(fill="x", padx=16, pady=4, ipady=7)

        tk.Label(right, text="SESSION CONTROLS", bg="white", fg="#64748b",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=16, pady=(18,4))
        tk.Label(right, text="Select a charger card by clicking its number below:",
                 bg="white", fg="#64748b", font=("Segoe UI", 8), wraplength=285).pack(anchor="w", padx=16)
        selector = tk.Frame(right, bg="white")
        selector.pack(anchor="w", padx=12, pady=7)
        self.selected_slot = tk.IntVar(value=0)
        for i in range(SLOT_COUNT):
            tk.Radiobutton(selector, text=f"{i+1}", variable=self.selected_slot, value=i,
                           bg="white", fg="#10243a", selectcolor="#dbeafe").pack(side="left", padx=5)

        footer = tk.Label(self.root, text="DEMO SETTINGS: 4 chargers  •  7 kW per charger  •  ₹8 per kWh  •  12 seconds = 1 simulated hour",
                          bg="#eef2f7", fg="#64748b", font=("Segoe UI", 8))
        footer.pack(pady=(0,10))

    def add_vehicle(self):
        try:
            vehicle = self.entries["vehicle"].get().strip().upper()
            model = self.entries["model"].get().strip()
            capacity = float(self.entries["capacity"].get())
            current = float(self.entries["current"].get())
            target = float(self.entries["target"].get())
            if not vehicle or not model:
                raise ValueError("Enter both vehicle number and model.")
            if capacity <= 0 or not (0 <= current < 100) or not (0 < target <= 100) or target <= current:
                raise ValueError("Capacity must be positive; target must be above current battery and at most 100%.")
            if any(v["vehicle"] == vehicle for v in self.queue) or any(s and s["vehicle"] == vehicle for s in self.slots):
                raise ValueError("This vehicle is already in the station.")
            item = {"id": self.next_id, "vehicle": vehicle, "model": model, "capacity": capacity,
                    "current": current, "start": current, "target": target, "energy": 0.0,
                    "status": "Charging", "started": datetime.now().isoformat(timespec="seconds")}
            self.next_id += 1
            free = next((i for i,s in enumerate(self.slots) if s is None), None)
            if free is not None:
                self.slots[free] = item
                messagebox.showinfo("Vehicle added", f"{vehicle} assigned to Charger {free+1}.")
            else:
                self.queue.append(item)
                messagebox.showinfo("Vehicle queued", f"{vehicle} added to waiting queue.")
            self.refresh_all()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))

    def resume_selected(self):
        i = self.selected_slot.get()
        if self.slots[i]:
            self.slots[i]["status"] = "Charging"
            self.refresh_all()

    def pause_selected(self):
        i = self.selected_slot.get()
        if self.slots[i]:
            self.slots[i]["status"] = "Paused"
            self.refresh_all()

    def stop_selected(self):
        i = self.selected_slot.get()
        item = self.slots[i]
        if not item:
            messagebox.showinfo("No session", "Selected charger is already empty.")
            return
        if messagebox.askyesno("Stop session", f"Remove {item['vehicle']} from Charger {i+1}? The partial session will not be added to completed reports."):
            self.slots[i] = None
            self.fill_free_slots()
            self.refresh_all()

    def finish_session(self, i):
        item = self.slots[i]
        if not item:
            return
        cost = item["energy"] * RATE_PER_KWH
        with db_connect() as con:
            con.execute("""INSERT INTO sessions
                (vehicle_no,model,start_percent,end_percent,battery_kwh,energy_kwh,cost,started_at,completed_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (item["vehicle"],item["model"],item["start"],item["current"],item["capacity"],
                 item["energy"],cost,item["started"],datetime.now().isoformat(timespec="seconds")))
        self.total_energy += item["energy"]
        self.total_revenue += cost
        self.completed_count += 1
        messagebox.showinfo("Charging complete",
            f"{item['vehicle']} charging completed!\nEnergy: {item['energy']:.2f} kWh\nBill: ₹{cost:.2f}")
        self.slots[i] = None
        self.fill_free_slots()

    def fill_free_slots(self):
        while self.queue and any(s is None for s in self.slots):
            i = next(i for i,s in enumerate(self.slots) if s is None)
            self.slots[i] = self.queue.popleft()

    def heartbeat(self):
        for i, item in enumerate(self.slots):
            if item and item["status"] == "Charging":
                # 1 real second = 1/SIM_SECONDS_PER_HOUR simulated hour
                added_energy = CHARGER_KW / 3600 * (3600 / SIM_SECONDS_PER_HOUR)
                remaining_percent = item["target"] - item["current"]
                max_energy = item["capacity"] * remaining_percent / 100
                added_energy = min(added_energy, max_energy)
                item["energy"] += added_energy
                item["current"] = min(item["target"], item["start"] + item["energy"] / item["capacity"] * 100)
                if item["current"] >= item["target"] - 0.0001:
                    self.finish_session(i)
        self.refresh_all()
        self.root.after(1000, self.heartbeat)

    def refresh_all(self):
        active = sum(1 for s in self.slots if s)
        self.stat_labels["active"].config(text=f"{active}/{SLOT_COUNT}")
        self.stat_labels["waiting"].config(text=str(len(self.queue)))
        self.stat_labels["energy"].config(text=f"{self.total_energy:.2f} kWh")
        self.stat_labels["revenue"].config(text=f"₹{self.total_revenue:.2f}")
        for i, card in enumerate(self.slot_cards):
            status, vehicle, progress, detail = card
            item = self.slots[i]
            if item:
                status.config(text=item["status"].upper(), fg="#16834a" if item["status"]=="Charging" else "#d97706")
                vehicle.config(text=f"{item['vehicle']} • {item['model']}  |  {item['current']:.1f}% → {item['target']:.0f}%")
                progress["value"] = item["current"]
                detail.config(text=f"{item['energy']:.2f} kWh delivered • Est. bill ₹{item['energy']*RATE_PER_KWH:.2f}")
            else:
                status.config(text="AVAILABLE", fg="#16834a")
                vehicle.config(text="No vehicle connected")
                progress["value"] = 0
                detail.config(text=f"{CHARGER_KW:.0f} kW • {RATE_PER_KWH:.0f} ₹/kWh")
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)
        for item in self.queue:
            self.queue_tree.insert("", "end", values=(item["vehicle"],item["model"],f'{item["current"]:.0f}%',f'{item["target"]:.0f}%'))

def main():
    init_db()
    root = tk.Tk()
    EVChargingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
