#!/bin/bash
echo "Activating A-Share Quantitative Trading System Virtual Environment"
source .venv/bin/activate
echo "Virtual environment activated successfully"
echo
echo "Common commands:"
echo "  python main_quantitative_system.py  # Run main quantitative system"
echo "  python simulation/main.py           # Run real-time simulation system"
echo "  deactivate                          # Exit virtual environment"
echo
exec bash
