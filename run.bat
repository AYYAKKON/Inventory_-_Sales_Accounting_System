@echo off
echo Starting the Inventory Management System...

REM Check if the virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found. Please set it up first.
    pause
    exit /b 1
)

REM Activate the virtual environment
echo Activating virtual environment...
call .\.venv\Scripts\activate.bat

REM Run the development server
echo Starting Django development server...
python manage.py runserver

pause
