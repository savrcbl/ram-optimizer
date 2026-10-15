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
  Add them by selecting a process and pressing "Never trim", or type a name like `game.exe`.
- Auto mode: checks every few seconds and runs Smart clean when RAM use passes your threshold,
  then waits for a cooldown.

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
pytest
```
Tests use mocks, so they run on any OS. Real behavior must be checked on Windows.

## Build an .exe
```
pip install pyinstaller
pyinstaller --noconsole --onefile main.py
```
Unsigned exes may trigger SmartScreen or antivirus warnings.
