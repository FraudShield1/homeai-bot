#!/bin/bash
#
# Debug Report Generator for HomeAI Bot
# Creates comprehensive report for troubleshooting
#

echo "🔍 Generating Debug Report..."
echo ""

REPORT_FILE="/tmp/homeai_debug_report_$(date +%Y%m%d_%H%M%S).txt"

cat > "$REPORT_FILE" << 'HEADER'
=====================================
HomeAI Bot - Debug Report
=====================================
HEADER

echo "Generated: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# System Info
echo "=== SYSTEM INFO ===" >> "$REPORT_FILE"
echo "Hostname: $(hostname)" >> "$REPORT_FILE"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)" >> "$REPORT_FILE"
echo "Python: $(python3 --version)" >> "$REPORT_FILE"
echo "Uptime: $(uptime -p)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Bot Status
echo "=== BOT STATUS ===" >> "$REPORT_FILE"
systemctl status homeai --no-pager >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

# Recent Logs
echo "=== RECENT LOGS (Last 200 lines) ===" >> "$REPORT_FILE"
tail -n 200 ~/homeai-bot/logs/bot.log >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

# Errors
echo "=== ERRORS (Last 50) ===" >> "$REPORT_FILE"
grep -E "(ERROR|Exception|Traceback)" ~/homeai-bot/logs/bot.log | tail -n 50 >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

# Database Stats
echo "=== DATABASE STATS ===" >> "$REPORT_FILE"
sqlite3 ~/homeai-bot/data/homeai.db << 'EOF' >> "$REPORT_FILE" 2>&1
.tables
SELECT 'Total Commands: ' || COUNT(*) FROM command_history;
SELECT 'Total Scenes: ' || COUNT(*) FROM scenes;
SELECT 'Total Users: ' || COUNT(*) FROM users;
EOF
echo "" >> "$REPORT_FILE"

# File Structure
echo "=== FILE STRUCTURE ===" >> "$REPORT_FILE"
ls -lh ~/homeai-bot/*.py >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

# Environment Check
echo "=== ENVIRONMENT CHECK ===" >> "$REPORT_FILE"
cd ~/homeai-bot
source venv/bin/activate
pip list | grep -E "(telegram|aiohttp|google|anthropic|pillow)" >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

# Configuration (sanitized)
echo "=== CONFIGURATION (sanitized) ===" >> "$REPORT_FILE"
cat ~/homeai-bot/.env | sed 's/=.*/=***HIDDEN***/' >> "$REPORT_FILE" 2>&1
echo "" >> "$REPORT_FILE"

echo "=====================================
Report saved to: $REPORT_FILE
=====================================" | tee -a "$REPORT_FILE"

# Display the report
cat "$REPORT_FILE"

echo ""
echo "📋 Report saved to: $REPORT_FILE"
echo ""
echo "To share with developer:"
echo "  cat $REPORT_FILE"
echo ""
