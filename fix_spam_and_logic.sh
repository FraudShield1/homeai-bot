#!/bin/bash
#
# Fix False Positives & Intelligence
# 1. Updates monitor.py to stop spamming offline alerts
# 2. Updates homeai_bot.py logic to handle "hi" intelligently
#

echo "🧠 Applying Intelligence Fixes..."

cd ~/homeai-bot

# 1. Update Monitor (stop the spam)
# We will overwrite monitor.py with the smarter version
cat > monitor.py << 'EOF'
"""
Proactive Monitoring Module
Continuously checks home state and sends alerts for anomalies.
Avoids spamming alerts for known issues or during startup.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HomeMonitor:
    def __init__(self, ha_controller, db, context=None):
        self.ha = ha_controller
        self.db = db
        self.context = context
        self.running = False
        self.last_alert = {}
        
        # Debounce alerts (don't alert same thing twice in 6 hours)
        self.alert_timeout = timedelta(hours=6)
        
        # Ignored entities (noisy backups, internal components)
        self.ignored_strings = ["backup", "slug", "update", "zone", "person", "sun"]

    async def start(self):
        self.running = True
        logger.info("Proactive monitor started")
        # WAIT 60s on startup to let HA connect
        await asyncio.sleep(60)
        
        while self.running:
            try:
                await self.check_status()
                await asyncio.sleep(300) # Check every 5 mins
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)

    async def check_status(self):
        if not self.context: return

        try:
            states = await self.ha.get_all_states()
            offline_devices = []
            
            for state in states:
                entity_id = state.get("entity_id", "")
                status = state.get("state")
                
                # Check for unavailability
                if status in ["unavailable", "unknown"]:
                    # FILTERS
                    if any(ig in entity_id.lower() for ig in self.ignored_strings):
                        continue
                        
                    friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                    
                    # DEBOUNCE
                    last = self.last_alert.get(entity_id)
                    if last and datetime.now() - last < self.alert_timeout:
                        continue
                        
                    offline_devices.append(f"{friendly_name}")
                    self.last_alert[entity_id] = datetime.now()

            # GROUP ALERTS
            if offline_devices:
                if len(offline_devices) > 3:
                     # Summary alert
                     await self.send_alert(f"⚠️ **System Check**: {len(offline_devices)} devices reported offline/unavailable.")
                else:
                    # Detail alert
                    for dev in offline_devices:
                        await self.send_alert(f"⚠️ Device offline: {dev}")

        except Exception as e:
            logger.error(f"Status failed: {e}")

    async def send_alert(self, message):
        users = self.db.get_users()
        for user_id in users:
            try:
                await self.context.bot.send_message(chat_id=user_id, text=message)
            except: pass

    def stop(self):
        self.running = False
EOF

# 2. Fix HomeAI Bot Logic (smarter 'hi')
# We need to ensure the LLM analysis handles greetings better or falls back properly.
# The simplest fix without rewriting the whole file blindly is to use sed to inject the greeting check.

# We'll create a python script to patch the bot file safely
cat > patch_bot_logic.py << 'PY_EOF'
import sys

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # Find the handle_natural_language function
    marker = 'async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:'
    if marker not in content:
        print("Could not find handle_natural_language function")
        sys.exit(1)
        
    # We want to insert Greeting detection RIGHT AFTER message_text is defined
    # Look for: message_text = update.message.text.strip()
    
    insert_point_str = 'message_text = update.message.text.strip()'
    idx = content.find(insert_point_str)
    
    if idx != -1:
        # Construct the new logic block
        new_logic = """
    
    # --- QUICK GREETING CHECK ---
    # Bypass heavy analysis for simple hellos
    if message_text.lower() in ['hi', 'hello', 'hey', 'start', 'gm']:
        if llm.enabled:
             await update.message.reply_chat_action("typing")
             response = await llm.chat(message_text)
             await update.message.reply_text(response)
             return
    # ----------------------------
        """
        # Insert it after the line
        insert_idx = idx + len(insert_point_str)
        content = content[:insert_idx] + new_logic + content[insert_idx:]
        
        with open('homeai_bot.py', 'w') as f:
            f.write(content)
        print("✅ Bot logic patched for greetings")
        
    else:
        print("Could not find insertion point")

except Exception as e:
    print(f"Error patching: {e}")
PY_EOF

python3 patch_bot_logic.py

echo "✅ Fixes Applied!"
echo "  - Monitor: Reduced spam & added delay"
echo "  - Bot: Added smart greeting handler"
echo ""
echo "Restarting service..."
python3 homeai_bot.py
