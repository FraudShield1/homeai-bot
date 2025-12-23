"""
Utility functions for HomeAI bot
"""

import logging
import re
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import json


def setup_logging(log_level: str = "INFO", log_file: str = "logs/homeai.log") -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        
    Returns:
        Configured logger
    """
    # Create logs directory if it doesn't exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Setup handlers
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def is_user_authorized(user_id: int, allowed_users: List[int]) -> bool:
    """
    Check if user is authorized to use the bot
    
    Args:
        user_id: Telegram user ID
        allowed_users: List of allowed user IDs
        
    Returns:
        True if authorized, False otherwise
    """
    return user_id in allowed_users


class RateLimiter:
    """Simple rate limiter for user commands"""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # user_id: [timestamps]
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now().timestamp()
        
        # Initialize user if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old timestamps
        self.requests[user_id] = [
            ts for ts in self.requests[user_id]
            if now - ts < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limiter(user_id: int) -> bool:
    """
    Check rate limit for user
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if allowed, False if rate limited
    """
    return _rate_limiter.is_allowed(user_id)


def format_device_list(devices: List[Dict[str, Any]], max_items: int = 10) -> str:
    """
    Format device list for display
    
    Args:
        devices: List of device state dictionaries
        max_items: Maximum items to show
        
    Returns:
        Formatted string
    """
    if not devices:
        return "No devices found"
    
    lines = []
    for i, device in enumerate(devices[:max_items]):
        entity_id = device.get("entity_id", "")
        name = device.get("attributes", {}).get("friendly_name", entity_id)
        state = device.get("state", "unknown")
        
        state_icon = "✅" if state in ["on", "open", "unlocked", "home"] else "⭕"
        lines.append(f"{state_icon} {name} ({state})")
    
    if len(devices) > max_items:
        lines.append(f"... and {len(devices) - max_items} more")
    
    return "\n".join(lines)


def parse_natural_command(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse natural language command into structured format
    
    Args:
        text: User's text message
        
    Returns:
        Dictionary with action, domain, target, and value or None
    """
    text = text.lower().strip()
    
    # Patterns for common commands
    patterns = [
        # Turn on/off patterns
        (r"turn (on|off) (?:the )?(.+)", lambda m: {
            "action": m.group(1),
            "domain": _infer_domain(m.group(2)),
            "target": _clean_target(m.group(2)),
        }),
        
        # Set temperature patterns
        (r"set (?:the )?(.+?)(?:temperature)? to (\d+)", lambda m: {
            "action": "set_temperature",
            "domain": "climate",
            "target": _clean_target(m.group(1)),
            "value": m.group(2),
        }),
        
        # Open/close patterns
        (r"(open|close) (?:the )?(.+)", lambda m: {
            "action": m.group(1),
            "domain": "cover",
            "target": _clean_target(m.group(2)),
        }),
        
        # Lock/unlock patterns
        (r"(lock|unlock) (?:the )?(.+)", lambda m: {
            "action": m.group(1),
            "domain": "lock",
            "target": _clean_target(m.group(2)),
        }),
        
        # Status patterns
        (r"(?:what(?:'s| is) the |is the |check the )(.+?)(?:\?|$)", lambda m: {
            "action": "status",
            "domain": _infer_domain(m.group(1)),
            "target": _clean_target(m.group(1)),
        }),
        
        # Simple on/off without "turn"
        (r"^(.+?)\s+(on|off)$", lambda m: {
            "action": m.group(2),
            "domain": _infer_domain(m.group(1)),
            "target": _clean_target(m.group(1)),
        }),
    ]
    
    # Try each pattern
    for pattern, parser in patterns:
        match = re.search(pattern, text)
        if match:
            return parser(match)
    
    return None


def _infer_domain(target: str) -> str:
    """
    Infer device domain from target name
    
    Args:
        target: Target device/room name
        
    Returns:
        Domain name (light, switch, climate, etc.)
    """
    target = target.lower()
    
    # Light keywords
    if any(word in target for word in ["light", "lamp", "bulb"]):
        return "light"
    
    # Climate keywords
    if any(word in target for word in ["temperature", "thermostat", "climate", "ac", "heat"]):
        return "climate"
    
    # Cover keywords
    if any(word in target for word in ["blind", "shade", "curtain", "garage", "door", "window"]):
        return "cover"
    
    # Lock keywords
    if any(word in target for word in ["lock", "door lock"]):
        return "lock"
    
    # Switch keywords
    if any(word in target for word in ["switch", "plug", "outlet"]):
        return "switch"
    
    # Fan keywords
    if any(word in target for word in ["fan"]):
        return "fan"
    
    # Default to light for room names
    return "light"


def _clean_target(target: str) -> str:
    """
    Clean target name by removing common articles and words
    
    Args:
        target: Raw target string
        
    Returns:
        Cleaned target string
    """
    # Remove common words
    remove_words = ["the", "my", "a", "an", "all"]
    words = target.split()
    words = [w for w in words if w.lower() not in remove_words]
    
    # Remove trailing question marks and punctuation
    result = " ".join(words).strip("?.,!")
    
    return result if result else "all"


def format_temperature(temp: float, unit: str = "C") -> str:
    """
    Format temperature for display
    
    Args:
        temp: Temperature value
        unit: Unit (C or F)
        
    Returns:
        Formatted temperature string
    """
    return f"{temp:.1f}°{unit}"


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration (e.g., "2h 15m")
    """
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        return f"{hours}h {remaining_minutes}m" if remaining_minutes else f"{hours}h"
    
    days = hours // 24
    remaining_hours = hours % 24
    return f"{days}d {remaining_hours}h"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem use
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")
    
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:190] + (f".{ext}" if ext else "")
    
    return filename


def parse_relative_time(time_str: str) -> Optional[int]:
    """
    Parse relative time string to seconds
    
    Args:
        time_str: Time string (e.g., "2 hours", "30 minutes", "1h", "30m")
        
    Returns:
        Number of seconds or None if invalid
    """
    time_str = time_str.lower().strip()
    
    # Pattern: number + unit
    patterns = [
        (r"(\d+)\s*(?:hour|hours|h)", 3600),
        (r"(\d+)\s*(?:minute|minutes|min|m)", 60),
        (r"(\d+)\s*(?:second|seconds|sec|s)", 1),
    ]
    
    for pattern, multiplier in patterns:
        match = re.search(pattern, time_str)
        if match:
            return int(match.group(1)) * multiplier
    
    return None


def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> Dict:
    """
    Create inline keyboard markup for Telegram
    
    Args:
        buttons: 2D list of button dictionaries with 'text' and 'callback_data'
        
    Returns:
        Inline keyboard markup dictionary
    """
    keyboard = []
    for row in buttons:
        keyboard.append([
            {"text": btn["text"], "callback_data": btn["callback_data"]}
            for btn in row
        ])
    
    return {"inline_keyboard": keyboard}


def log_command(user_id: int, username: str, command: str, success: bool = True):
    """
    Log command execution
    
    Args:
        user_id: User ID
        username: Username
        command: Command executed
        success: Whether command succeeded
    """
    logger = logging.getLogger(__name__)
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"[{status}] User {user_id} ({username}): {command}")
