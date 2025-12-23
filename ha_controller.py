"""
Home Assistant Controller
Handles all communication with Home Assistant API
"""

import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class HomeAssistantController:
    """Controller for Home Assistant API interactions"""
    
    def __init__(self, url: str, token: str):
        """
        Initialize Home Assistant controller
        
        Args:
            url: Home Assistant URL (e.g., http://192.168.1.100:8123)
            token: Long-lived access token
        """
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 30  # seconds
        self._last_cache_time: Optional[datetime] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session
    
    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def test_connection(self) -> bool:
        """
        Test connection to Home Assistant
        
        Returns:
            True if connected, False otherwise
        """
        try:
            session = await self._get_session()
            async with session.get(f'{self.url}/api/') as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Connected to Home Assistant: {data.get('message', 'OK')}")
                    return True
                else:
                    logger.error(f"HA connection failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"HA connection error: {e}")
            return False
    
    async def get_all_states(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all entity states from Home Assistant
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of entity state dictionaries
        """
        # Check cache
        if use_cache and self._last_cache_time:
            age = (datetime.now() - self._last_cache_time).total_seconds()
            if age < self._cache_ttl and 'states' in self._cache:
                logger.debug("Using cached states")
                return self._cache['states']
        
        try:
            session = await self._get_session()
            async with session.get(f'{self.url}/api/states') as response:
                if response.status == 200:
                    states = await response.json()
                    # Update cache
                    self._cache['states'] = states
                    self._last_cache_time = datetime.now()
                    logger.debug(f"Retrieved {len(states)} states from HA")
                    return states
                else:
                    logger.error(f"Failed to get states: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting states: {e}")
            return []
    
    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get state of a specific entity
        
        Args:
            entity_id: Entity ID (e.g., light.living_room)
            
        Returns:
            Entity state dictionary or None
        """
        try:
            session = await self._get_session()
            async with session.get(f'{self.url}/api/states/{entity_id}') as response:
                if response.status == 200:
                    state = await response.json()
                    return state
                elif response.status == 404:
                    logger.warning(f"Entity not found: {entity_id}")
                    return None
                else:
                    logger.error(f"Failed to get state for {entity_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting state for {entity_id}: {e}")
            return None
    
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        service_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Call a Home Assistant service
        
        Args:
            domain: Service domain (e.g., light, switch, climate)
            service: Service name (e.g., turn_on, turn_off)
            entity_id: Target entity ID (optional)
            service_data: Additional service data (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = service_data or {}
            if entity_id:
                data['entity_id'] = entity_id
            
            session = await self._get_session()
            async with session.post(
                f'{self.url}/api/services/{domain}/{service}',
                json=data
            ) as response:
                if response.status == 200:
                    logger.info(f"Service called: {domain}.{service} for {entity_id}")
                    # Invalidate cache
                    self._last_cache_time = None
                    return True
                else:
                    logger.error(f"Service call failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error calling service {domain}.{service}: {e}")
            return False
    
    async def turn_on(self, entity_id: str, **kwargs) -> bool:
        """Turn on an entity"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'turn_on', entity_id, kwargs)
    
    async def turn_off(self, entity_id: str, **kwargs) -> bool:
        """Turn off an entity"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'turn_off', entity_id, kwargs)
    
    async def toggle(self, entity_id: str) -> bool:
        """Toggle an entity"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, 'toggle', entity_id)
    
    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        """Set climate device temperature"""
        return await self.call_service(
            'climate',
            'set_temperature',
            entity_id,
            {'temperature': temperature}
        )
    
    async def lock(self, entity_id: str) -> bool:
        """Lock a lock"""
        return await self.call_service('lock', 'lock', entity_id)
    
    async def unlock(self, entity_id: str) -> bool:
        """Unlock a lock"""
        return await self.call_service('lock', 'unlock', entity_id)
    
    async def open_cover(self, entity_id: str) -> bool:
        """Open a cover (blinds, garage, etc.)"""
        return await self.call_service('cover', 'open_cover', entity_id)
    
    async def close_cover(self, entity_id: str) -> bool:
        """Close a cover"""
        return await self.call_service('cover', 'close_cover', entity_id)
    
    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all entities for a specific domain
        
        Args:
            domain: Domain name (light, switch, climate, etc.)
            
        Returns:
            List of entity states
        """
        states = await self.get_all_states()
        return [s for s in states if s.get('entity_id', '').startswith(f'{domain}.')]
    
    async def get_entities_by_area(self, area: str) -> List[Dict[str, Any]]:
        """
        Get all entities in a specific area/room
        
        Args:
            area: Area name (e.g., bedroom, living_room)
            
        Returns:
            List of entity states
        """
        states = await self.get_all_states()
        area_lower = area.lower().replace(' ', '_')
        
        return [
            s for s in states
            if area_lower in s.get('entity_id', '').lower()
            or area_lower in s.get('attributes', {}).get('friendly_name', '').lower()
        ]
    
    async def get_sensors(self) -> Dict[str, Any]:
        """
        Get all sensor data organized by type
        
        Returns:
            Dictionary of sensor data
        """
        sensors = await self.get_entities_by_domain('sensor')
        
        organized = {
            'temperature': [],
            'humidity': [],
            'motion': [],
            'door': [],
            'window': [],
            'other': []
        }
        
        for sensor in sensors:
            entity_id = sensor.get('entity_id', '')
            name = sensor.get('attributes', {}).get('friendly_name', entity_id)
            state = sensor.get('state', 'unknown')
            
            if 'temperature' in entity_id or 'temp' in entity_id:
                organized['temperature'].append({'name': name, 'value': state, 'entity_id': entity_id})
            elif 'humidity' in entity_id:
                organized['humidity'].append({'name': name, 'value': state, 'entity_id': entity_id})
            elif 'motion' in entity_id:
                organized['motion'].append({'name': name, 'value': state, 'entity_id': entity_id})
            elif 'door' in entity_id:
                organized['door'].append({'name': name, 'value': state, 'entity_id': entity_id})
            elif 'window' in entity_id:
                organized['window'].append({'name': name, 'value': state, 'entity_id': entity_id})
            else:
                organized['other'].append({'name': name, 'value': state, 'entity_id': entity_id})
        
        return organized
    
    async def get_history(
        self,
        entity_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entity history
        
        Args:
            entity_id: Entity ID
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)
            
        Returns:
            List of historical states
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)
        if end_time is None:
            end_time = datetime.now()
        
        try:
            session = await self._get_session()
            url = f'{self.url}/api/history/period/{start_time.isoformat()}'
            params = {'filter_entity_id': entity_id}
            if end_time:
                params['end_time'] = end_time.isoformat()
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    history = await response.json()
                    return history[0] if history else []
                else:
                    logger.error(f"Failed to get history: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    async def fire_event(self, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Fire a custom event
        
        Args:
            event_type: Event type name
            event_data: Event data
            
        Returns:
            True if successful
        """
        try:
            session = await self._get_session()
            async with session.post(
                f'{self.url}/api/events/{event_type}',
                json=event_data or {}
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error firing event: {e}")
            return False
    
    async def render_template(self, template: str) -> Optional[str]:
        """
        Render a Home Assistant template
        
        Args:
            template: Template string
            
        Returns:
            Rendered template or None
        """
        try:
            session = await self._get_session()
            async with session.post(
                f'{self.url}/api/template',
                json={'template': template}
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return None
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return None
    
    def __del__(self):
        """Cleanup on deletion"""
        if self._session and not self._session.closed:
            try:
                asyncio.get_event_loop().create_task(self.close())
            except:
                pass
