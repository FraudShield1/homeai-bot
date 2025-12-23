#!/bin/bash
#
# Conversation Memory Integration Script
# Adds conversation memory to homeai_bot.py
#

echo "🧠 Integrating Conversation Memory..."

cd ~/homeai-bot

# Backup original file
cp homeai_bot.py homeai_bot.py.backup

# Add import after database import (line 26)
sed -i '26 a from conversation_memory import ConversationMemory' homeai_bot.py

# Add initialization after database (around line 55)
sed -i '/^db = Database/a \
\
# Initialize conversation memory\
conversation_memory = ConversationMemory(db)' homeai_bot.py

echo "✅ Conversation memory integrated!"
echo ""
echo "Next steps:"
echo "1. Restart bot: sudo systemctl restart homeai"
echo "2. Test with follow-up questions"
echo ""
