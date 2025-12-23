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
        self.context = context  # Telegram context for sending messages
        self.running = False
        self.last_alert = {}  # Store timestamp of last alert per entity
        self.startup_time = datetime.now()
        
        # IGNORE LIST: Don't alert for these
        self.ignored_entities = [
            "media_player", "automation", "script", "scene", 
            "zone", "person", "sun", "updater"
        ]
        
        # STATUSES TO IGNORE
        self.ignored_states = ["unavailable", "unknown", "off", "idle"] 
        # Note: "unavailable" is often just a temporary glitch, only alert if persistent?
        # For now, let's alert on unavailable but with proper debris.

    async def start(self):
        """Start the monitoring loop"""
        self.running = True
        logger.info("Proactive monitor started")
        
        # Give HA 2 minutes to settle down before alerting
        await asyncio.sleep(60) 
        
        while self.running:
            try:
                await self.check_status()
                await asyncio.sleep(300)  # Check every 5 minutes (reduced frequency)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)

    async def check_status(self):
        """Check all entities and alert on issues"""
        if not self.context:
            return

        try:
            states = await self.ha.get_all_states()
            
            # Group alerts to avoid spam
            offline_devices = []
            
            for state in states:
                entity_id = state.get("entity_id", "")
                domain = entity_id.split(".")[0]
                status = state.get("state")
                
                # Filters
                if domain in self.ignored_entities:
                    continue
                
                # Check for offline devices
                if status == "unavailable":
                    friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                    
                    # IGNORE specific noisy devices associated with backups/system
                    if "backup" in entity_id.lower() or "slug" in entity_id.lower():
                        continue
                        
                    # Check if we alerted recently (debounce)
                    last_time = self.last_alert.get(entity_id)
                    if last_time and datetime.now() - last_time < timedelta(hours=24):
                        continue
                        
                    offline_devices.append(f"{friendly_name} ({entity_id})")
                    self.last_alert[entity_id] = datetime.now()

            # Send SUMMARY alert instead of 20 individual ones
            if offline_devices:
                # If too many devices are offline, it's likely a System issue (HA down), not individual devices
                if len(offline_devices) > 5:
                     # Only alert if we haven't sent a system alert recently
                     sys_alert_key = "system_offline_summary"
                     last_sys = self.last_alert.get(sys_alert_key)
                     if not last_sys or datetime.now() - last_sys > timedelta(hours=1):
                         await self.send_alert(f"⚠️ **System Alert**: {len(offline_devices)} devices are reported offline. Check Home Assistant connection.")
                         self.last_alert[sys_alert_key] = datetime.now()
                else:
                    # Send individual but grouped
                    msg = "⚠️ **Device Status Report**\n" + "\n".join([f"- {d} is offline" for d in offline_devices])
                    await self.send_alert(msg)

        except Exception as e:
            logger.error(f"Status check failed: {e}")

    async def send_alert(self, message):
        """Send alert to authorized users"""
        users = self.db.get_users()
        for user_id in users:
            try:
                await self.context.bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error sending proactive alert: {e}")

    def stop(self):
        self.running = False
