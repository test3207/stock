@echo off
echo Activating A-Share Quantitative Trading System Virtual Environment
call .venv\Scripts\activate.bat
echo Virtual environment activated successfully
echo.
echo Common commands:
echo   python main_quantitative_system.py  # Run main quantitative system
echo   python simulation/main.py           # Run real-time simulation system  
echo   deactivate                          # Exit virtual environment
echo.
cmd /k
