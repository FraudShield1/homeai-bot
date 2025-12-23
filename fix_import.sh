#!/bin/bash
#
# QUICK FIX: Update Monitor Import
#

echo "🔧 Fixing Import Error..."

cd ~/homeai-bot

# Replace 'ProactiveMonitor' with 'HomeMonitor' in imports
sed -i 's/from monitor import ProactiveMonitor/from monitor import HomeMonitor/g' homeai_bot.py

# Also fix the usage line if it exists (usually "monitor = ProactiveMonitor(...)")
sed -i 's/monitor = ProactiveMonitor/monitor = HomeMonitor/g' homeai_bot.py

echo "✅ Import Fixed."
echo "Restarting..."
python3 homeai_bot.py
