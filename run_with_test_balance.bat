@echo off
REM Run the bot with test balance mode enabled

echo Setting test mode environment variables...
set DMARKET_TEST_MODE=true
set DMARKET_FIXED_BALANCE=5.00

echo Running bot with test balance $5.00...
python run.py

echo Done.
pause 