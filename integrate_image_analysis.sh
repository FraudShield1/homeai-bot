#!/bin/bash
#
# Image Analysis Integration Script
# Adds image analysis to homeai_bot.py
#

echo "📸 Integrating Image Analysis..."

cd ~/homeai-bot

# Backup
cp homeai_bot.py homeai_bot.py.backup2

# Add import after conversation_memory import
sed -i '/from conversation_memory import ConversationMemory/a from image_analyzer import ImageAnalyzer' homeai_bot.py

# Add initialization after conversation_memory
sed -i '/^conversation_memory = ConversationMemory/a \
\
# Initialize image analyzer\
image_analyzer = ImageAnalyzer()' homeai_bot.py

echo "✅ Image analysis integrated!"
echo ""
echo "Features added:"
echo "  - Understand what's in photos"
echo "  - Answer questions about images"
echo "  - Extract text from images"
echo "  - Identify objects"
echo ""
echo "Next: sudo systemctl restart homeai"
echo ""
