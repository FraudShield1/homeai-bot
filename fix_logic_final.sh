#!/bin/bash
#
# Fix Bot Logic - End-to-End Hardening
# Replaces the handle_natural_language function with a robust, smart version.
#

echo "🧠 Hardening Bot Intelligence..."

cd ~/homeai-bot

# We will use a python script to replace the entire handle_natural_language function
# because it's too complex for sed
cat > replace_handler.py << 'EOF'
import sys
import re

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # Define the new robust handler code
    new_handler = """
async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    \"\"\"
    Unified Natural Language Handler (Robust)
    1. Greeting -> Fast Chat
    2. Command Analysis -> Execute
    3. General Chat -> Conversational Response
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
        
        # B. FAST PATH: Greetings
        if message_text.lower() in ["hi", "hello", "hey", "start", "yo", "gm", "gn", "hola"]:
            if llm.enabled:
                response = await llm.chat(message_text, context={"history": history})
                if 'conversation_memory' in globals() and conversation_memory:
                    conversation_memory.add_message(user_id, "user", message_text)
                    conversation_memory.add_message(user_id, "assistant", response)
                await update.message.reply_text(response)
                return

        # C. SMART PATH: LLM Analysis
        if llm.enabled:
            # Get Home State
            home_context = {}
            try:
                states = await ha.get_all_states()
                home_context = {
                    "lights_active": sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on"),
                    "temperature": next((s.get("state") for s in states if "temperature" in s.get("entity_id", "")), "unknown")
                }
            except: pass

            # Analyze
            analysis = await llm.analyze_command(message_text, context=home_context)
            
            # Execute if Command
            if analysis and analysis.get("action") and analysis.get("confidence", 0) > 0.6:
                # Execute Logic (Inline for safety)
                action = analysis["action"]
                target = analysis.get("target", "all")
                domain = analysis.get("domain", "light") # Default to light
                
                # --- Execution Block ---
                states = await ha.get_all_states()
                devices = [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]
                if target and target != "all":
                    devices = [d for d in devices if target.lower() in d.get("entity_id", "").lower()]
                
                if devices:
                    count = 0
                    for d in devices:
                        # Map actions
                        service = "turn_on" if action == "turn_on" else "turn_off" # simplified
                        if action == "turn_on": service = "turn_on"
                        elif action == "turn_off": service = "turn_off"
                        elif action == "lock": service = "lock"
                        elif action == "unlock": service = "unlock"
                        
                        await ha.call_service(domain, service, d["entity_id"])
                        count += 1
                    
                    await update.message.reply_text(f"✅ Executed {action} on {count} devices.")
                    if 'conversation_memory' in globals() and conversation_memory:
                         conversation_memory.add_message(user_id, "user", message_text)
                         conversation_memory.add_message(user_id, "system", f"Action: {action}")
                    return
                # -----------------------
            
            # Fallback to Chat
            response = await llm.chat(message_text, context={"history": history, "home": home_context})
            if response:
                if 'conversation_memory' in globals() and conversation_memory:
                    conversation_memory.add_message(user_id, "user", message_text)
                    conversation_memory.add_message(user_id, "assistant", response)
                await update.message.reply_text(response)
                return

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

    """

    # Replace the existing function
    # Regex to capture the whole function (basic)
    # We assume standard formatting "async def handle_natural_language... -> None:" 
    # and then indented block.
    # Actually simpler: Find start, find start of next function, replace everything between.
    
    start_marker = "async def handle_natural_language"
    next_marker = "async def proactive_alert_callback" # usually the next one
    
    start_idx = content.find(start_marker)
    end_idx = content.find(next_marker)
    
    if start_idx != -1 and end_idx != -1:
        content = content[:start_idx] + new_handler + "\n\n" + content[end_idx:]
        
        with open('homeai_bot.py', 'w') as f:
            f.write(content)
        print("✅ Handler replaced successfully")
    else:
        print("Could not find function boundaries. Manual check needed.")

except Exception as e:
    print(f"Error: {e}")
EOF

python3 replace_handler.py

echo "✅ Logic Hardened."
echo "Restarting bot..."
python3 homeai_bot.py
