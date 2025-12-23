#!/bin/bash
#
# Fix Gemini Model Name
# Changes gemini-1.5-flash to gemini-pro for compatibility
#

echo "🔧 Fixing Gemini model name..."

cd ~/homeai-bot

# Backup
cp llm_handler.py llm_handler.py.backup_model_fix

# Replace model name
sed -i "s/'gemini-1.5-flash'/'gemini-pro'/g" llm_handler.py

echo "✅ Fixed! Gemini model changed to 'gemini-pro'"
echo ""
echo "Restart bot to apply fix:"
echo "  sudo systemctl restart homeai"
echo "  OR"
echo "  Ctrl+C and restart python3 homeai_bot.py"
echo ""
