#!/bin/bash
#
# 🧠 MEGA INTELLIGENCE FIX (Parsing + Logic)
#
# This script applies TWO critical fixes:
# 1. Updates utils.py to correctly strip "lights", "switches" from targets.
# 2. Updates homeai_bot.py to ask LLM if Regex fails to find devices.
#

echo "🧠 Applying Mega Intelligence Fix..."
cd ~/homeai-bot || exit

# ---------------------------------------------------------
# 1. FIX PARSING (utils.py)
# ---------------------------------------------------------
cat > utils_patch.py << 'EOF'
import sys

try:
    with open('utils.py', 'r') as f:
        content = f.read()

    # Define the better clean_target function
    new_clean_target = """def _clean_target(target: str) -> str:
    \"\"\"
    Clean target name by removing common articles and words
    \"\"\"
    # Expanded ignore list to fix "Turn off all lights" mismatch
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
    
    # We replace the old function. It starts with 'def _clean_target' and ends with 'return result if result else "all"'
    # But regex replace of the Whole function is safer if we match signatures.
    
    # Find start
    import re
    # We match the entire function body by looking for the next def or end of file
    # This regex looks for 'def _clean_target' ... until ... 'def ' or end of string
    pattern = r"(def _clean_target\(target: str\) -> str:.*?)(?=\n\n\ndef |\Z)"
    
    if re.search(pattern, content, re.DOTALL):
        # We replace the whole function
        new_content = re.sub(pattern, new_clean_target, content, flags=re.DOTALL)
        with open('utils.py', 'w') as f:
            f.write(new_content)
        print("✅ Fixed utils.py Parsing Logic")
    else:
        # Fallback: Just append/overwrite if we can't match? No, unsafe.
        # Let's try matching just the remove_words line
        short_pattern = r'remove_words = \["the", "my", "a", "an", "all"\]'
        replacement = """remove_words = ["the", "my", "a", "an", "all", "please", "light", "lights", "switch", "switches", "bulb", "bulbs", "lamp", "lamps", "device", "devices"]"""
        if re.search(short_pattern, content):
            new_content = re.sub(short_pattern, replacement, content)
            with open('utils.py', 'w') as f:
                f.write(new_content)
            print("✅ Fixed utils.py Parsing Logic (Simple Patch)")
        else:
            print("⚠️ Could not patch utils.py (no match)")

except Exception as e:
    print(f"❌ Error patching utils: {e}")
EOF

python3 utils_patch.py

# ---------------------------------------------------------
# 2. FIX LOGIC (homeai_bot.py)
# ---------------------------------------------------------
cat > logic_patch.py << 'EOF'
import re

# The new robust function
new_function = """
async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "Handle natural language commands with smart LLM fallback"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    message_text = update.message.text.lower().strip()
    
    # 1. Quick Scene Shortcuts
    if message_text in ["gm", "good morning"]:
        await activate_scene_by_name(update, "morning")
        return
    elif message_text in ["leaving", "goodbye", "bye"]:
        await activate_scene_by_name(update, "away")
        return
    elif message_text in ["movie mode", "movie time"]:
        await activate_scene_by_name(update, "movie")
        return
    elif message_text in ["good night", "gn"]:
        await activate_scene_by_name(update, "night")
        return
    
    # 2. Initial Parsing (Rule-based)
    command_info = parse_natural_command(message_text)
    used_llm = False
    
    # If Regex failed completely (command_info is None), go straight to LLM
    if not command_info:
        if llm.enabled:
            progress_msg = await update.message.reply_text("🤔 Analyzing...")
            states = await ha.get_all_states()
            # Provide simple context
            lights = [s for s in states if s.get("entity_id", "").startswith("light.")]
            context_data = {
                "light_count": len(lights),
                "lights_on": sum(1 for l in lights if l.get("state") == "on"),
                "sample_devices": [s.get("attributes", {}).get("friendly_name", s.get("entity_id")) for s in states[:20]]
            }
            command_info = await llm.analyze_command(message_text, context_data)
            await progress_msg.delete()
            used_llm = True
        
        if not command_info:
            await update.message.reply_text("🤷 I didn't understand that. Try 'turn on lights' or /help.")
            return

    # 3. Execution Helper
    async def execute_command(cmd_info, is_retry=False):
        action = cmd_info.get("action")
        domain = cmd_info.get("domain")
        target = cmd_info.get("target")
        value = cmd_info.get("value")
        
        # Fetch current states
        states = await ha.get_all_states()
        
        # Filter by domain
        candidates = []
        if domain == "light":
            candidates = [s for s in states if s.get("entity_id", "").startswith("light.")]
        elif domain == "climate":
            candidates = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        elif domain == "lock":
            candidates = [s for s in states if s.get("entity_id", "").startswith("lock.")]
        elif domain == "cover":
            candidates = [s for s in states if s.get("entity_id", "").startswith("cover.")]
        elif domain == "switch":
            candidates = [s for s in states if s.get("entity_id", "").startswith("switch.")]
        else:
            candidates = states

        # Filter by target
        final_devices = []
        if target and target not in ["all", "everything", "house", "home"]:
            target_clean = target.lower().replace("lights","").replace("switches","").strip()
            if not target_clean: target_clean = "all" # Handled below
            
            if target_clean != "all":
                for d in candidates:
                    eid = d.get("entity_id", "").lower()
                    name = d.get("attributes", {}).get("friendly_name", "").lower()
                    if target_clean in eid or target_clean in name:
                        final_devices.append(d)
        else:
            final_devices = candidates

        if not final_devices:
            # 4. SMART FALLBACK: If Regex failed to find devices, ask LLM!
            NONLOCAL_LLM_ENABLED = llm.enabled 
            if not is_retry and NONLOCAL_LLM_ENABLED:
                progress_msg = await update.message.reply_text(f"🔍 Can't find '{target}'. Asking AI...")
                
                device_names = [d.get("attributes", {}).get("friendly_name", d.get("entity_id")) for d in candidates]
                ctx = {
                    "error": f"Regex target '{target}' matched nothing.",
                    "available_devices": device_names[:50] 
                }
                
                new_cmd = await llm.analyze_command(message_text, ctx)
                await progress_msg.delete()
                
                if new_cmd:
                    return await execute_command(new_cmd, is_retry=True)
            
            await update.message.reply_text(f"❌ No {domain} devices found matching '{target}'.")
            return

        # Execute
        success_count = 0
        if action in ["turn_on", "on", "open", "unlock"]:
             svc = "turn_on"
             if domain == "cover": svc = "open_cover"
             if domain == "lock": svc = "unlock"
             for d in final_devices:
                 if await ha.call_service(domain, svc, d["entity_id"]): success_count += 1
                    
        elif action in ["turn_off", "off", "close", "lock"]:
             svc = "turn_off"
             if domain == "cover": svc = "close_cover"
             if domain == "lock": svc = "lock"
             for d in final_devices:
                 if await ha.call_service(domain, svc, d["entity_id"]): success_count += 1
                    
        elif action == "set_temperature" and value:
             for d in final_devices:
                 await ha.call_service(domain, "set_temperature", d["entity_id"], {"temperature": float(value)})
                 success_count += 1
                 
        target_name = target if target else "all"
        await update.message.reply_text(f"✅ Executed '{action}' on {success_count}/{len(final_devices)} devices ({target_name}).")
        db.log_command(update.effective_user.id, message_text, "natural_language", True)

    await execute_command(command_info)
"""

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # We match the function signature and replace the whole block until the next definition
    # The next definition is 'async def proactive_alert_callback'
    
    pattern = r"(async def handle_natural_language\(.*?:)(.*?)(?=\nasync def proactive_alert_callback)"
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_function + "\n\n\n", content, count=1, flags=re.DOTALL)
        with open('homeai_bot.py', 'w') as f:
            f.write(new_content)
        print("✅ Fixed homeai_bot.py Logic")
    else:
        print("⚠️ Could not patch homeai_bot.py (Pattern mismatch)")

except Exception as e:
    print(f"❌ Error patching bot logic: {e}")
EOF

python3 logic_patch.py

echo "🔄 Restarting..."
pkill -f homeai_bot.py
source venv/bin/activate
python3 homeai_bot.py
