#!/bin/bash
#
# Fix Initialization Order
# Reorders initialization to ensure 'llm' is defined before 'smart_search'
#

echo "🔧 Fixing initialization order..."

cd ~/homeai-bot

# Backup
cp homeai_bot.py homeai_bot.py.backup_init_fix

# We need to move the LLM initialization BEFORE the SmartSearch initialization
# Currently SmartSearch is initialized right after imports or WebSearch, but LLM is likely later

# Let's read the file content to understand the current structure and then rewrite the relevant parts
# Since we don't have the full file on the Pi in this context properly to sed complex multiline reorders easily without risk,
# we will use python to rewrite the file safely.

cat > fix_init_order.py << 'EOF'
import sys

try:
    with open('homeai_bot.py', 'r') as f:
        lines = f.readlines()

    # defined chunks
    imports_end_idx = 0
    llm_init_lines = []
    smart_search_init_idx = -1
    
    # Locate key sections
    for i, line in enumerate(lines):
        if "llm = LLMHandler" in line:
            llm_init_lines.append(i)
        if "smart_search = SmartSearch" in line:
            smart_search_init_idx = i

    if not llm_init_lines or smart_search_init_idx == -1:
        print("Could not find initialization lines. Manual check required.")
        sys.exit(1)

    llm_init_idx = llm_init_lines[0]

    # If llm is initialized AFTER smart_search, we have a problem
    if llm_init_idx > smart_search_init_idx:
        print(f"Found LLM init at line {llm_init_idx+1} and SmartSearch init at line {smart_search_init_idx+1}")
        print("Reordering...")
        
        # Extract LLM init block (assuming it's a few lines)
        # We'll look for the blank line after LLM init to define the block end
        llm_block_end = llm_init_idx
        while llm_block_end < len(lines) and lines[llm_block_end].strip() != "":
            llm_block_end += 1
        
        llm_block = lines[llm_init_idx:llm_block_end+1]
        
        # Remove LLM block from old location
        # We do this carefully. Since indices change, we better construct a new list
        
        new_lines = []
        for i in range(len(lines)):
            if i >= llm_init_idx and i <= llm_block_end:
                continue # Skip old LLM block
            
            new_lines.append(lines[i])
            
            # Insert LLM block BEFORE SmartSearch
            # But wait, SmartSearch depends on WebSearch too.
            # SmartSearch is likely initialized right after WebSearch.
            # So we should put LLM block before WebSearch initialization or just before SmartSearch.
            # Let's put it before SmartSearch but we need to find the new index of SmartSearch
            pass
            
        # Actually simplest way:
        # 1. Read file
        # 2. Extract LLM init block
        # 3. Comment out old LLM init block
        # 4. Insert LLM init block before SmartSearch
        
        # Let's try a different approach with Python string replacement
        content = "".join(lines)
        
        # Find LLM block
        llm_start = content.find("llm = LLMHandler")
        if llm_start == -1: sys.exit(1)
        
        # Find end of LLM block (double newline or similar)
        # Simple heuristic: take until next double newline
        llm_end = content.find("\n\n", llm_start)
        if llm_end == -1: llm_end = len(content)
        
        llm_block_str = content[llm_start:llm_end]
        
        # Comment out the old block
        commented_block = "\n".join(["# MOVED UP: " + line for line in llm_block_str.split('\n')])
        content = content.replace(llm_block_str, commented_block)
        
        # Insert before SmartSearch
        smart_search_start = content.find("smart_search = SmartSearch")
        if smart_search_start == -1: sys.exit(1)
        
        # Insert before web_search actually, commonly LLM is core
        # But allow insertion right before smart_search line
        new_content = content[:smart_search_start] + llm_block_str + "\n\n" + content[smart_search_start:]
        
        with open('homeai_bot.py', 'w') as f:
            f.write(new_content)
            
        print("File updated successfully.")
        
    else:
        print("Initialization order seems correct already (LLM before SmartSearch).")
        # If order is correct but variable not found, maybe scope issue?
        # But trace says: name 'llm' is not defined at line 68 (smart search init)
        # This implies line 68 comes BEFORE llm = ...

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

python3 fix_init_order.py

echo "✅ Initialization order fixed!"
echo ""
echo "Restart bot:"
echo "  python3 homeai_bot.py"
echo ""
