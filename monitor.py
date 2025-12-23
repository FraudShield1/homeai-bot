"""
Proactive Monitor for HomeAI Bot
Background monitoring for alerts, automation, and intelligent notifications
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from database import Database

logger = logging.getLogger(__name__)


class ProactiveMonitor:
    """Monitors home state and sends proactive alerts"""
    
    def __init__(self, db: Database, ha_controller, alert_callback: Callable):
        """
        Initialize proactive monitor
        
        Args:
            db: Database instance
            ha_controller: Home Assistant controller
            alert_callback: Async function to call with alerts
        """
        self.db = db
        self.ha = ha_controller
        self.alert_callback = alert_callback
        self.running = False
        self.monitor_task = None
        
        # Tracking state
        self.last_states = {}
        self.door_open_times = {}
        self.motion_last_seen = {}
        self.alert_cooldowns = {}  # Prevent spam
        
        # Configuration
        self.door_alert_delay = 1800  # 30 minutes
        self.motion_alert_enabled = True
        self.water_leak_alert_enabled = True
        self.temperature_anomaly_threshold = 5  # degrees
    
    async def start(self):
        """Start monitoring"""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Proactive monitor started")
    
    async def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Proactive monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_sensors()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_sensors(self):
        """Check all sensors and trigger alerts"""
        try:
            states = await self.ha.get_all_states()
            
            # Check doors and windows
            await self._check_doors_windows(states)
            
            # Check motion sensors
            await self._check_motion(states)
            
            # Check water leak sensors
            await self._check_water_leaks(states)
            
            # Check temperature anomalies
            await self._check_temperature(states)
            
            # Check device offline status
            await self._check_device_status(states)
            
            # Update last states
            self.last_states = {s['entity_id']: s for s in states}
            
        except Exception as e:
            logger.error(f"Error checking sensors: {e}")
    
    async def _check_doors_windows(self, states: List[Dict[str, Any]]):
        """Check for doors/windows left open"""
        now = datetime.now()
        
        # Find door and window sensors
        door_window_sensors = [
            s for s in states
            if ('door' in s.get('entity_id', '').lower() or 
                'window' in s.get('entity_id', '').lower())
            and s.get('state') in ['on', 'open']
        ]
        
        for sensor in door_window_sensors:
            entity_id = sensor.get('entity_id')
            
            # Track when door/window was opened
            if entity_id not in self.door_open_times:
                self.door_open_times[entity_id] = now
            
            # Check if open too long
            open_duration = (now - self.door_open_times[entity_id]).total_seconds()
            
            if open_duration > self.door_alert_delay:
                # Check cooldown to avoid spam
                if not self._is_on_cooldown(f"door_{entity_id}"):
                    name = sensor.get('attributes', {}).get('friendly_name', entity_id)
                    minutes = int(open_duration / 60)
                    
                    await self._send_alert(
                        alert_type="door_open",
                        entity_id=entity_id,
                        message=f"🚪 {name} has been open for {minutes} minutes",
                        severity="warning",
                        actions=[
                            {"text": "Close", "callback": f"close_{entity_id}"},
                            {"text": "Remind in 1 hour", "callback": f"snooze_{entity_id}"},
                            {"text": "Ignore", "callback": f"ignore_{entity_id}"}
                        ]
                    )
                    
                    self._set_cooldown(f"door_{entity_id}", 3600)  # 1 hour cooldown
        
        # Clean up closed doors/windows
        for entity_id in list(self.door_open_times.keys()):
            if not any(s.get('entity_id') == entity_id and s.get('state') in ['on', 'open'] 
                      for s in door_window_sensors):
                del self.door_open_times[entity_id]
    
    async def _check_motion(self, states: List[Dict[str, Any]]):
        """Check motion sensors"""
        if not self.motion_alert_enabled:
            return
        
        motion_sensors = [
            s for s in states
            if 'motion' in s.get('entity_id', '').lower()
            and s.get('state') == 'on'
        ]
        
        for sensor in motion_sensors:
            entity_id = sensor.get('entity_id')
            
            # Check if this is new motion
            last_state = self.last_states.get(entity_id, {})
            if last_state.get('state') != 'on':
                # New motion detected
                name = sensor.get('attributes', {}).get('friendly_name', entity_id)
                
                # Only alert if not on cooldown
                if not self._is_on_cooldown(f"motion_{entity_id}"):
                    await self._send_alert(
                        alert_type="motion",
                        entity_id=entity_id,
                        message=f"👤 Motion detected: {name}",
                        severity="info",
                        actions=[
                            {"text": "View Camera", "callback": f"camera_{entity_id}"},
                            {"text": "Dismiss", "callback": f"dismiss_{entity_id}"}
                        ]
                    )
                    
                    self._set_cooldown(f"motion_{entity_id}", 300)  # 5 min cooldown
    
    async def _check_water_leaks(self, states: List[Dict[str, Any]]):
        """Check water leak sensors"""
        if not self.water_leak_alert_enabled:
            return
        
        leak_sensors = [
            s for s in states
            if ('water' in s.get('entity_id', '').lower() or 
                'leak' in s.get('entity_id', '').lower())
            and s.get('state') in ['on', 'wet', 'detected']
        ]
        
        for sensor in leak_sensors:
            entity_id = sensor.get('entity_id')
            name = sensor.get('attributes', {}).get('friendly_name', entity_id)
            
            # Water leak is critical - always alert
            await self._send_alert(
                alert_type="water_leak",
                entity_id=entity_id,
                message=f"🚨 WATER LEAK DETECTED: {name}",
                severity="critical",
                actions=[
                    {"text": "Shut Off Water", "callback": f"shutoff_water"},
                    {"text": "View Camera", "callback": f"camera_{entity_id}"},
                    {"text": "False Alarm", "callback": f"false_alarm_{entity_id}"}
                ]
            )
            
            # Log to database
            self.db.log_alert("water_leak", entity_id, f"Water leak detected at {name}", "critical")
    
    async def _check_temperature(self, states: List[Dict[str, Any]]):
        """Check for temperature anomalies"""
        temp_sensors = [
            s for s in states
            if 'temperature' in s.get('entity_id', '').lower()
            and s.get('state') not in ['unknown', 'unavailable']
        ]
        
        for sensor in temp_sensors:
            entity_id = sensor.get('entity_id')
            try:
                current_temp = float(sensor.get('state'))
                
                # Get expected temperature from user preferences
                # For now, use simple thresholds
                if current_temp < 10:  # Too cold
                    if not self._is_on_cooldown(f"temp_low_{entity_id}"):
                        name = sensor.get('attributes', {}).get('friendly_name', entity_id)
                        await self._send_alert(
                            alert_type="temperature",
                            entity_id=entity_id,
                            message=f"❄️ Low temperature alert: {name} is {current_temp}°C",
                            severity="warning"
                        )
                        self._set_cooldown(f"temp_low_{entity_id}", 3600)
                
                elif current_temp > 30:  # Too hot
                    if not self._is_on_cooldown(f"temp_high_{entity_id}"):
                        name = sensor.get('attributes', {}).get('friendly_name', entity_id)
                        await self._send_alert(
                            alert_type="temperature",
                            entity_id=entity_id,
                            message=f"🔥 High temperature alert: {name} is {current_temp}°C",
                            severity="warning"
                        )
                        self._set_cooldown(f"temp_high_{entity_id}", 3600)
                        
            except (ValueError, TypeError):
                continue
    
    async def _check_device_status(self, states: List[Dict[str, Any]]):
        """Check for devices that went offline"""
        for state in states:
            entity_id = state.get('entity_id')
            current_state = state.get('state')
            
            # Check if device became unavailable
            if current_state in ['unavailable', 'unknown']:
                last_state = self.last_states.get(entity_id, {})
                if last_state.get('state') not in ['unavailable', 'unknown']:
                    # Device just went offline
                    if not self._is_on_cooldown(f"offline_{entity_id}"):
                        name = state.get('attributes', {}).get('friendly_name', entity_id)
                        await self._send_alert(
                            alert_type="device_offline",
                            entity_id=entity_id,
                            message=f"⚠️ Device offline: {name}",
                            severity="info"
                        )
                        self._set_cooldown(f"offline_{entity_id}", 1800)
    
    async def _send_alert(self, alert_type: str, entity_id: str, message: str, 
                         severity: str = "info", actions: List[Dict[str, str]] = None):
        """Send alert via callback"""
        try:
            alert_data = {
                "type": alert_type,
                "entity_id": entity_id,
                "message": message,
                "severity": severity,
                "actions": actions or [],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.alert_callback(alert_data)
            
            # Log to database
            self.db.log_alert(alert_type, entity_id, message, severity)
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def _is_on_cooldown(self, key: str) -> bool:
        """Check if alert is on cooldown"""
        if key not in self.alert_cooldowns:
            return False
        
        cooldown_until = self.alert_cooldowns[key]
        return datetime.now() < cooldown_until
    
    def _set_cooldown(self, key: str, seconds: int):
        """Set alert cooldown"""
        self.alert_cooldowns[key] = datetime.now() + timedelta(seconds=seconds)
    
    async def check_arrival_departure(self, user_id: int, location: str):
        """
        Check for arrival/departure and trigger automations
        
        Args:
            user_id: User ID
            location: 'home' or 'away'
        """
        try:
            # Get user preferences
            auto_away = self.db.get_preference(user_id, 'auto_away_mode', True)
            auto_arrival = self.db.get_preference(user_id, 'auto_arrival_mode', True)
            
            if location == 'away' and auto_away:
                # Trigger away mode
                await self._send_alert(
                    alert_type="departure",
                    entity_id="automation",
                    message="👋 Activating away mode...",
                    severity="info"
                )
                
            elif location == 'home' and auto_arrival:
                # Trigger arrival mode
                await self._send_alert(
                    alert_type="arrival",
                    entity_id="automation",
                    message="🏠 Welcome home! Preparing your home...",
                    severity="info"
                )
                
        except Exception as e:
            logger.error(f"Error in arrival/departure check: {e}")
