#!/bin/bash
#
# Voice Messages Integration Script
# Adds voice transcription to homeai_bot.py
#

echo "🎤 Integrating Voice Messages..."

cd ~/homeai-bot

# Backup
cp homeai_bot.py homeai_bot.py.backup4

# Add import after web_search import
sed -i '/from web_search import WebSearch, SmartSearch/a from voice_handler import VoiceHandler, VoiceCommandProcessor' homeai_bot.py

# Add initialization after web_search
sed -i '/^smart_search = SmartSearch/a \
\
# Initialize voice handler\
voice_handler = VoiceHandler()\
voice_processor = VoiceCommandProcessor(voice_handler)' homeai_bot.py

# Install dependency
echo "📦 Installing openai..."
source venv/bin/activate
pip install -q openai

echo "✅ Voice messages integrated!"
echo ""
echo "Features added:"
echo "  - Voice message transcription"
echo "  - Hands-free control"
echo "  - Multi-language support"
echo "  - Process as text commands"
echo ""
echo "⚠️  Note: Requires OPENAI_API_KEY in .env"
echo ""
echo "Next: sudo systemctl restart homeai"
echo ""
