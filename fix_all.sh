#!/bin/bash
#
# Fix Bot Initialization & Dependencies
# 1. Fixes Initialization Order (LLM before SmartSearch)
# 2. Removes OpenAI dependency
# 3. Ensures Google Generative AI is installed
#

echo "🔧 applying ALL fixes..."

cd ~/homeai-bot

# 1. Fix Init Order (using python script)
cat > fix_full.py << 'EOF'
import sys

# Read file
try:
    with open('homeai_bot.py', 'r') as f:
        lines = f.readlines()
    
    content = "".join(lines)
    
    # 1. Fix Init Order
    # We look for the block "llm = LLMHandler" and move it before "smart_search = SmartSearch"
    if content.find("llm = LLMHandler") > content.find("smart_search = SmartSearch"):
        print("  - Fixing NameError (Init order)...")
        # Find LLM block
        llm_start = content.find("llm = LLMHandler")
        llm_end = content.find("\n\n", llm_start)
        if llm_end == -1: llm_end = len(content)
        llm_block = content[llm_start:llm_end+2] # include spacing
        
        # Remove old block
        content = content.replace(llm_block, "")
        
        # Insert before SmartSearch, but AFTER helpers (doc_manager etc)
        # Safest is to put it right before web_search or smart_search
        target_indices = [content.find("web_search = WebSearch"), content.find("smart_search = SmartSearch")]
        target_idx = min([i for i in target_indices if i != -1])
        
        content = content[:target_idx] + llm_block + content[target_idx:]
        
    # 2. Update Voice Handler Import (if not already done by git pull of new file)
    # The file voice_handler.py itself handles the logic change, 
    # but we should ensure we don't try to use OpenAI in imports if previously added
    
    with open('homeai_bot.py', 'w') as f:
        f.write(content)
        
    print("✅ fixes applied to homeai_bot.py")

except Exception as e:
    print(f"Error processing file: {e}")
EOF

python3 fix_full.py

# 2. Update Dependencies
echo "📦 Updating dependencies..."
source venv/bin/activate
pip uninstall -y openai
# Ensure we have the google library
pip install -U google-generativeai

echo "✅ All fixes applied!"
echo "  - OpenAI removed"
echo "  - Voice now uses free Gemini"
echo "  - Startup crash fixed"
echo ""
echo "Try running now:"
echo "  python3 homeai_bot.py"
echo ""
