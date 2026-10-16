# RAM Optimizer

A small Windows tool (Python) that shows live RAM use, lists the biggest processes,
manages startup apps, and trims memory from idle background processes when RAM is tight.

## What it does
- Live RAM meter.
- Process list sorted by RAM: search by name or PID, choose how many to show (15 by default, up to All),
  scrollable, with a Close button (protected system processes are greyed out and refused).
- Startup manager for apps in `HKCU\...\Run` (toggle on/off; nothing is deleted).
- Smart clean: trims the working set of large, non-protected, non-foreground processes.
  The "freed" amount is the real change in system available memory, measured after a
  2-second settle delay (not a sum of per-process numbers, which double-counts shared memory).
- Exclude list: apps that Smart clean and auto mode never trim (a game, a video editor).
  Add an app by selecting it in the process list and pressing "Never trim"; remove it from the list below.
- Auto mode: checks every few seconds and runs Smart clean when RAM use passes your threshold,
  then waits for a cooldown.

## System tray
- A tray icon (near the clock) shows RAM use on hover. Left-click opens the window; right-click gives
  Open, Smart clean now, Auto mode (checkbox) and Quit.
- With "Close button hides to tray" on (default), the X button hides the window and the app keeps
  running, so auto mode keeps working. Use Quit in the tray menu to really exit.
- `python main.py --minimized` starts hidden in the tray.
- Only one copy can run at a time.
- If the tray cannot start, the app works as before and the X button quits.

## What it does not do
- No registry cleaning, no service disabling, no Defender/UAC/update changes.
- No standby-list clearing (needs admin and is easy to get wrong).
- HKLM startup entries are not managed (they need admin rights).

## Honest note about RAM "optimization"
Windows deliberately uses spare RAM as cache, so a high usage number is normal. Trimming moves idle
pages out of a process's working set; Windows reloads them on demand. It helps when RAM is genuinely
full, and can make apps slightly slower to wake otherwise. That is why Smart clean only runs
automatically above your threshold. The best long-term fixes are fewer startup apps and closing
memory-hungry programs.

## Run
```
pip install -r requirements.txt
python main.py
```
Settings and the log live in `%APPDATA%\RamOptimizer` (`config.json`, `ram_optimizer.log`).

## Tests
```
python -m pytest
```
Tests use mocks, so they run on any OS. Real behavior must be checked on Windows.

## Build an .exe

```
python -m pip install pyinstaller
python -m PyInstaller --noconsole --onefile --name RamOptimizer --collect-all customtkinter --hidden-import pystray._win32 main.py
```

The exe is created at `dist\RamOptimizer.exe`.

Notes:
- Use `python -m ...` so it works even if Python's Scripts folder isn't on your PATH. The module name is `PyInstaller` (capital P and I).
- Windows SmartScreen may warn about an unsigned exe. Click **More info**, then **Run anyway**.
- If the exe closes immediately, rebuild with `--console` instead of `--noconsole` and run it from a terminal to see the error.

Unsigned exes may trigger SmartScreen or antivirus warnings.
