@echo off

REM Activate the virtual environment
pushd "F:\Python scripts\n8nsummarizer"
call myenv\Scripts\activate.bat

REM Run the enhanced GUI script with Python
python main.py

REM Keep the window open if there's an error
pause
