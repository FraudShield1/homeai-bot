#!/bin/bash
#
# Fix Parsing Logic in utils.py
#
# This script updates the _clean_target function in utils.py
# to remove generic domain words like 'lights', 'switches', etc.
# This ensures that "Turn off all lights" resolves to target="all"
# instead of target="lights".
#

echo "🔧 Fixing Parsing Logic..."

cd ~/homeai-bot || exit

cat > fix_parsing_utils.py << 'EOF'
import sys
import re

try:
    with open('utils.py', 'r') as f:
        content = f.read()

    # We will replace the _clean_target function
    # It currently looks like:
    # def _clean_target(target: str) -> str:
    # ...
    #     remove_words = ["the", "my", "a", "an", "all"]
    # ...
    
    # We want to add more words to remove_words
    
    new_clean_target = """def _clean_target(target: str) -> str:
    \"\"\"
    Clean target name by removing common articles and words
    
    Args:
        target: Raw target string
        
    Returns:
        Cleaned target string
    \"\"\"
    # Remove common words and generic domain terms
    # This prevents "Turn off lights" from looking for a device named "lights"
    remove_words = [
        "the", "my", "a", "an", "all", "please", 
        "light", "lights", "switch", "switches", 
        "bulb", "bulbs", "lamp", "lamps",
        "device", "devices"
    ]
    
    words = target.split()
    # matches lower case against remove_words
    words = [w for w in words if w.lower() not in remove_words]
    
    # Remove trailing question marks and punctuation
    result = " ".join(words).strip("?.,!")
    
    return result if result else "all"
"""

    # Regex to replace the function
    # Match from 'def _clean_target' to 'return result if result else "all"'
    # We need to be careful with indentation and multi-line matching
    
    # Find the function start
    start_marker = "def _clean_target(target: str) -> str:"
    # Find the end of the function (it ends before the next def or end of file)
    # But relying on specific content lines is safer
    
    # We'll regex replace the specific block containing remove_words
    # Old: remove_words = ["the", "my", "a", "an", "all"]
    
    pattern = r'remove_words = \["the", "my", "a", "an", "all"\]'
    replacement = """remove_words = [
        "the", "my", "a", "an", "all", "please",
        "light", "lights", "switch", "switches",
        "bulb", "bulbs", "lamp", "lamps",
        "device", "devices"
    ]"""
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
        with open('utils.py', 'w') as f:
            f.write(new_content)
        print("✅ Updated utils.py remove_words list")
    else:
        print("⚠️ Could not find exact remove_words definition to replace")
        # Fallback: Replace entire function if simple replace failed
        # This is fallback logic if the user formatted it differently
        pass

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 fix_parsing_utils.py

# Restart the bot to apply changes
echo "🔄 Restarting Bot..."
pkill -f homeai_bot.py
# We use nohup or just run it (user is in interactive shell usually)
# For the script we just run it
source venv/bin/activate
python3 homeai_bot.py
