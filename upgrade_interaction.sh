#!/bin/bash
#
# Upgrade Interaction Model
# Implementation of "Dashboard + Personality"
#
# Changes:
# 1. Modifies "Hi" logic to send /status report FIRST (fast check)
# 2. Then sends LLM commentary SECOND (smart check)
#

echo "🚀 Upgrading Interaction Model..."

cd ~/homeai-bot

cat > upgrade_interaction.py << 'EOF'
import sys

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # We want to change the "Greeting" block we added earlier.
    # It looked like this:
    # if message_text.lower() in ["hi", "hello", ...]:
    #     ... response = await llm.chat(...) ...
    
    # We want it to be:
    # if message_text.lower() in ["hi", "hello", ...]:
    #     # 1. Send Status (Fast)
    #     await status_command(update, context)
    #     
    #     # 2. Send Smart Commentary (Slow/Brain)
    #     if llm.enabled:
    #          response = await llm.chat("Here is the current home status. Give me a brief, punchy commentary on it.", context=home_context)
    #          await update.message.reply_text(response)
    #     return
    
    # LOCATE THE BLOCK
    # We will look for the simplified block we might have injected or the standard one
    
    # To be safe, let's just REPLACE the handle_natural_language function AGAIN with the evolved version.
    # This is safer than patching patches.
    
    new_handler = """
async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    \"\"\"
    Unified Natural Language Handler (Dual-Mode)
    \"\"\"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # 0. Typing indicator
    await update.message.reply_chat_action("typing")

    try:
        # A. Gather Context
        history = []
        if 'conversation_memory' in globals() and conversation_memory:
            history = conversation_memory.get_history(user_id)
        
        home_context = {}
        try:
            states = await ha.get_all_states()
            home_context = {
                "lights_active": sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on"),
                "total_lights": sum(1 for s in states if s.get("entity_id", "").startswith("light.")),
                "temperature": next((s.get("state") for s in states if "temperature" in s.get("entity_id", "")), "unknown"),
                "doors_open": [s.get("attributes", {}).get("friendly_name") for s in states if "door" in s.get("entity_id", "") and s.get("state") in ["on", "open"]]
            }
        except: pass

        # B. FAST PATH: Greetings -> STATUS + CHAT
        if message_text.lower() in ["hi", "hello", "hey", "start", "yo", "gm", "gn", "hola", "status"]:
            
            # 1. Run Standard Status Command (The "Quick Check")
            await status_command(update, context)
            
            # 2. Run Brain Commentary (The "Personality")
            if llm.enabled:
                # We ask the LLM specifically to comment on the state we just showed
                prompt = f"The user just checked status. Comment on this home state: {home_context}. Be brief and brutally honest."
                response = await llm.chat(prompt, context={"home": home_context})
                
                await update.message.reply_text(response)
                
                if 'conversation_memory' in globals() and conversation_memory:
                    conversation_memory.add_message(user_id, "user", message_text)
                    conversation_memory.add_message(user_id, "assistant", response)
            return

        # C. SMART PATH: LLM Analysis
        if llm.enabled:
            # Analyze
            analysis = await llm.analyze_command(message_text, context=home_context)
            
            # Execute if Command
            if analysis and analysis.get("action") and analysis.get("confidence", 0) > 0.6:
                # ... (Execution Logic Reuse) ...
                # For brevity in this replace script, we are re-injecting the simple execution logic
                # Ideally we call a helper, but we'll inline for robustness
                action = analysis["action"]
                target = analysis.get("target", "all")
                domain = analysis.get("domain", "light")
                
                states = await ha.get_all_states()
                devices = [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]
                
                if target and target != "all":
                    devices = [d for d in devices if target.lower() in d.get("entity_id", "").lower()]
                
                if devices:
                    count = 0
                    for d in devices:
                        service = "turn_on" if "on" in action else "turn_off"
                        if "lock" in action: service = "lock"
                        if "unlock" in action: service = "unlock"
                        
                        await ha.call_service(domain, service, d["entity_id"])
                        count += 1
                    
                    await update.message.reply_text(f"✅ Action {action} completed on {count} devices.")
                    return
            
            # Fallback to Chat
            response = await llm.chat(message_text, context={"history": history, "home": home_context})
            if response:
                await update.message.reply_text(response)
                return

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")
"""

    # Replace the existing function
    start_marker = "async def handle_natural_language"
    next_marker = "async def proactive_alert_callback" 
    
    start_idx = content.find(start_marker)
    end_idx = content.find(next_marker)
    
    if start_idx != -1 and end_idx != -1:
        content = content[:start_idx] + new_handler + "\n\n" + content[end_idx:]
        with open('homeai_bot.py', 'w') as f:
            f.write(content)
        print("✅ Interaction Model Upgraded (Status + Chat)")
    else:
        print("Could not find function boundaries.")

except Exception as e:
    print(e)
EOF

python3 upgrade_interaction.py

echo "Restarting..."
python3 homeai_bot.py
