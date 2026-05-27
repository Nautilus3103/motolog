# 🏍 MotoLog: The Universal Rider's Companion

A terminal-based Python application that helps motorcyclists track fuel
efficiency, maintenance schedules, and riding expenses — across multiple vehicles.

---

## Requirements

- **Python 3.8+**
- Standard library only (`os`, `json`, `datetime`)

---

## How to Run

```bash
python motolog.py
```

---

## File Layout

| File                  | Purpose                                                   |
|-----------------------|-----------------------------------------------------------|
| `motolog.py`          | Main application source code                              |
| `motolog_data.json`   | Auto-generated — persists all vehicles, rides, and fuel logs |
| `rider_report.txt`    | Auto-generated — exported report (option 9)               |

---

## Features

| Option | Feature              | Description                                                  |
|--------|----------------------|--------------------------------------------------------------|
| `1`    | Log a Ride           | Record km ridden with a date (DD/MM/YYYY or Enter for today) |
| `2`    | Log a Refuel         | Record odometer reading, litres added, and cost paid         |
| `3`    | View Dashboard       | Full stats: odometer, km ridden, litres, spend, efficiency   |
| `4`    | Fuel History         | Per-fill table: odometer, litres, cost, km/tank, km/L        |
| `5`    | Ride History         | Per-day ride log with dates and distances                    |
| `6`    | Range Buffer         | Estimate km remaining based on fuel level and efficiency     |
| `7`    | Maintenance Alert    | Check/reset service interval counter                         |
| `8`    | Edit / Delete        | Edit or delete any ride, fuel, or bike profile entry         |
| `9`    | Export Report        | Write a formatted stats report to `rider_report.txt`         |
| `V`    | Vehicle Manager      | Switch between, add, or delete vehicles                      |
| `0`    | Exit                 | Quit the program                                             |

---

## First-Time Setup

On the very first run (or when adding a new vehicle), the program prompts:

```
  Bike model name              : Royal Enfield Super Meteor 650
  Purchase date (DD/MM/YYYY)   : 20/04/2026
  Starting odometer (km)       : 63.8
  Fuel tank capacity (L)       : 15.5
  Maintenance interval (km)    : 5000
```

All data is saved immediately and loaded automatically on future runs.

---

## Data Persistence

Everything is stored in a single **`motolog_data.json`** file with this structure:

```json
{
    "current_vehicle": 0,
    "vehicles": [
        {
            "bike": {
                "model": "...",
                "purchase_date": "YYYY-MM-DD",
                "starting_odometer": 63.8,
                "tank_capacity": 15.5,
                "maintenance_interval": 5000.0,
                "km_since_service": 0.0,
                "fuel_level": 15.5
            },
            "fuel_log": [
                {"odometer": 178.9, "litres": 12.0, "cost": 23.99, "km_this_tank": 235.4}
            ],
            "ride_log": [
                {"date": "2026-04-20", "km": 39.8}
            ]
        }
    ]
}
```

- **Totals** (`total_km`, `total_litres`, `total_cost`) are always computed live
  from the logs — never stored redundantly.
- **`km_this_tank`** on each fuel entry = distance from that fill to the next fill.
  This is auto-computed when a new refuel is logged and is used for efficiency calculations.
- The file is updated after **every** action.

---

## Multi-Vehicle Support

Press **`V`** from the main menu to open the Vehicle Manager:

- **S** — Switch the active vehicle
- **A** — Add a new vehicle (runs the setup wizard)
- **D** — Delete a vehicle (cannot delete the last remaining one)

The menu header always shows the currently active vehicle name, odometer, and fuel level.

---

## Edit & Delete

Press **`8`** from the main menu to open the Edit / Delete submenu:

| Option | Action              | Notes                                                         |
|--------|---------------------|---------------------------------------------------------------|
| `1`    | Edit Bike Profile   | Change model, dates, tank size, service interval, fuel level  |
| `2`    | Edit Ride Entry     | Pick by number; change date and/or km                         |
| `3`    | Edit Fuel Entry     | Pick by number; change odometer, litres, or cost. `km_this_tank` is recomputed automatically for all adjacent entries |
| `4`    | Delete Ride Entry   | Removes entry; `km_since_service` adjusts automatically       |
| `5`    | Delete Fuel Entry   | Removes entry; `km_this_tank` chain recomputed automatically  |

---

## Fuel Efficiency Calculation

Efficiency (km/L) is calculated **per fill** using the bracket value in the fuel log:

- When a new refuel is logged at odometer X, the **previous** entry's `km_this_tank`
  is set to `X − previous_odometer`.
- Average efficiency = total `km_this_tank` ÷ total litres (for completed fills only).

This matches the manual calculation method: fill at 414.3 km → previous fill at
178.9 km → `km_this_tank = 414.3 − 178.9 = 235.4 km`.

---

## Input Validation

- All numeric inputs loop until a valid number ≥ the required minimum is entered.
- Dates accept `DD/MM/YYYY` or `YYYY-MM-DD`; pressing Enter defaults to today.
- Invalid choices display a clear `[X]` error without crashing.
