"""
Network Scanner for HomeAI Bot
Discovers devices on local network and identifies Home Assistant entities
"""

import asyncio
import logging
import socket
import subprocess
import re
from typing import List, Dict, Any, Optional
import ipaddress
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NetworkScanner:
    """Scans local network for devices and Home Assistant entities"""
    
    def __init__(self):
        """Initialize network scanner"""
        self.local_ip = self._get_local_ip()
        self.network = self._get_network_range()
        logger.info(f"Network scanner initialized: {self.network}")
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            return "192.168.1.1"
    
    def _get_network_range(self) -> str:
        """Get network range in CIDR notation"""
        try:
            # Assume /24 subnet (most common for home networks)
            ip_parts = self.local_ip.split('.')
            network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
            return network
        except Exception as e:
            logger.error(f"Error getting network range: {e}")
            return "192.168.1.0/24"
    
    async def scan_network(self, timeout: int = 2) -> List[Dict[str, Any]]:
        """
        Scan network for active devices
        
        Args:
            timeout: Timeout for each host ping in seconds
            
        Returns:
            List of discovered devices
        """
        logger.info(f"Scanning network: {self.network}")
        
        devices = []
        network = ipaddress.ip_network(self.network, strict=False)
        
        # Use ThreadPoolExecutor for parallel scanning
        with ThreadPoolExecutor(max_workers=50) as executor:
            loop = asyncio.get_event_loop()
            tasks = []
            
            for ip in network.hosts():
                ip_str = str(ip)
                task = loop.run_in_executor(executor, self._check_host, ip_str, timeout)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # Filter out None results
            devices = [r for r in results if r is not None]
        
        logger.info(f"Found {len(devices)} active devices")
        return devices
    
    def _check_host(self, ip: str, timeout: int) -> Optional[Dict[str, Any]]:
        """
        Check if host is alive and gather information
        
        Args:
            ip: IP address to check
            timeout: Timeout in seconds
            
        Returns:
            Device info dict or None
        """
        try:
            # Try to ping the host
            if not self._ping_host(ip, timeout):
                return None
            
            device = {
                "ip": ip,
                "hostname": self._get_hostname(ip),
                "mac": self._get_mac_address(ip),
                "ports": self._scan_common_ports(ip),
                "device_type": "unknown"
            }
            
            # Try to identify device type
            device["device_type"] = self._identify_device_type(device)
            
            return device
            
        except Exception as e:
            logger.debug(f"Error checking host {ip}: {e}")
            return None
    
    def _ping_host(self, ip: str, timeout: int) -> bool:
        """Ping host to check if alive"""
        try:
            # Use platform-specific ping command
            import platform
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
            
            command = ['ping', param, '1', timeout_param, str(timeout), ip]
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 1
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """Get hostname for IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except Exception:
            return None
    
    def _get_mac_address(self, ip: str) -> Optional[str]:
        """Get MAC address for IP (works on same subnet)"""
        try:
            # Use arp command
            import platform
            if platform.system().lower() == 'windows':
                command = ['arp', '-a', ip]
            else:
                command = ['arp', '-n', ip]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2,
                text=True
            )
            
            if result.returncode == 0:
                # Parse MAC address from output
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                match = re.search(mac_pattern, result.stdout)
                if match:
                    return match.group(0)
            
            return None
        except Exception:
            return None
    
    def _scan_common_ports(self, ip: str) -> List[int]:
        """Scan common ports to identify services"""
        common_ports = [
            80,    # HTTP
            443,   # HTTPS
            8080,  # HTTP alternate
            8123,  # Home Assistant
            8883,  # MQTT
            1883,  # MQTT
            22,    # SSH
            3389,  # RDP
            5000,  # Flask/Python
            9000,  # Portainer
        ]
        
        open_ports = []
        for port in common_ports:
            if self._check_port(ip, port, timeout=0.5):
                open_ports.append(port)
        
        return open_ports
    
    def _check_port(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        """Check if port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _identify_device_type(self, device: Dict[str, Any]) -> str:
        """Identify device type based on available information"""
        hostname = device.get("hostname", "").lower() if device.get("hostname") else ""
        ports = device.get("ports", [])
        
        # Check for Home Assistant
        if 8123 in ports:
            return "home_assistant"
        
        # Check for common device types
        if "raspberry" in hostname or "raspberrypi" in hostname:
            return "raspberry_pi"
        
        if "homeassistant" in hostname or "hass" in hostname:
            return "home_assistant"
        
        if 1883 in ports or 8883 in ports:
            return "mqtt_broker"
        
        if 22 in ports and (80 in ports or 443 in ports):
            return "linux_server"
        
        if 3389 in ports:
            return "windows_pc"
        
        if 80 in ports or 443 in ports:
            return "web_server"
        
        return "unknown"
    
    async def find_home_assistant(self) -> Optional[Dict[str, Any]]:
        """
        Find Home Assistant instance on network
        
        Returns:
            Home Assistant device info or None
        """
        logger.info("Searching for Home Assistant...")
        
        devices = await self.scan_network()
        
        # Look for Home Assistant
        ha_devices = [d for d in devices if d["device_type"] == "home_assistant"]
        
        if ha_devices:
            ha = ha_devices[0]
            logger.info(f"Found Home Assistant at {ha['ip']}")
            
            # Try to verify it's actually HA
            if await self._verify_home_assistant(ha['ip']):
                return ha
        
        # If not found by port, check all web servers
        web_servers = [d for d in devices if 8123 in d.get("ports", [])]
        for server in web_servers:
            if await self._verify_home_assistant(server['ip']):
                server["device_type"] = "home_assistant"
                return server
        
        logger.warning("Home Assistant not found on network")
        return None
    
    async def _verify_home_assistant(self, ip: str) -> bool:
        """Verify if IP is running Home Assistant"""
        try:
            import aiohttp
            
            url = f"http://{ip}:8123/api/"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                    if response.status == 401:  # Unauthorized = HA is there
                        return True
                    data = await response.json()
                    return "message" in data and "API running" in data.get("message", "")
        except Exception:
            return False
    
    def format_devices_report(self, devices: List[Dict[str, Any]]) -> str:
        """
        Format devices into a readable report
        
        Args:
            devices: List of discovered devices
            
        Returns:
            Formatted report string
        """
        if not devices:
            return "No devices found on network."
        
        report = f"**Network Scan Results**\n\n"
        report += f"Network: {self.network}\n"
        report += f"Found {len(devices)} device(s)\n\n"
        
        # Group by device type
        by_type = {}
        for device in devices:
            dtype = device["device_type"]
            if dtype not in by_type:
                by_type[dtype] = []
            by_type[dtype].append(device)
        
        # Format each type
        type_emojis = {
            "home_assistant": "🏠",
            "raspberry_pi": "🥧",
            "mqtt_broker": "📡",
            "linux_server": "🖥️",
            "windows_pc": "💻",
            "web_server": "🌐",
            "unknown": "❓"
        }
        
        for dtype, devs in sorted(by_type.items()):
            emoji = type_emojis.get(dtype, "•")
            report += f"**{emoji} {dtype.replace('_', ' ').title()} ({len(devs)}):**\n"
            
            for dev in devs:
                report += f"• {dev['ip']}"
                if dev.get('hostname'):
                    report += f" ({dev['hostname']})"
                if dev.get('ports'):
                    report += f" - Ports: {', '.join(map(str, dev['ports']))}"
                report += "\n"
            report += "\n"
        
        return report


class DeviceDiscovery:
    """Discovers and configures Home Assistant devices"""
    
    def __init__(self, ha_controller):
        """
        Initialize device discovery
        
        Args:
            ha_controller: Home Assistant controller instance
        """
        self.ha = ha_controller
        self.scanner = NetworkScanner()
    
    async def discover_all_devices(self) -> Dict[str, Any]:
        """
        Discover all devices and Home Assistant entities
        
        Returns:
            Discovery results
        """
        results = {
            "network_devices": [],
            "ha_entities": [],
            "suggestions": []
        }
        
        # Scan network
        results["network_devices"] = await self.scanner.scan_network()
        
        # Get HA entities
        try:
            states = await self.ha.get_all_states()
            results["ha_entities"] = states
        except Exception as e:
            logger.error(f"Error getting HA entities: {e}")
        
        # Generate suggestions
        results["suggestions"] = self._generate_suggestions(
            results["network_devices"],
            results["ha_entities"]
        )
        
        return results
    
    def _generate_suggestions(
        self,
        network_devices: List[Dict[str, Any]],
        ha_entities: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate configuration suggestions"""
        suggestions = []
        
        # Check for Home Assistant
        ha_devices = [d for d in network_devices if d["device_type"] == "home_assistant"]
        if not ha_devices:
            suggestions.append("⚠️ No Home Assistant found on network. Please verify it's running.")
        
        # Check for MQTT broker
        mqtt_devices = [d for d in network_devices if d["device_type"] == "mqtt_broker"]
        if mqtt_devices and not any("mqtt" in e.get("entity_id", "") for e in ha_entities):
            suggestions.append("💡 MQTT broker found but no MQTT entities in HA. Consider adding MQTT integration.")
        
        # Check for unconfigured devices
        total_network = len(network_devices)
        total_entities = len(ha_entities)
        
        if total_network > total_entities + 5:  # Allow some overhead
            suggestions.append(f"💡 Found {total_network} network devices but only {total_entities} HA entities. Some devices may not be configured.")
        
        return suggestions
