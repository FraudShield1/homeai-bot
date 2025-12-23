"""
Scene Manager for HomeAI Bot
Handles scene creation, management, and execution
"""

import logging
from typing import Dict, List, Any, Optional
from database import Database

logger = logging.getLogger(__name__)


class SceneManager:
    """Manages home automation scenes"""
    
    def __init__(self, db: Database, ha_controller):
        """
        Initialize scene manager
        
        Args:
            db: Database instance
            ha_controller: Home Assistant controller instance
        """
        self.db = db
        self.ha = ha_controller
        self._init_default_scenes()
    
    def _init_default_scenes(self):
        """Initialize default scenes if they don't exist"""
        default_scenes = {
            "morning": {
                "description": "Morning routine - lights on, temperature up, blinds open",
                "actions": {
                    "lights": {"action": "turn_on", "brightness": 60, "rooms": ["kitchen", "bedroom"]},
                    "climate": {"action": "set_temperature", "temperature": 21},
                    "covers": {"action": "open", "rooms": ["bedroom", "living_room"]},
                    "switches": {"action": "turn_on", "devices": ["coffee_maker"]}
                }
            },
            "away": {
                "description": "Away mode - secure home, save energy",
                "actions": {
                    "lights": {"action": "turn_off", "rooms": ["all"]},
                    "climate": {"action": "set_temperature", "temperature": 18},
                    "locks": {"action": "lock", "devices": ["all"]},
                    "covers": {"action": "close", "rooms": ["all"]},
                    "security": {"action": "arm"}
                }
            },
            "movie": {
                "description": "Movie mode - dim lights, close blinds",
                "actions": {
                    "lights": {"action": "turn_on", "brightness": 30, "rooms": ["living_room"]},
                    "covers": {"action": "close", "rooms": ["living_room"]},
                    "media": {"action": "turn_on", "devices": ["tv", "soundbar"]}
                }
            },
            "night": {
                "description": "Night mode - dim lights, lower temperature, secure home",
                "actions": {
                    "lights": {"action": "turn_off", "rooms": ["all"], "except": ["bedroom"]},
                    "bedroom_light": {"action": "turn_on", "brightness": 10},
                    "climate": {"action": "set_temperature", "temperature": 18},
                    "locks": {"action": "lock", "devices": ["all"]},
                    "covers": {"action": "close", "rooms": ["all"]}
                }
            },
            "home": {
                "description": "Arrival home - welcome settings",
                "actions": {
                    "lights": {"action": "turn_on", "brightness": 70, "rooms": ["entrance", "living_room"]},
                    "climate": {"action": "set_temperature", "temperature": 21},
                    "locks": {"action": "unlock", "devices": ["front_door"]},
                    "security": {"action": "disarm"}
                }
            }
        }
        
        # Save default scenes if they don't exist
        for name, config in default_scenes.items():
            existing = self.db.get_scene(name)
            if not existing:
                self.db.save_scene(
                    name=name,
                    description=config["description"],
                    actions=config["actions"],
                    created_by=0  # System
                )
                logger.info(f"Created default scene: {name}")
    
    async def activate_scene(self, scene_name: str) -> Dict[str, Any]:
        """
        Activate a scene
        
        Args:
            scene_name: Name of the scene to activate
            
        Returns:
            Result dictionary with success status and details
        """
        scene = self.db.get_scene(scene_name)
        if not scene:
            return {"success": False, "error": f"Scene '{scene_name}' not found"}
        
        results = {
            "scene": scene_name,
            "success": True,
            "actions_executed": [],
            "actions_failed": []
        }
        
        try:
            actions = scene["actions"]
            
            # Execute lights actions
            if "lights" in actions:
                await self._execute_light_actions(actions["lights"], results)
            
            # Execute climate actions
            if "climate" in actions:
                await self._execute_climate_actions(actions["climate"], results)
            
            # Execute lock actions
            if "locks" in actions:
                await self._execute_lock_actions(actions["locks"], results)
            
            # Execute cover actions
            if "covers" in actions:
                await self._execute_cover_actions(actions["covers"], results)
            
            # Execute switch actions
            if "switches" in actions:
                await self._execute_switch_actions(actions["switches"], results)
            
            # Execute media actions
            if "media" in actions:
                await self._execute_media_actions(actions["media"], results)
            
            # Execute custom actions
            for key, action in actions.items():
                if key not in ["lights", "climate", "locks", "covers", "switches", "media"]:
                    await self._execute_custom_action(key, action, results)
            
            logger.info(f"Scene '{scene_name}' activated: {len(results['actions_executed'])} actions executed")
            
        except Exception as e:
            logger.error(f"Error activating scene '{scene_name}': {e}")
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    async def _execute_light_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute light-related actions"""
        action = config.get("action", "turn_on")
        brightness = config.get("brightness", 100)
        rooms = config.get("rooms", [])
        except_rooms = config.get("except", [])
        
        # Get all lights
        states = await self.ha.get_all_states()
        lights = [s for s in states if s.get("entity_id", "").startswith("light.")]
        
        # Filter by rooms
        if rooms and "all" not in rooms:
            lights = [
                l for l in lights
                if any(room.lower() in l.get("entity_id", "").lower() for room in rooms)
            ]
        
        # Exclude specific rooms
        if except_rooms:
            lights = [
                l for l in lights
                if not any(room.lower() in l.get("entity_id", "").lower() for room in except_rooms)
            ]
        
        # Execute action
        for light in lights:
            entity_id = light.get("entity_id")
            try:
                if action == "turn_on":
                    success = await self.ha.turn_on(entity_id, brightness_pct=brightness)
                elif action == "turn_off":
                    success = await self.ha.turn_off(entity_id)
                else:
                    success = False
                
                if success:
                    results["actions_executed"].append(f"Light {entity_id}: {action}")
                else:
                    results["actions_failed"].append(f"Light {entity_id}: {action}")
            except Exception as e:
                logger.error(f"Error controlling light {entity_id}: {e}")
                results["actions_failed"].append(f"Light {entity_id}: {str(e)}")
    
    async def _execute_climate_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute climate-related actions"""
        action = config.get("action", "set_temperature")
        temperature = config.get("temperature")
        rooms = config.get("rooms", [])
        
        if not temperature:
            return
        
        # Get climate devices
        states = await self.ha.get_all_states()
        climate_devices = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        
        # Filter by rooms
        if rooms and "all" not in rooms:
            climate_devices = [
                c for c in climate_devices
                if any(room.lower() in c.get("entity_id", "").lower() for room in rooms)
            ]
        
        # Execute action
        for device in climate_devices:
            entity_id = device.get("entity_id")
            try:
                success = await self.ha.set_temperature(entity_id, temperature)
                if success:
                    results["actions_executed"].append(f"Climate {entity_id}: {temperature}°C")
                else:
                    results["actions_failed"].append(f"Climate {entity_id}: failed")
            except Exception as e:
                logger.error(f"Error controlling climate {entity_id}: {e}")
                results["actions_failed"].append(f"Climate {entity_id}: {str(e)}")
    
    async def _execute_lock_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute lock-related actions"""
        action = config.get("action", "lock")
        devices = config.get("devices", [])
        
        # Get locks
        states = await self.ha.get_all_states()
        locks = [s for s in states if s.get("entity_id", "").startswith("lock.")]
        
        # Filter by devices
        if devices and "all" not in devices:
            locks = [
                l for l in locks
                if any(device.lower() in l.get("entity_id", "").lower() for device in devices)
            ]
        
        # Execute action
        for lock in locks:
            entity_id = lock.get("entity_id")
            try:
                if action == "lock":
                    success = await self.ha.lock(entity_id)
                elif action == "unlock":
                    success = await self.ha.unlock(entity_id)
                else:
                    success = False
                
                if success:
                    results["actions_executed"].append(f"Lock {entity_id}: {action}")
                else:
                    results["actions_failed"].append(f"Lock {entity_id}: {action}")
            except Exception as e:
                logger.error(f"Error controlling lock {entity_id}: {e}")
                results["actions_failed"].append(f"Lock {entity_id}: {str(e)}")
    
    async def _execute_cover_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute cover-related actions (blinds, garage, etc.)"""
        action = config.get("action", "close")
        rooms = config.get("rooms", [])
        
        # Get covers
        states = await self.ha.get_all_states()
        covers = [s for s in states if s.get("entity_id", "").startswith("cover.")]
        
        # Filter by rooms
        if rooms and "all" not in rooms:
            covers = [
                c for c in covers
                if any(room.lower() in c.get("entity_id", "").lower() for room in rooms)
            ]
        
        # Execute action
        for cover in covers:
            entity_id = cover.get("entity_id")
            try:
                if action == "open":
                    success = await self.ha.open_cover(entity_id)
                elif action == "close":
                    success = await self.ha.close_cover(entity_id)
                else:
                    success = False
                
                if success:
                    results["actions_executed"].append(f"Cover {entity_id}: {action}")
                else:
                    results["actions_failed"].append(f"Cover {entity_id}: {action}")
            except Exception as e:
                logger.error(f"Error controlling cover {entity_id}: {e}")
                results["actions_failed"].append(f"Cover {entity_id}: {str(e)}")
    
    async def _execute_switch_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute switch-related actions"""
        action = config.get("action", "turn_on")
        devices = config.get("devices", [])
        
        # Get switches
        states = await self.ha.get_all_states()
        switches = [s for s in states if s.get("entity_id", "").startswith("switch.")]
        
        # Filter by devices
        if devices and "all" not in devices:
            switches = [
                s for s in switches
                if any(device.lower() in s.get("entity_id", "").lower() for device in devices)
            ]
        
        # Execute action
        for switch in switches:
            entity_id = switch.get("entity_id")
            try:
                if action == "turn_on":
                    success = await self.ha.turn_on(entity_id)
                elif action == "turn_off":
                    success = await self.ha.turn_off(entity_id)
                else:
                    success = False
                
                if success:
                    results["actions_executed"].append(f"Switch {entity_id}: {action}")
                else:
                    results["actions_failed"].append(f"Switch {entity_id}: {action}")
            except Exception as e:
                logger.error(f"Error controlling switch {entity_id}: {e}")
                results["actions_failed"].append(f"Switch {entity_id}: {str(e)}")
    
    async def _execute_media_actions(self, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute media-related actions"""
        action = config.get("action", "turn_on")
        devices = config.get("devices", [])
        
        # Get media players
        states = await self.ha.get_all_states()
        media_players = [s for s in states if s.get("entity_id", "").startswith("media_player.")]
        
        # Filter by devices
        if devices and "all" not in devices:
            media_players = [
                m for m in media_players
                if any(device.lower() in m.get("entity_id", "").lower() for device in devices)
            ]
        
        # Execute action
        for player in media_players:
            entity_id = player.get("entity_id")
            try:
                if action == "turn_on":
                    success = await self.ha.turn_on(entity_id)
                elif action == "turn_off":
                    success = await self.ha.turn_off(entity_id)
                else:
                    success = False
                
                if success:
                    results["actions_executed"].append(f"Media {entity_id}: {action}")
                else:
                    results["actions_failed"].append(f"Media {entity_id}: {action}")
            except Exception as e:
                logger.error(f"Error controlling media {entity_id}: {e}")
                results["actions_failed"].append(f"Media {entity_id}: {str(e)}")
    
    async def _execute_custom_action(self, key: str, config: Dict[str, Any], results: Dict[str, Any]):
        """Execute custom action"""
        try:
            # Custom actions can be extended here
            results["actions_executed"].append(f"Custom action {key}: executed")
        except Exception as e:
            logger.error(f"Error executing custom action {key}: {e}")
            results["actions_failed"].append(f"Custom action {key}: {str(e)}")
    
    def create_scene(self, name: str, description: str, actions: Dict[str, Any], user_id: int) -> bool:
        """
        Create a new scene
        
        Args:
            name: Scene name
            description: Scene description
            actions: Scene actions configuration
            user_id: User creating the scene
            
        Returns:
            True if successful
        """
        return self.db.save_scene(name, description, actions, user_id)
    
    def get_scene(self, name: str) -> Optional[Dict[str, Any]]:
        """Get scene by name"""
        return self.db.get_scene(name)
    
    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all available scenes"""
        return self.db.get_all_scenes()
    
    def delete_scene(self, name: str) -> bool:
        """Delete a scene"""
        return self.db.delete_scene(name)
