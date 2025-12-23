#!/bin/bash
#
# Enhance Natural Language Logic with Smart Fallback
#
# This script replaces the handle_natural_language function in homeai_bot.py
# with an improved version that:
# 1. Tries Regex first (fast).
# 2. If Regex fails OR finds no matching devices, falls back to LLM (smart).
# 3. Uses context-aware device lookup.
#

echo "🧠 Enhancing Bot Intelligence..."

cd ~/homeai-bot || exit

cat > fix_nl_logic.py << 'EOF'
import re
import sys

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
    
    # If Regex failed completely, go straight to LLM
    if not command_info:
        if llm.enabled:
            progress_msg = await update.message.reply_text("🤔 Analyzing...")
            states = await ha.get_all_states()
            # Provide simple context to save tokens
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

    # 3. Device Lookup & Execution
    # We define a helper to find devices based on current command_info
    
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
            # improved fuzzy matching
            target_clean = target.lower()
            for d in candidates:
                eid = d.get("entity_id", "").lower()
                name = d.get("attributes", {}).get("friendly_name", "").lower()
                if target_clean in eid or target_clean in name:
                    final_devices.append(d)
        else:
            final_devices = candidates

        if not final_devices:
            # 4. SMART FALLBACK: If Regex failed to find devices, ask LLM!
            NONLOCAL_LLM_ENABLED = llm.enabled # access global
            if not is_retry and NONLOCAL_LLM_ENABLED:
                progress_msg = await update.message.reply_text(f"🔍 Can't find '{target}'. Asking AI...")
                
                # Give LLM a list of friendly names to match against
                device_names = [d.get("attributes", {}).get("friendly_name", d.get("entity_id")) for d in candidates]
                ctx = {
                    "error": f"User said '{message_text}' but regex target '{target}' matched nothing.",
                    "available_devices_in_domain": device_names[:50] 
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
            service_cmd = "turn_on"
            if domain == "cover": service_cmd = "open_cover"
            if domain == "lock": service_cmd = "unlock"
            
            for d in final_devices:
                if await ha.call_service(domain, service_cmd, d["entity_id"]):
                    success_count += 1
                    
        elif action in ["turn_off", "off", "close", "lock"]:
            service_cmd = "turn_off"
            if domain == "cover": service_cmd = "close_cover"
            if domain == "lock": service_cmd = "lock"
            
            for d in final_devices:
                if await ha.call_service(domain, service_cmd, d["entity_id"]):
                    success_count += 1
                    
        elif action == "set_temperature" and value:
            for d in final_devices:
                if await ha.call_service(domain, "set_temperature", d["entity_id"], {"temperature": float(value)}):
                    success_count += 1

        # Feedback
        target_name = target if target else "all"
        await update.message.reply_text(f"✅ Executed '{action}' on {success_count}/{len(final_devices)} devices ({target_name}).")
        db.log_command(update.effective_user.id, message_text, "natural_language", True)

    # Start Execution
    await execute_command(command_info)

"""

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()
    
    # We replace the old handle_natural_language function
    # Regex to capture the function definition
    pattern = r"async def handle_natural_language\(.*?\).*?# Execute command"
    # This is tricky because the old function is long. 
    # Better approach: Find start of function and end of function by indentation/next def
    
    # Finds "async def handle_natural_language" and consumes everything until the next "async def" or "def"
    # WARNING: This assumes handle_natural_language is not the last function.
    # In the file viewed earlier, proactive_alert_callback comes after.
    
    start_pattern = r"(async def handle_natural_language\(.*?:)"
    next_def_pattern = r"(async def proactive_alert_callback)"
    
    # We construct a regex that matches everything between them
    full_pattern = start_pattern + r".*?" + next_def_pattern
    
    match = re.search(full_pattern, content, re.DOTALL)
    if match:
        # We replace the entire block with new_function + next_def
        # But we need to be careful about not duplicating the next function def line
        
        # Actually, simply injecting the new function logic might be safer if we overwrite the whole file
        # But for robustness let's try to match the block
        
        # Let's locate the index
        start_idx = match.start(1)
        end_idx = match.start(2)
        
        new_content = content[:start_idx] + new_function + "\n\n\n" + content[end_idx:]
        
        with open('homeai_bot.py', 'w') as f:
            f.write(new_content)
        print("✅ Successfully updated handle_natural_language logic")
        
    else:
        print("⚠️ Could not find function boundaries. Patch failed.")
        # Fallback: Append to end? No, that would duplicate.
        # We abort if we can't cleanly replace.

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 fix_nl_logic.py

echo "🔄 Restarting Bot..."
pkill -f homeai_bot.py
# Using nohup pattern would be better but simple run is what user expects
# user handles the loop
source venv/bin/activate
python3 homeai_bot.py
