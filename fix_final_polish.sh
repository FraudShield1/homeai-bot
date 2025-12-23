#!/bin/bash
#
# ✨ FINAL POLISH SCRIPT
#
# 1. Update Utils for cleaner device list
# 2. Update Bot Logic for:
#    - Smart Device Fallback (English -> French)
#    - General Chat Fallback (math/jokes/advice)
#    - Robust Error Handling
#

echo "✨ Applying Final Polish..."
cd ~/homeai-bot || exit

# ---------------------------------------------------------
# 1. UPDATE UTILS.PY (Cleaner UI)
# ---------------------------------------------------------
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

def format_device_list(devices: List[Dict[str, Any]], max_items: int = 30) -> str:
    """Format device list, hiding noisy system entities"""
    if not devices:
        return "No devices found"
    
    # Business Grade Filtering
    SYSTEM_TERMS = ["sun", "backup", "update", "zone", "person", "input_", "scene", "script", "automation", "weather", "alarm", "mobile_app"]
    
    clean_devices = []
    for d in devices:
        eid = d.get("entity_id", "").lower()
        if any(term in eid for term in SYSTEM_TERMS):
            continue
        clean_devices.append(d)
        
    # Group by Domain
    grouped = {}
    for d in clean_devices:
        domain = d["entity_id"].split(".")[0]
        if domain not in grouped: grouped[domain] = []
        grouped[domain].append(d)
        
    lines = []
    # Prioritize important domains
    priority = ["light", "switch", "cover", "climate", "lock", "sensor", "media_player"]
    
    for dom in priority:
        if dom in grouped:
            lines.append(f"**{dom.title()}s**")
            for d in grouped[dom]:
                state = d.get("state", "?")
                name = d.get("attributes", {}).get("friendly_name", d["entity_id"])
                icon = "💡" if dom == "light" else "🔌" if dom == "switch" else "🪟" if dom == "cover" else "🌡️"
                status = "✅" if state in ["on", "open", "home"] else "⭕"
                lines.append(f"{status} {name} ({state})")
            lines.append("") # spacer
            del grouped[dom]
            
    # Remaining
    for dom, devs in grouped.items():
        lines.append(f"**{dom.title()}**")
        for d in devs:
            lines.append(f"• {d.get('attributes',{}).get('friendly_name')} ({d['state']})")
        lines.append("")

    return "\n".join(lines) if lines else "No controllable devices found."

def parse_natural_command(text: str) -> Optional[Dict[str, Any]]:
    text = text.lower().strip()
    
    patterns = [
        # Explicit "turn on/off"
        (r"turn (on|off) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": _infer_domain(m.group(2)), "target": _clean_target(m.group(2))
        }),
        # Set temp
        (r"set (?:the )?(.+?)(?:temperature)? to (\d+)", lambda m: {
            "action": "set_temperature", "domain": "climate", "target": _clean_target(m.group(1)), "value": m.group(2)
        }),
        # Open/Close
        (r"(open|close) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": "cover", "target": _clean_target(m.group(2))
        }),
        # Lock/Unlock
        (r"(lock|unlock) (?:the )?(.+)", lambda m: {
            "action": m.group(1), "domain": "lock", "target": _clean_target(m.group(2))
        }),
        # Status
        (r"(?:what(?:'s| is) the |is the |check the )(.+?)(?:\?|$)", lambda m: {
            "action": "status", "domain": _infer_domain(m.group(1)), "target": _clean_target(m.group(1))
        }),
        # Simple "light on"
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
    if any(w in target for w in ["blind", "shade", "curtain", "garage", "window", "shutter", "volet"]): return "cover"
    if any(w in target for w in ["lock", "door lock"]): return "lock"
    if any(w in target for w in ["switch", "plug", "outlet", "prise"]): return "switch"
    if "fan" in target: return "fan"
    return "light" # Default guess

def _clean_target(target: str) -> str:
    # Remove generic words so "bedroom lights" becomes "bedroom"
    remove_words = [
        "the", "my", "a", "an", "all", "please", 
        "light", "lights", "switch", "switches", 
        "bulb", "bulbs", "lamp", "lamps",
        "device", "devices", "volet", "shutter"
    ]
    words = target.split()
    words = [w for w in words if w.lower() not in remove_words]
    result = " ".join(words).strip("?.,!")
    return result if result else "all"

def format_temperature(temp: float, unit: str = "C") -> str:
    return f"{temp:.1f}°{unit}"
EOF

# ---------------------------------------------------------
# 2. UPDATE HOMEAI_BOT.PY (Polished Logic)
# ---------------------------------------------------------

cat > patch_bot_final.py << 'EOF'
import sys

# New Function 1: Smart Natural Language Handler with Chat Fallback
new_handle_nl = """async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "Handle with Regex -> Smart Match -> General Chat Fallback"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return

    message_text = update.message.text.lower().strip()
    
    # Shortcuts
    if message_text in ["gm", "good morning"]: await activate_scene_by_name(update, "morning"); return
    elif message_text in ["bye", "leaving"]: await activate_scene_by_name(update, "away"); return
    
    # 1. Regex Parse
    command_info = parse_natural_command(message_text)
    
    async def execute_command(cmd_info, is_retry=False):
        action = cmd_info.get("action")
        domain = cmd_info.get("domain")
        target = cmd_info.get("target")
        value = cmd_info.get("value")
        
        # Validation checks
        if not action or not domain: return False

        states = await ha.get_all_states()
        
        # Domain Filter
        candidates = []
        if domain: candidates = [s for s in states if s.get("entity_id","").startswith(domain)]
        if not candidates: candidates = states
        
        # Target Filter (Fuzzy Match)
        final_devices = []
        if target and target not in ["all", "home", "house"]:
            t_clean = target.lower()
            for d in candidates:
                eid = d.get("entity_id", "").lower()
                name = d.get("attributes", {}).get("friendly_name", "").lower()
                if t_clean in eid or t_clean in name:
                    final_devices.append(d)
        else:
            final_devices = candidates

        # 2. SMART DEVICE MATCHING (LLM)
        if not final_devices:
            # Only retry if LLM is enabled and we haven't tried yet
            if not is_retry and llm.enabled and target:
                progress = await update.message.reply_text(f"🤔 Looking for '{target}'...")
                
                # Full list of devices for mapping
                simple_list = [f"{d.get('attributes',{}).get('friendly_name')} ({d.get('entity_id')})" for d in candidates]
                
                ctx = {
                    "user_command": message_text,
                    "target_searched": target,
                    "available_devices": simple_list[:100]
                }
                
                # Ask LLM to translate (e.g. "bedroom" -> "chambre")
                new_cmd = await llm.analyze_command(message_text, ctx)
                await progress.delete()
                
                if new_cmd and (new_cmd.get("target") != target or new_cmd.get("domain") != domain):
                    # Recurse with new target
                    return await execute_command(new_cmd, is_retry=True)
            
            # If still no devices found, return False to trigger General Chat
            return False

        # Execute Actions
        success = 0
        for d in final_devices:
            d_domain = d["entity_id"].split(".")[0]
            svc = None
            if action in ["turn_on", "on"]: svc = "turn_on"
            elif action in ["turn_off", "off"]: svc = "turn_off"
            elif action == "open": svc = "open_cover" if d_domain == "cover" else "turn_on"
            elif action == "close": svc = "close_cover" if d_domain == "cover" else "turn_off"
            elif action == "set_temperature" and value:
                await ha.call_service(d_domain, "set_temperature", d["entity_id"], {"temperature": float(value)})
                success += 1
                continue
            
            if svc:
                if await ha.call_service(d_domain, svc, d["entity_id"]):
                    success += 1
        
        t_name = target if target else "all"
        await update.message.reply_text(f"✅ Executed {action} on {success}/{len(final_devices)} devices.")
        db.log_command(update.effective_user.id, message_text, "natural_language", True)
        return True

    # Try to execute if command found
    if command_info:
        if await execute_command(command_info):
            return

    # 3. GENERAL CHAT FALLBACK (The "2+2" Fix)
    if llm.enabled:
        # If we reached here, it's not a command OR command failed to find devices
        await update.message.chat.send_action(action="typing")
        
        # Get context for relevant chat
        states = await ha.get_all_states()
        summary = {
            "lights_on_count": sum(1 for s in states if "light" in s["entity_id"] and s["state"] == "on"),
            "doors_open": [s["attributes"].get("friendly_name") for s in states if "binary_sensor" in s["entity_id"] and "door" in s["entity_id"] and s["state"] == "on"],
            "temperature_sensors": [f"{s['attributes'].get('friendly_name')}: {s['state']}" for s in states if "sensor" in s["entity_id"] and "temperature" in s["entity_id"]]
        }
        
        response = await llm.generate_smart_response(message_text, summary)
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text("🤔 I'm not sure how to respond to that.")
    else:
        await update.message.reply_text("🤷 I don't understand that command and AI is disabled.")
"""

new_devices_cmd = """async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "List devices cleanly"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return
    
    await update.message.reply_text("📋 Fetching devices...")
    try:
        states = await ha.get_all_states()
        msg = "🏠 **My Devices**\\n\\n"
        msg += format_device_list(states, max_items=40)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error fetching list")
"""

try:
    with open('homeai_bot.py', 'r') as f:
        lines = f.readlines()

    def replace_function(lines, func_name, end_marker, new_code):
        start = -1
        end = -1
        search_str = f"async def {func_name}"
        
        for i, line in enumerate(lines):
            if search_str in line:
                start = i
                break
        
        if start == -1:
            print(f"⚠️ Could not find {func_name}")
            return lines

        for i in range(start + 1, len(lines)):
            if end_marker in lines[i]:
                end = i
                break
        
        if end == -1:
            print(f"⚠️ Could not find end of {func_name}")
            return lines

        print(f"✅ Replacing {func_name} (lines {start}-{end})")
        return lines[:start] + [new_code + "\n\n"] + lines[end:]

    # Replace handle_natural_language
    lines = replace_function(lines, "handle_natural_language", "async def proactive_alert_callback", new_handle_nl)
    
    # Replace devices_command (finding next async def is safer)
    d_start = -1
    for i, line in enumerate(lines):
        if "async def devices_command" in line:
            d_start = i
            break
            
    if d_start != -1:
        d_end = -1
        # Look for next async def manually
        for i in range(d_start + 1, len(lines)):
            if "async def " in lines[i]:
                d_end = i
                break
        if d_end != -1:
             print(f"✅ Replacing devices_command (lines {d_start}-{d_end})")
             lines = lines[:d_start] + [new_devices_cmd + "\n\n"] + lines[d_end:]
        else:
             print("⚠️ Could not find devices_command end")
             
    with open('homeai_bot.py', 'w') as f:
        f.writelines(lines)
    print("✅ Successfully patched homeai_bot.py")

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 patch_bot_final.py

echo "🔄 Restarting Bot..."
pkill -f homeai_bot.py
# Verify syntax
python3 -m py_compile homeai_bot.py
if [ $? -eq 0 ]; then
    echo "✅ Syntax Check Passed"
    source venv/bin/activate
    python3 homeai_bot.py
else
    echo "❌ Syntax Error Detected! Aborting restart."
fi
