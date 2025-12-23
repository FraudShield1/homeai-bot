#!/bin/bash
#
# 🧠 MEGA-FIX: Intelligence & Usability
# 
# This script forcefully updates the bot to:
# 1. Be "Smart" -> If it can't find a device (like "bedroom"), it asks the LLM to find the best match (e.g., "chambre").
# 2. Be "Clean" -> Hides "sun", "backup", "update" entities from the device list.
# 3. Be "Robust" -> Fixes the parsing of "turn off lights" to not look for a device named "lights".
#

echo "🚀 Applying Intelligent Upgrade..."
cd ~/homeai-bot || exit

# -----------------------------------------------------------------------------
# 1. OVERWRITE UTILS.PY (Better Parsing & Cleaner Lists)
# -----------------------------------------------------------------------------
cat > utils.py << 'EOF'
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
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        now = datetime.now().timestamp()
        if user_id not in self.requests:
            self.requests[user_id] = []
        self.requests[user_id] = [ts for ts in self.requests[user_id] if now - ts < self.window_seconds]
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True

_rate_limiter = RateLimiter()

def rate_limiter(user_id: int) -> bool:
    return _rate_limiter.is_allowed(user_id)

def is_user_authorized(user_id: int, allowed_users: List[int]) -> bool:
    return user_id in allowed_users

def format_device_list(devices: List[Dict[str, Any]], max_items: int = 15) -> str:
    """Format device list, hiding noisy system entities"""
    if not devices:
        return "No devices found"
    
    # Filter out noisy system entities
    SYSTEM_TERMS = ["sun", "backup", "update", "zone", "person", "input_", "scene", "script", "automation"]
    
    clean_devices = []
    for d in devices:
        eid = d.get("entity_id", "").lower()
        if any(term in eid for term in SYSTEM_TERMS):
            continue
        clean_devices.append(d)
        
    lines = []
    for device in clean_devices[:max_items]:
        entity_id = device.get("entity_id", "")
        name = device.get("attributes", {}).get("friendly_name", entity_id)
        state = device.get("state", "unknown")
        
        state_icon = "✅" if state in ["on", "open", "unlocked", "home"] else "⭕"
        lines.append(f"{state_icon} {name} ({state})")
    
    if len(clean_devices) > max_items:
        lines.append(f"... and {len(clean_devices) - max_items} more")
    
    return "\n".join(lines)

def parse_natural_command(text: str) -> Optional[Dict[str, Any]]:
    text = text.lower().strip()
    
    patterns = [
        (r"turn (on|off) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": _infer_domain(m.group(2)), "target": _clean_target(m.group(2))
        }),
        (r"set (?:the )?(.+?)(?:temperature)? to (\d+)", lambda m: {
            "action": "set_temperature", "domain": "climate", "target": _clean_target(m.group(1)), "value": m.group(2)
        }),
        (r"(open|close) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": "cover", "target": _clean_target(m.group(2))
        }),
        (r"(lock|unlock) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": "lock", "target": _clean_target(m.group(2))
        }),
        (r"(?:what(?:'s| is) the |is the |check the )(.+?)(?:\?|$)", lambda m: {
            "action": "status", "domain": _infer_domain(m.group(1)), "target": _clean_target(m.group(1))
        }),
        (r"^(.+?)\s+(on|off)$", lambda m: {
            "action": m.group(2), "domain": _infer_domain(m.group(1)), "target": _clean_target(m.group(1))
        }),
    ]
    
    for pattern, parser in patterns:
        match = re.search(pattern, text)
        if match:
            return parser(match)
    return None

def _infer_domain(target: str) -> str:
    target = target.lower()
    if any(w in target for w in ["light", "lamp", "bulb"]): return "light"
    if any(w in target for w in ["temp", "thermostat", "climate", "ac", "heat"]): return "climate"
    if any(w in target for w in ["blind", "shade", "curtain", "garage", "window"]): return "cover"
    if any(w in target for w in ["lock", "door lock"]): return "lock"
    if any(w in target for w in ["switch", "plug", "outlet"]): return "switch"
    if "fan" in target: return "fan"
    return "light"

def _clean_target(target: str) -> str:
    # UPDATED: Remove generic words so "bedroom lights" becomes "bedroom"
    remove_words = [
        "the", "my", "a", "an", "all", "please", 
        "light", "lights", "switch", "switches", 
        "bulb", "bulbs", "lamp", "lamps",
        "device", "devices"
    ]
    words = target.split()
    words = [w for w in words if w.lower() not in remove_words]
    result = " ".join(words).strip("?.,!")
    return result if result else "all"

def format_temperature(temp: float, unit: str = "C") -> str:
    return f"{temp:.1f}°{unit}"
EOF

# -----------------------------------------------------------------------------
# 2. OVERWRITE HOMEAI_BOT.PY (With Smart Fallback)
# -----------------------------------------------------------------------------
# We read the existing file first to keep imports and init correct, but we really need 
# to replace the handle_natural_language function. Since previous regex replacements failing,
# we will rewrite the specific logic block using a more robust python script.

cat > apply_bot_logic.py << 'EOF'
import re

new_logic = """
async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "Handle natural language commands using Regex -> then Smart Fallback"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return

    message_text = update.message.text.lower().strip()
    
    # 1. Shortcuts
    if message_text in ["gm", "good morning"]:
        await activate_scene_by_name(update, "morning"); return
    elif message_text in ["leaving", "bye"]:
        await activate_scene_by_name(update, "away"); return
    
    # 2. Parse
    command_info = parse_natural_command(message_text)
    
    # 3. Execution Wrapper
    async def execute_command(cmd_info, is_retry=False):
        action = cmd_info.get("action")
        domain = cmd_info.get("domain")
        target = cmd_info.get("target")
        value = cmd_info.get("value")
        
        states = await ha.get_all_states()
        
        # Domain Filter
        candidates = []
        if domain:
            candidates = [s for s in states if s.get("entity_id", "").startswith(domain + ".")]
        if not candidates: candidates = states
        
        # Target Match
        final_devices = []
        if target and target not in ["all", "everything", "home"]:
            for d in candidates:
                # MATCHING LOGIC: Check both ID and Friendly Name
                eid = d.get("entity_id", "").lower()
                fname = d.get("attributes", {}).get("friendly_name", "").lower()
                clean_target = target.lower()
                
                if clean_target in eid or clean_target in fname:
                    final_devices.append(d)
        else:
            final_devices = candidates

        # --- SMART FALLBACK ---
        if not final_devices:
            # If we found no devices, ASK THE LLM using the full list
            if llm.enabled and not is_retry:
                progress = await update.message.reply_text(f"🤔 Can't find '{target}'. Checking translations...")
                
                # Create a list of all friendly names for the LLM
                all_names = [f"{d.get('attributes',{}).get('friendly_name')} ({d.get('entity_id')})" for d in candidates]
                
                # Ask LLM to pick the best match
                ctx = {
                    "user_said": message_text,
                    "target_not_found": target,
                    "available_devices": all_names[:100] # Limit to avoid token limit
                }
                
                new_cmd = await llm.analyze_command(message_text, ctx)
                await progress.delete()
                
                if new_cmd and new_cmd.get("target"):
                    # Recurse with new target found by LLM
                    return await execute_command(new_cmd, is_retry=True)
            
            await update.message.reply_text(f"❌ No devices found matching '{target}'.")
            return

        # Execute
        success_count = 0
        svc_map = {
            "turn_on": "turn_on", "on": "turn_on", 
            "turn_off": "turn_off", "off": "turn_off",
            "open": "open_cover", "close": "close_cover",
            "lock": "lock", "unlock": "unlock"
        }
        
        svc = svc_map.get(action)
        if svc:
             for d in final_devices:
                 if await ha.call_service(d["entity_id"].split(".")[0], svc, d["entity_id"]):
                     success_count += 1
        elif action == "set_temperature" and value:
             for d in final_devices:
                 await ha.call_service("climate", "set_temperature", d["entity_id"], {"temperature": float(value)})
                 success_count += 1
        
        t_name = target if target else "all"
        await update.message.reply_text(f"✅ Executed {action} on {success_count} device(s) ({t_name}).")
        db.log_command(update.effective_user.id, message_text, "natural_language", True)

    # 4. Run it
    if command_info:
        await execute_command(command_info)
    elif llm.enabled:
        # Direct LLM fallback if regex failed completely
        prog = await update.message.reply_text("🤔 Analyzing command...")
        states = await ha.get_all_states()
        names = [d.get("attributes",{}).get("friendly_name") for d in states[:50]]
        cmd = await llm.analyze_command(message_text, {"devices": names})
        await prog.delete()
        if cmd: await execute_command(cmd)
        else: await update.message.reply_text("🤷 Couldn't understand command.")
"""

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # Regex to replace handle_natural_language block
    # We look for "async def handle_natural_language" and replace until next async def
    # This is "async def proactive_alert_callback"
    
    pattern = r"(async def handle_natural_language\(.*?:)(.*?)(?=\nasync def proactive_alert_callback)"
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_logic + "\n\n\n", content, count=1, flags=re.DOTALL)
        with open('homeai_bot.py', 'w') as f:
            f.write(new_content)
        print("✅ Replaced Bot Logic with Smart Fallback")
    else:
        print("⚠️ Failed to replace logic (regex mismatch)")

except Exception as e:
    print(e)
EOF

python3 apply_bot_logic.py

echo "🔄 Restarting Bot..."
pkill -f homeai_bot.py
source venv/bin/activate
python3 homeai_bot.py
