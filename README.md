# LiteGame Optimizer

A lightweight Windows 11 desktop application built with Python to help prepare your laptop for gaming.

LiteGame Optimizer provides system monitoring, optional background process cleanup, a game launcher, and Windows power-plan controls.

**Note:** This application cannot guarantee higher FPS. Results depend on your hardware, game settings, drivers, cooling, and available system memory.

## Features

- **System Dashboard** — Monitor CPU, RAM, and system-drive usage in real time.
- **Gaming Mode** — Request an available Windows performance power plan.
- **Restore Power Plan** — Restore the power plan saved before enabling Gaming Mode during the current session.
- **Game Launcher** — Select and launch a game's executable file.
- **Process Cleanup** — Select unnecessary applications and request normal process termination.
- **Dark Desktop UI** — Modern interface built with CustomTkinter.
- **Safety-Focused Design** — No intentional registry modifications, service disabling, security changes, or hardware overclocking.

## Technologies Used

- Python
- CustomTkinter
- psutil
- Windows PowerShell-compatible command-line utilities (`powercfg`)

## Requirements

- Windows 11
- Python 3.10 or newer recommended
- Internet connection for installing dependencies

## Installation

**1. Clone the repository**

```powershell
git clone YOUR_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```

Alternatively, download the repository as a ZIP and extract it.

**2. Install dependencies**

```powershell
py -m pip install customtkinter psutil
```

**3. Run the application**

```powershell
py litegame_optimizer.py
```

## How to Use

### Gaming Mode

Select **Gaming mode** to request a performance-oriented Windows power plan when supported.

### Launch a Game

1. Click **Browse**.
2. Select the game's `.exe` file.
3. Click **Optimize & Launch** or **Launch only**.

### Clean Up Background Applications

Select applications you recognize and no longer need, then click **Close selected apps**.

Save your work before closing applications. Some processes may be protected or inaccessible.

### Restore Power Settings

Use **Restore power plan** to return to the power plan saved when Gaming Mode was first enabled during the current session.

## Safety Notes

- Do not terminate unfamiliar Windows processes.
- Do not attempt to terminate `MemCompression`; it is part of Windows memory management.
- Save open work before closing applications.
- The application does not force-kill processes that fail to exit normally.
- Performance power plans may increase heat, fan noise, and power consumption.
- Some features may be restricted by Windows or laptop manufacturer settings.

## Current Limitations

- No direct in-game FPS measurement.
- No built-in GPU temperature monitoring.
- No guarantee of increased FPS.
- Available power-plan options vary by device.
- Hardware limitations remain important, particularly on laptops with 4 GB RAM and integrated graphics.

## Project Structure

```text
LiteGame-Optimizer/
├── litegame_optimizer.py
└── README.md
```

## Contributing

Suggestions, bug reports, and improvements are welcome. Please include your Windows version, Python version, and relevant error messages when reporting issues.

## Disclaimer

LiteGame Optimizer is provided as-is, without warranties. Review the source code before running it. This project is not affiliated with Microsoft, Intel, Steam, or any game publisher.

## License

No license has been selected yet. Add a `LICENSE` file before distributing the project under an open-source license.
