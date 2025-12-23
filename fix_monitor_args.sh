#!/bin/bash
#
# Fix Monitor Arguments
# Enforces (ha, db) order in both definition and call
#

echo "🔧 Fixing Monitor Arguments..."

cd ~/homeai-bot

# 1. Overwrite monitor.py with EXPLICIT argument order
cat > monitor.py << 'EOF'
"""
HomeMonitor v2.0
"""
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class HomeMonitor:
    def __init__(self, ha_controller, db, context=None):
        # Explicitly name arguments for clarity
        self.ha = ha_controller
        self.db = db
        self.context = context
        self.running = False
        self.last_alert = {}
        self.alert_timeout = timedelta(hours=6)
        self.ignored_strings = ["backup", "slug", "update", "zone", "person", "sun"]

    async def start(self):
        self.running = True
        logger.info("Proactive monitor started")
        await asyncio.sleep(60) # Wait for HA
        
        while self.running:
            try:
                await self.check_status()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Status check failed: {e}")
                await asyncio.sleep(60)

    async def check_status(self):
        if not self.context: return
        
        # This line was crashing because self.ha was actually 'db'
        states = await self.ha.get_all_states()
        
        offline_devices = []
        for state in states:
            entity_id = state.get("entity_id", "")
            status = state.get("state")
            if status in ["unavailable", "unknown"]:
                if any(ig in entity_id.lower() for ig in self.ignored_strings): continue
                friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                last = self.last_alert.get(entity_id)
                if last and datetime.now() - last < self.alert_timeout: continue
                offline_devices.append(f"{friendly_name}")
                self.last_alert[entity_id] = datetime.now()

        if offline_devices:
            if len(offline_devices) > 3:
                 await self.send_alert(f"⚠️ **System Check**: {len(offline_devices)} devices offline.")
            else:
                for dev in offline_devices:
                    await self.send_alert(f"⚠️ Device offline: {dev}")

    async def send_alert(self, message):
        users = self.db.get_users()
        for user_id in users:
            try:
                await self.context.bot.send_message(chat_id=user_id, text=message)
            except: pass

    def stop(self):
        self.running = False
EOF

# 2. Update homeai_bot.py to pass arguments in correct order (ha, db)
# We locate the initialization line and replace it
# "monitor = HomeMonitor(...)"

# We construct a python script to replace the init line safely
cat > fix_monitor_init.py << 'EOF'
import sys

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()
    
    # We want to find "monitor = HomeMonitor(" and ensure args are ha, db
    # We will just Find and Replace the line entirely
    
    # Pattern to match: monitor = HomeMonitor(anything)
    # Replacement: monitor = HomeMonitor(ha, db, context=app)
    
    import re
    # Match assignment to monitor
    # It might be "monitor = HomeMonitor(ha, db, context=app)" already or swapped
    
    # We just force replace it
    new_line = "monitor = HomeMonitor(ha, db, context=app)"
    
    # Check if we can find the line roughly
    if "monitor = HomeMonitor" in content:
        # Regex replacement to handle potential variations in existing args
        content = re.sub(r"monitor\s*=\s*HomeMonitor\(.*?\)", new_line, content)
        
        with open('homeai_bot.py', 'w') as f:
            f.write(content)
        print("✅ homeai_bot.py updated with correct Monitor init")
    else:
        print("⚠️ Could not find HomeMonitor init in homeai_bot.py")

except Exception as e:
    print(e)
EOF

python3 fix_monitor_init.py

echo "✅ Monitor Argument Clash Fixed."
echo "Restarting..."
python3 homeai_bot.py
