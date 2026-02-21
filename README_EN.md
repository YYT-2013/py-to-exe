# Python Source to EXE (Windows)

A simple desktop GUI tool to convert a Python script (`.py`) into a Windows executable (`.exe`) using **PyInstaller**.

- GUI: **PyQt5**
- Builder: **PyInstaller**
- Live build log + common error hints
- UI language: 简体中文 / English
- Theme: Light / Dark

## Requirements

- Windows 10/11
- Python 3.8–3.12 (tested on your environment)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## How to use

1. Select a Python source file (`.py`).
2. Select an output directory.
3. Choose build mode:
   - `--onefile` (single EXE)
   - `--onedir` (folder output)
4. Choose runtime mode:
   - `--windowed` (no console window)
   - `--console` (show console)
5. Optional settings:
   - App name (`--name`)
   - Icon (`--icon`, `.ico`)
   - Admin privilege (`--uac-admin`)
   - Clean cache (`--clean`)
   - Overwrite without prompt (`-y`)

## UPX compression

- There is only one switch now: **Use UPX compression**.
- If enabled:
  - You may set the UPX directory manually (the folder that contains `upx.exe`).
  - If left empty, the app will automatically use the **bundled UPX** in this workspace: `UPX.EXE`.
- If disabled:
  - The app will pass `--noupx` to PyInstaller.

## Output

The build output is written to the `--distpath` you selected.

## Troubleshooting

- **PyInstaller not found**
  - Run: `pip install pyinstaller`
- **Missing module** (`ModuleNotFoundError`)
  - Install the missing dependency: `pip install <module>`
- **Permission error**
  - Try enabling the admin option or run this tool as Administrator.

## Notes

- The tool runs PyInstaller via `python -m PyInstaller ...` and streams stdout/stderr to the log panel.
