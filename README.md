# EV Charging Station Simulation (Python)

A ready-to-run college mini project using Python Tkinter and SQLite.

## Features
- GUI dashboard with 4 charging points
- Vehicle registration (number, model, battery capacity, current and target charge)
- Automatic charger allocation and waiting queue
- Live battery charging simulation with pause/resume/stop controls
- Energy consumption and estimated bill calculation
- Completed charging sessions saved in `data/ev_station.db`

## Requirements
- Windows 10/11
- Python 3.9 or newer (recommended)
- Tkinter (normally included with the Windows Python installer)

## Run on Windows
1. Extract the ZIP file.
2. Open the extracted `EV_Charging_Station` folder.
3. Double-click `run.bat`.
4. The app opens. Register a vehicle and watch its battery percentage increase.

If Windows blocks the script, open PowerShell in this folder and run:
```powershell
python main.py
```

## Demo settings
- 4 charging points
- 7 kW per charger
- Electricity rate: ₹8 per kWh
- Simulation speed: 12 real seconds represent 1 simulated charging hour

These are demonstration assumptions, not live charger specifications or actual electricity tariffs.

## How to demonstrate
1. Add a vehicle, e.g. `MP09AB1234`, model `Tata Nexon EV`, capacity `40`, current `25`, target `35`.
2. It is assigned to an available charger.
3. Add five vehicles to see the waiting queue after all four chargers are occupied.
4. Pause and resume a selected charger using the charger number selector.
5. When a session completes, a bill is displayed and the session is stored in SQLite.

## Project files
- `main.py` - complete GUI and simulation logic
- `data/` - SQLite database is created automatically on first run
- `run.bat` - Windows one-click launcher
- `requirements.txt` - Python package list

## Important
This is a software simulation for academic demonstration. It does not connect to physical EV chargers, vehicles, payment gateways, or the electricity grid.
