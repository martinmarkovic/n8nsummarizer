@echo off

REM Activate the virtual environment
pushd "F:\Python scripts\n8nsummarizer"
call myenv\Scripts\activate.bat

REM Run the enhanced GUI script with Python
python enhanced_transcribe_gui_playlist_fixed.py

REM Keep the window open if there's an error
pause
