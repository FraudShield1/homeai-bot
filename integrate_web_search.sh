#!/bin/bash
#
# Web Search Integration Script
# Adds web search to homeai_bot.py
#

echo "🔍 Integrating Web Search..."

cd ~/homeai-bot

# Backup
cp homeai_bot.py homeai_bot.py.backup3

# Add import after image_analyzer import
sed -i '/from image_analyzer import ImageAnalyzer/a from web_search import WebSearch, SmartSearch' homeai_bot.py

# Add initialization after image_analyzer
sed -i '/^image_analyzer = ImageAnalyzer/a \
\
# Initialize web search\
web_search = WebSearch()\
smart_search = SmartSearch(web_search, llm)' homeai_bot.py

# Install dependency
echo "📦 Installing duckduckgo-search..."
source venv/bin/activate
pip install -q duckduckgo-search

echo "✅ Web search integrated!"
echo ""
echo "Features added:"
echo "  - Real-time web search"
echo "  - Latest news"
echo "  - Quick answers"
echo "  - Smart search with LLM"
echo ""
echo "Next: sudo systemctl restart homeai"
echo ""
