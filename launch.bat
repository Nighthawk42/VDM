@echo off
:: Launch script for the Virtual Dungeon Master project

:: Set the title for this console window
title Virtual Dungeon Master Launcher

:: Use 'uv run' to execute main.py
:: This command automatically detects the pinned Python version (.python-version)
:: and activates the virtual environment (.venv) for the script.
uv run python main.py
echo Press any key to close this window...
pause > nul