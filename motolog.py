"""
MotoLog v3.0 - The Universal Rider's Companion
"""
import os, sys, json, datetime
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_FILE   = "motolog_data.json"
REPORT_FILE = "rider_report.txt"

def print_header():
    print(r"""
  __  __       _        _
 |  \/  | ___ | |_ ___ | |    ___   __ _
 | |\/| |/ _ \| __/ _ \| |   / _ \ / _` |
 | |  | | (_) | || (_) | |__| (_) | (_| |
 |_|  |_|\___/ \__\___/|_____\___/ \__, |
                                    |___/
  ========================================
   **  THE UNIVERSAL RIDER'S COMPANION  **
  ========================================
""")

# ── BIKE CLASS ────────────────────────────────────────────────────────

class Bike:
    def __init__(self, model, purchase_date, starting_odometer, tank_capacity,
                 maintenance_interval, km_since_service=0.0, fuel_level=None,
                 fuel_log=None, ride_log=None):
        self.model                = model
        self.purchase_date        = purchase_date
        self.starting_odometer    = starting_odometer
        self.tank_capacity        = tank_capacity
        self.maintenance_interval = maintenance_interval
        self.km_since_service     = km_since_service
        self.fuel_level           = fuel_level if fuel_level is not None else tank_capacity
        self.fuel_log             = fuel_log  if fuel_log  is not None else []
        self.ride_log             = ride_log  if ride_log  is not None else []

    @property
    def total_km(self):
        return round(sum(r["km"] for r in self.ride_log), 1)

    @property
    def total_litres(self):
        return round(sum(f["litres"] for f in self.fuel_log), 2)

    @property
    def total_cost(self):
        return round(sum(f["cost"] for f in self.fuel_log), 2)

    @property
    def current_odometer(self):
        return round(self.starting_odometer + self.total_km, 1)

    def average_efficiency(self):
        tracked = [f for f in self.fuel_log if f.get("km_this_tank") is not None]
        if tracked:
            km_sum  = sum(f["km_this_tank"] for f in tracked)
            lit_sum = sum(f["litres"]        for f in tracked)
            return round(km_sum / lit_sum, 2) if lit_sum else 0.0
        return round(self.total_km / self.total_litres, 2) if self.total_litres else 0.0

    def cost_per_km(self):
        return round(self.total_cost / self.total_km, 4) if self.total_km else 0.0

    def estimated_range(self):
        eff = self.average_efficiency()
        return round(self.fuel_level * eff, 1) if eff else 0.0

    def is_service_due(self):
        return self.km_since_service >= self.maintenance_interval

    def last_fill_odometer(self):
        return self.fuel_log[-1]["odometer"] if self.fuel_log else self.starting_odometer

    def log_ride(self, date_str, km):
        self.ride_log.append({"date": date_str, "km": km})
        self.km_since_service += km
        # Deduct estimated fuel consumed based on historical efficiency
        eff = self.average_efficiency()
        if eff:
            self.fuel_level = max(0.0, round(self.fuel_level - km / eff, 3))

    def log_refuel(self, odometer, litres, cost, date_str=None):
        if self.fuel_log and self.fuel_log[-1].get("km_this_tank") is None:
            self.fuel_log[-1]["km_this_tank"] = round(odometer - self.fuel_log[-1]["odometer"], 1)
        self.fuel_log.append({"date": date_str, "odometer": odometer, "litres": litres, "cost": cost, "km_this_tank": None})
        self.fuel_level = min(self.fuel_level + litres, self.tank_capacity)

    def reset_service_counter(self):
        self.km_since_service = 0.0

    def to_dict(self):
        return {
            "bike": {
                "model": self.model, "purchase_date": self.purchase_date,
                "starting_odometer": self.starting_odometer,
                "tank_capacity": self.tank_capacity,
                "maintenance_interval": self.maintenance_interval,
                "km_since_service": self.km_since_service,
                "fuel_level": self.fuel_level,
            },
            "fuel_log": self.fuel_log,
            "ride_log": self.ride_log,
        }

    @classmethod
    def from_dict(cls, data):
        if "bike" in data:
            b = data["bike"]
            return cls(b["model"], b.get("purchase_date", ""), b.get("starting_odometer", 0.0),
                       b["tank_capacity"], b["maintenance_interval"],
                       b.get("km_since_service", 0.0), b.get("fuel_level"),
                       data.get("fuel_log", []), data.get("ride_log", []))
        return cls(data["model"], "", 0.0, data["tank_capacity"], data["maintenance_interval"],
                   data.get("km_since_service", 0.0), data.get("fuel_level"))


# ── PERSISTENCE ───────────────────────────────────────────────────────

def save_data(vehicles, current_idx):
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump({"current_vehicle": current_idx,
                   "vehicles": [v.to_dict() for v in vehicles]}, fh, indent=4)

def load_data():
    if not os.path.exists(DATA_FILE):
        return [], 0
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if "vehicles" not in data:
            return [Bike.from_dict(data)], 0
        vehicles = [Bike.from_dict(v) for v in data["vehicles"]]
        return vehicles, data.get("current_vehicle", 0)
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"  [!] Could not read data: {exc}")
        return [], 0

def recompute_km_this_tank(bike):
    """Recalculate km_this_tank for all fuel entries from odometer diffs."""
    for i in range(len(bike.fuel_log) - 1):
        bike.fuel_log[i]["km_this_tank"] = round(
            bike.fuel_log[i + 1]["odometer"] - bike.fuel_log[i]["odometer"], 1)
    if bike.fuel_log:
        bike.fuel_log[-1]["km_this_tank"] = None


# ── INPUT HELPERS ─────────────────────────────────────────────────────

def get_float(prompt, min_val=0.0):
    while True:
        try:
            v = float(input(prompt))
            if v < min_val:
                print(f"  [X] Must be >= {min_val}.")
                continue
            return v
        except ValueError:
            print("  [X] Enter a valid number.")

def get_str(prompt):
    while True:
        v = input(prompt).strip()
        if v:
            return v
        print("  [X] Cannot be blank.")

def get_date(prompt):
    today = datetime.date.today().isoformat()
    while True:
        raw = input(prompt).strip()
        if not raw:
            return today
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
        print("  [X] Use DD/MM/YYYY or YYYY-MM-DD (Enter = today).")


# ── INITIAL SETUP ─────────────────────────────────────────────────────

def initial_setup(vehicles):
    print("\n  +==================================+")
    print("  |       ADD A VEHICLE              |")
    print("  +==================================+\n")
    model     = get_str  ("  Bike model name              : ")
    pdate     = get_date ("  Purchase date (DD/MM/YYYY)   : ")
    start_odo = get_float("  Starting odometer (km)       : ")
    capacity  = get_float("  Fuel tank capacity (L)       : ", 0.1)
    interval  = get_float("  Maintenance interval (km)    : ", 100.0)
    bike = Bike(model, pdate, start_odo, capacity, interval, fuel_level=capacity)
    vehicles.append(bike)
    idx = len(vehicles) - 1
    save_data(vehicles, idx)
    print(f"\n  [OK] '{model}' added!\n")
    return vehicles, idx


# ── CORE FEATURES ─────────────────────────────────────────────────────

def log_ride(bike, vehicles, idx):
    print("\n  ── LOG A RIDE ──────────────────────")
    date_str = get_date ("  Ride date (DD/MM/YYYY, Enter=today): ")
    km       = get_float("  Kilometres ridden            : ", 0.01)
    bike.log_ride(date_str, km)
    save_data(vehicles, idx)
    print(f"\n  [OK] {km:.1f} km logged for {date_str}.")
    print(f"       Odometer now : {bike.current_odometer:.1f} km\n")

def log_refuel(bike, vehicles, idx):
    print("\n  ── LOG A REFUEL ────────────────────")
    print(f"  Estimated odometer : {bike.current_odometer:.1f} km")
    date_str = get_date ("  Refuel date (DD/MM/YYYY, Enter=today): ")
    odometer = get_float("  Odometer at fill (km)        : ", 0.01)
    litres   = get_float("  Litres added                 : ", 0.01)
    cost     = get_float("  Total cost ($)               : ", 0.01)
    bike.log_refuel(odometer, litres, cost, date_str)
    save_data(vehicles, idx)
    print(f"\n  [OK] Refuel at {odometer:.1f} km recorded.")
    print(f"       Fuel level now : {bike.fuel_level:.2f} L\n")

def view_dashboard(bike):
    eff  = bike.average_efficiency()
    cpkm = bike.cost_per_km()
    due  = max(bike.maintenance_interval - bike.km_since_service, 0)
    W = 54
    print(f"\n  +{'=' * W}+")
    print(f"  |{'RIDER DASHBOARD':^{W}}|")
    print(f"  +{'=' * W}+")
    print(f"  |  {'Bike':<18}: {bike.model:<{W-22}}|")
    print(f"  |  {'Purchased':<18}: {bike.purchase_date:<{W-22}}|")
    print(f"  |  {'Start odometer':<18}: {str(bike.starting_odometer) + ' km':<{W-22}}|")
    print(f"  |  {'Current odometer':<18}: {str(bike.current_odometer) + ' km':<{W-22}}|")
    print(f"  |  {'Total km ridden':<18}: {str(bike.total_km) + ' km':<{W-22}}|")
    print(f"  |  {'Total litres':<18}: {str(bike.total_litres) + ' L':<{W-22}}|")
    print(f"  |  {'Total spend':<18}: {'$' + str(bike.total_cost):<{W-22}}|")
    print(f"  +{'-' * W}+")
    print(f"  |  {'Avg efficiency':<18}: {str(eff) + ' km/L':<{W-22}}|")
    print(f"  |  {'Cost per km':<18}: {'$' + str(cpkm) + '/km':<{W-22}}|")
    print(f"  +{'-' * W}+")
    print(f"  |  {'KM since service':<18}: {str(bike.km_since_service) + ' km':<{W-22}}|")
    print(f"  |  {'Next service in':<18}: {str(round(due,1)) + ' km':<{W-22}}|")
    print(f"  |  {'Fuel fills':<18}: {len(bike.fuel_log):<{W-22}}|")
    print(f"  |  {'Days logged':<18}: {len(bike.ride_log):<{W-22}}|")
    print(f"  +{'=' * W}+\n")

def view_fuel_history(bike):
    print("\n  ── FUEL HISTORY ──────────────────────────────────────────────────────")
    if not bike.fuel_log:
        print("  [!] No fuel entries logged.\n")
        return
    print(f"  {'#':<4} {'Date':<12} {'Odometer':>10} {'Litres':>8} {'Cost':>8} {'km/Tank':>9} {'km/L':>6}")
    print("  " + "-" * 65)
    for i, f in enumerate(bike.fuel_log, 1):
        kt       = f.get("km_this_tank")
        kml      = round(kt / f["litres"], 2) if kt else None
        date_str = f.get("date") or "--"
        print(f"  {i:<4} {date_str:<12} {f['odometer']:>10.1f} {f['litres']:>8.2f} "
              f"${f['cost']:>7.2f} "
              f"{str(round(kt,1)) if kt is not None else '--':>9} "
              f"{str(kml) if kml else '--':>6}")
    print()

def view_ride_history(bike):
    print("\n  ── RIDE HISTORY ────────────────────")
    if not bike.ride_log:
        print("  [!] No ride entries logged.\n")
        return
    print(f"  {'#':<4} {'Date':<14} {'KM':>8}")
    print("  " + "-" * 28)
    for i, r in enumerate(bike.ride_log, 1):
        print(f"  {i:<4} {r['date']:<14} {r['km']:>8.1f}")
    print(f"\n  Total: {bike.total_km:.1f} km over {len(bike.ride_log)} days\n")

def range_buffer(bike):
    print("\n  ── RANGE BUFFER ────────────────────")
    eff = bike.average_efficiency()
    if not eff:
        print("  [!] Log at least one full refuel cycle first.\n")
        return
    print(f"  Fuel level  : {bike.fuel_level:.2f} L")
    print(f"  Efficiency  : {eff:.2f} km/L")
    print(f"  [>>] Est. range : {bike.estimated_range():.1f} km remaining")
    if bike.fuel_level < bike.tank_capacity * 0.20:
        print("  [!] LOW FUEL WARNING -- below 20%!")
    print()

def maintenance_alert(bike, vehicles, idx):
    print("\n  ── MAINTENANCE ALERT ───────────────")
    print(f"  Interval   : {bike.maintenance_interval:.0f} km")
    print(f"  Since svc  : {bike.km_since_service:.1f} km")
    if bike.is_service_due():
        print(f"\n  [!!] OVERDUE by {bike.km_since_service - bike.maintenance_interval:.1f} km!")
        if input("  Just completed a service? (y/n): ").strip().lower() == "y":
            bike.reset_service_counter()
            save_data(vehicles, idx)
            print("  [OK] Counter reset.\n")
    else:
        print(f"\n  [OK] Next service in {bike.maintenance_interval - bike.km_since_service:.1f} km.\n")

def export_report(bike):
    eff  = bike.average_efficiency()
    now  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    svc  = "OVERDUE" if bike.is_service_due() else "OK"
    due  = max(bike.maintenance_interval - bike.km_since_service, 0)
    lines = [
        "=" * 54, "        MOTOLOG - RIDER PERFORMANCE REPORT", "=" * 54,
        f"  Generated  : {now}", f"  Bike       : {bike.model}",
        f"  Purchased  : {bike.purchase_date}  | Start odo: {bike.starting_odometer:.1f} km",
        "-" * 54, "",
        "  LIFETIME STATISTICS", "  " + "-" * 40,
        f"  Total km ridden        : {bike.total_km:.1f} km",
        f"  Current odometer       : {bike.current_odometer:.1f} km",
        f"  Total fuel consumed    : {bike.total_litres:.2f} L",
        f"  Total spend            : ${bike.total_cost:.2f}",
        f"  Fuel fills             : {len(bike.fuel_log)}",
        f"  Ride days              : {len(bike.ride_log)}", "",
        "  EFFICIENCY & COSTS", "  " + "-" * 40,
        f"  Avg efficiency         : {eff:.2f} km/L",
        f"  Cost per km            : ${bike.cost_per_km():.4f}/km",
        f"  Current fuel level     : {bike.fuel_level:.2f} L",
        f"  Estimated range        : {bike.estimated_range():.1f} km", "",
        "  MAINTENANCE", "  " + "-" * 40,
        f"  Service interval       : {bike.maintenance_interval:.0f} km",
        f"  KMs since service      : {bike.km_since_service:.1f} km",
        f"  Next service in        : {due:.1f} km",
        f"  Status                 : {svc}", "",
        "=" * 54, "  Ride safe. Stay rubber-side down.", "=" * 54,
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\n  [OK] Report saved to '{REPORT_FILE}'\n")

# ── EDIT / DELETE ─────────────────────────────────────────────────────

def edit_bike_profile(bike, vehicles, idx):
    while True:
        print("\n  ── EDIT BIKE PROFILE ───────────────")
        print(f"  1. Model            : {bike.model}")
        print(f"  2. Purchase date    : {bike.purchase_date}")
        print(f"  3. Starting odo (km): {bike.starting_odometer}")
        print(f"  4. Tank capacity (L): {bike.tank_capacity}")
        print(f"  5. Service interval : {bike.maintenance_interval} km")
        print(f"  6. KM since service : {bike.km_since_service}")
        print(f"  7. Fuel level (L)   : {bike.fuel_level}")
        print("  0. Back")
        ch = input("  Field to edit [0-7]: ").strip()
        if ch == "0":
            break
        elif ch == "1":
            bike.model = get_str("  New model name: ")
        elif ch == "2":
            bike.purchase_date = get_date("  New purchase date (DD/MM/YYYY): ")
        elif ch == "3":
            bike.starting_odometer = get_float("  New starting odometer (km): ")
        elif ch == "4":
            bike.tank_capacity = get_float("  New tank capacity (L): ", 0.1)
        elif ch == "5":
            bike.maintenance_interval = get_float("  New service interval (km): ", 100.0)
        elif ch == "6":
            bike.km_since_service = get_float("  KM since last service: ")
        elif ch == "7":
            bike.fuel_level = get_float("  Current fuel level (L): ")
        else:
            print("  [X] Invalid choice.")
            continue
        save_data(vehicles, idx)
        print("  [OK] Profile updated.")

def edit_ride_entry(bike, vehicles, idx):
    if not bike.ride_log:
        print("  [!] No rides to edit.\n")
        return
    view_ride_history(bike)
    try:
        n = int(input("  Entry # to edit (0=cancel): "))
        if n == 0:
            return
        if not (1 <= n <= len(bike.ride_log)):
            raise IndexError
        entry = bike.ride_log[n - 1]
    except (ValueError, IndexError):
        print("  [X] Invalid selection.\n")
        return
    print(f"  Editing entry {n}: {entry['date']}  {entry['km']} km")
    nd = input(f"  New date (Enter to keep '{entry['date']}'): ").strip()
    if nd:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                entry["date"] = datetime.datetime.strptime(nd, fmt).date().isoformat()
                break
            except ValueError:
                pass
    nk = input(f"  New km   (Enter to keep '{entry['km']}'): ").strip()
    if nk:
        try:
            diff = float(nk) - entry["km"]
            entry["km"] = float(nk)
            bike.km_since_service = max(0.0, bike.km_since_service + diff)
        except ValueError:
            print("  [X] Invalid km - kept original.")
    save_data(vehicles, idx)
    print("  [OK] Ride entry updated.\n")

def edit_fuel_entry(bike, vehicles, idx):
    if not bike.fuel_log:
        print("  [!] No fuel entries to edit.\n")
        return
    view_fuel_history(bike)
    try:
        n = int(input("  Entry # to edit (0=cancel): "))
        if n == 0:
            return
        if not (1 <= n <= len(bike.fuel_log)):
            raise IndexError
        entry = bike.fuel_log[n - 1]
    except (ValueError, IndexError):
        print("  [X] Invalid selection.\n")
        return
    current_date = entry.get("date") or "--"
    print(f"  Editing entry {n}: date={current_date}  odo={entry['odometer']}  {entry['litres']}L  ${entry['cost']}")
    # Edit date
    raw_date = input(f"  New date (DD/MM/YYYY, Enter to keep '{current_date}'): ").strip()
    if raw_date:
        parsed = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.datetime.strptime(raw_date, fmt).date().isoformat()
                break
            except ValueError:
                pass
        if parsed:
            entry["date"] = parsed
        else:
            print("  [X] Invalid date format - date unchanged.")
    # Edit numeric fields
    for field, label, cast in [
        ("odometer", "New odometer (km)", float),
        ("litres",   "New litres",        float),
        ("cost",     "New cost ($)",       float),
    ]:
        raw = input(f"  {label} (Enter to keep '{entry[field]}'): ").strip()
        if raw:
            try:
                entry[field] = cast(raw)
            except ValueError:
                print(f"  [X] Invalid - '{field}' unchanged.")
    recompute_km_this_tank(bike)
    save_data(vehicles, idx)
    print("  [OK] Fuel entry updated.\n")

def delete_ride_entry(bike, vehicles, idx):
    if not bike.ride_log:
        print("  [!] No rides to delete.\n")
        return
    view_ride_history(bike)
    try:
        n = int(input("  Entry # to delete (0=cancel): "))
        if n == 0:
            return
        if not (1 <= n <= len(bike.ride_log)):
            raise IndexError
        entry = bike.ride_log[n - 1]
    except (ValueError, IndexError):
        print("  [X] Invalid selection.\n")
        return
    if input(f"  Delete {entry['date']} ({entry['km']} km)? (y/n): ").strip().lower() == "y":
        bike.km_since_service = max(0.0, bike.km_since_service - entry["km"])
        bike.ride_log.pop(n - 1)
        save_data(vehicles, idx)
        print("  [OK] Ride entry deleted.\n")

def delete_fuel_entry(bike, vehicles, idx):
    if not bike.fuel_log:
        print("  [!] No fuel entries to delete.\n")
        return
    view_fuel_history(bike)
    try:
        n = int(input("  Entry # to delete (0=cancel): "))
        if n == 0:
            return
        if not (1 <= n <= len(bike.fuel_log)):
            raise IndexError
        entry = bike.fuel_log[n - 1]
    except (ValueError, IndexError):
        print("  [X] Invalid selection.\n")
        return
    if input(f"  Delete fill at {entry['odometer']} km ({entry['litres']}L  ${entry['cost']})? (y/n): ").strip().lower() == "y":
        bike.fuel_log.pop(n - 1)
        recompute_km_this_tank(bike)
        save_data(vehicles, idx)
        print("  [OK] Fuel entry deleted.\n")

def edit_delete_menu(bike, vehicles, idx):
    while True:
        print("\n  ++ EDIT / DELETE ++++++++++++++++++++")
        print("  |  1.  Edit Bike Profile           |")
        print("  |  2.  Edit Ride Entry             |")
        print("  |  3.  Edit Fuel Entry             |")
        print("  |  4.  Delete Ride Entry           |")
        print("  |  5.  Delete Fuel Entry           |")
        print("  |  0.  Back                        |")
        print("  +++++++++++++++++++++++++++++++++++++")
        ch = input("  Select [0-5]: ").strip()
        if   ch == "0": break
        elif ch == "1": edit_bike_profile(bike, vehicles, idx)
        elif ch == "2": edit_ride_entry(bike, vehicles, idx)
        elif ch == "3": edit_fuel_entry(bike, vehicles, idx)
        elif ch == "4": delete_ride_entry(bike, vehicles, idx)
        elif ch == "5": delete_fuel_entry(bike, vehicles, idx)
        else: print("  [X] Invalid option.")


# ── VEHICLE MANAGER ───────────────────────────────────────────────────

def vehicle_manager(vehicles, current_idx):
    while True:
        print("\n  ++ VEHICLE MANAGER +++++++++++++++++++")
        for i, v in enumerate(vehicles):
            tag = "  << ACTIVE" if i == current_idx else ""
            print(f"  {i+1}. {v.model}{tag}")
        print("  +++++++++++++++++++++++++++++++++++++")
        print("  S. Switch active vehicle")
        print("  A. Add new vehicle")
        print("  D. Delete a vehicle")
        print("  0. Back")
        ch = input("  Select: ").strip().upper()
        if ch == "0":
            break
        elif ch == "S":
            try:
                n = int(input(f"  Switch to # (1-{len(vehicles)}): "))
                if 1 <= n <= len(vehicles):
                    current_idx = n - 1
                    save_data(vehicles, current_idx)
                    print(f"  [OK] Switched to '{vehicles[current_idx].model}'.\n")
                else:
                    print("  [X] Out of range.")
            except ValueError:
                print("  [X] Invalid input.")
        elif ch == "A":
            vehicles, current_idx = initial_setup(vehicles)
        elif ch == "D":
            if len(vehicles) == 1:
                print("  [X] Cannot delete the only vehicle.\n")
                continue
            try:
                n = int(input(f"  Delete vehicle # (1-{len(vehicles)}): "))
                if 1 <= n <= len(vehicles):
                    name = vehicles[n - 1].model
                    if input(f"  Delete '{name}'? Cannot be undone. (y/n): ").strip().lower() == "y":
                        vehicles.pop(n - 1)
                        current_idx = min(current_idx, len(vehicles) - 1)
                        save_data(vehicles, current_idx)
                        print(f"  [OK] '{name}' deleted.\n")
                else:
                    print("  [X] Out of range.")
            except ValueError:
                print("  [X] Invalid input.")
        else:
            print("  [X] Invalid option.")
    return vehicles, current_idx


# ── MAIN MENU + ENTRY POINT ───────────────────────────────────────────

def show_menu(bike):
    fuel_pct = (bike.fuel_level / bike.tank_capacity * 100) if bike.tank_capacity else 0
    svc_warn = "  [!!] SERVICE DUE" if bike.is_service_due() else ""
    print(f"\n  [{bike.model}]  Odo: {bike.current_odometer:.1f} km  |  "
          f"Fuel: {bike.fuel_level:.1f}L ({fuel_pct:.0f}%){svc_warn}")
    print("  +--------------------------------------+")
    print("  |              MAIN MENU               |")
    print("  +--------------------------------------+")
    print("  |  1.  Log a Ride                      |")
    print("  |  2.  Log a Refuel                    |")
    print("  |  3.  View Dashboard                  |")
    print("  |  4.  Fuel History                    |")
    print("  |  5.  Ride History                    |")
    print("  |  6.  Range Buffer                    |")
    print("  |  7.  Maintenance Alert               |")
    print("  |  8.  Edit / Delete                   |")
    print("  |  9.  Export Report                   |")
    print("  |  V.  Vehicle Manager                 |")
    print("  |  0.  Exit                            |")
    print("  +--------------------------------------+")

def main():
    print_header()
    vehicles, current_idx = load_data()
    if not vehicles:
        vehicles, current_idx = initial_setup([])
    else:
        print(f"  Welcome back! Active: '{vehicles[current_idx].model}'\n")

    while True:
        bike = vehicles[current_idx]
        show_menu(bike)
        ch = input("  Select [0-9/V]: ").strip().upper()
        if   ch == "0": print("\n  Safe riding! MotoLog signing off.\n"); break
        elif ch == "1": log_ride(bike, vehicles, current_idx)
        elif ch == "2": log_refuel(bike, vehicles, current_idx)
        elif ch == "3": view_dashboard(bike)
        elif ch == "4": view_fuel_history(bike)
        elif ch == "5": view_ride_history(bike)
        elif ch == "6": range_buffer(bike)
        elif ch == "7": maintenance_alert(bike, vehicles, current_idx)
        elif ch == "8": edit_delete_menu(bike, vehicles, current_idx)
        elif ch == "9": export_report(bike)
        elif ch == "V":
            vehicles, current_idx = vehicle_manager(vehicles, current_idx)
        else:
            print("  [X] Invalid option. Enter 0-9 or V.\n")

if __name__ == "__main__":
    main()
