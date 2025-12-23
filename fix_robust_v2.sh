#!/bin/bash
#
# 🛡️ ROBUST UPGRADE SCRIPT (SYNTAX FIXED)
#
# v2 Fix: Properly escapes backslashes for python-generation
#

echo "🛡️ Re-Applying Robust Business-Grade Update..."
cd ~/homeai-bot || exit

# ---------------------------------------------------------
# 1. UPDATE UTILS.PY (Parsing & Formatting)
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

def format_device_list(devices: List[Dict[str, Any]], max_items: int = 20) -> str:
    """Format device list, hiding noisy system entities"""
    if not devices:
        return "No devices found"
    
    # Business Grade Filtering: Hide system internals
    SYSTEM_TERMS = ["sun", "backup", "update", "zone", "person", "input_", "scene", "script", "automation", "weather"]
    
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
        
        # Icon based on domain
        domain = entity_id.split(".")[0]
        icon = "•"
        if domain == "light": icon = "💡"
        elif domain == "switch": icon = "🔌"
        elif domain == "cover": icon = "🪟"
        elif domain == "lock": icon = "🔒"
        elif domain == "climate": icon = "🌡️"
        elif domain == "sensor": icon = "📊"
        
        state_icon = "✅" if state in ["on", "open", "unlocked", "home"] else "⭕"
        lines.append(f"{icon} {name}: {state_icon} {state}")
    
    if len(clean_devices) > max_items:
        lines.append(f"... and {len(clean_devices) - max_items} more")
    
    return "\n".join(lines)

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
# 2. UPDATE HOMEAI_BOT.PY (Function Replacement)
# ---------------------------------------------------------

# NOTE: We use double backslashes \\n for newlines inside the python string
# effectively escaping them so they arrive as \n in the final file.

cat > patch_bot.py << 'EOF'
import sys
import re

# New Function 1: Smart Natural Language Handler
# Double-escaped newlines: \\n
new_handle_nl = """async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "Handle with Regex + Smart LLM Parsing"
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

        # 2. SMART FALLBACK
        # If no devices found, and LLM enabled, ask for help
        if not final_devices and not is_retry and llm.enabled:
            progress = await update.message.reply_text(f"🤔 Looking for '{target}'...")
            
            # Send simplified list to LLM
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
                # Retry with new info
                return await execute_command(new_cmd, is_retry=True)
                
            await update.message.reply_text(f"❌ Could not find any device matching '{target}'.")
            return

        if not final_devices:
            await update.message.reply_text(f"❌ No devices found for '{target}'.")
            return

        # Execute
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

    if command_info:
        await execute_command(command_info)
    elif llm.enabled:
        prog = await update.message.reply_text("🤔 Analyzing...")
        cmd = await llm.analyze_command(message_text, {})
        await prog.delete()
        if cmd: await execute_command(cmd)
        else: await update.message.reply_text("🤷 I don't understand based on my rules.")
"""

# New Function 2: Cleaner Devices Command
# Double-escaped newlines: \\n
new_devices_cmd = """async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    "List devices cleanly"
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return
    
    await update.message.reply_text("📋 Fetching devices...")
    try:
        states = await ha.get_all_states()
        msg = "🏠 **My Devices**\\n\\n"
        msg += format_device_list(states, max_items=25)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Error fetching list")
"""

try:
    with open('homeai_bot.py', 'r') as f:
        lines = f.readlines()

    # Helper to replace block
    def replace_block(lines, start_marker, end_marker, new_content):
        # Scan for range
        start_idx = -1
        end_idx = -1
        
        # Find start
        for i, line in enumerate(lines):
            if start_marker in line:
                start_idx = i
                break
        
        if start_idx == -1:
            print(f"⚠️ Could not find block start: {start_marker}")
            return lines

        # Find end (after start)
        for i in range(start_idx + 1, len(lines)):
            if end_marker in lines[i]:
                end_idx = i
                break
        
        if end_idx == -1:
             print(f"⚠️ Could not find block end: {end_marker}")
             return lines
             
        # Replace
        print(f"✅ Replacing lines {start_idx} to {end_idx}")
        # Insert new content, ensuring logical spacing
        return lines[:start_idx] + [new_content + "\n\n"] + lines[end_idx:]

    # 1. Replace handle_natural_language
    lines = replace_block(lines, "async def handle_natural_language", "async def proactive_alert_callback", new_handle_nl)

    # 2. Replace devices_command
    # To be robust, if we can't find exact end, we'll assume it ends at next async def
    # Let's find devices_command index manually to be sure
    d_start = -1
    for i, line in enumerate(lines):
        if "async def devices_command" in line:
            d_start = i
            break
            
    if d_start != -1:
        # Find next async def
        d_end = -1
        for i in range(d_start + 1, len(lines)):
            if "async def " in lines[i]:
                d_end = i
                break
        
        if d_end != -1:
            print(f"✅ Replacing devices_command (lines {d_start}-{d_end})")
            lines = lines[:d_start] + [new_devices_cmd + "\n\n"] + lines[d_end:]
        else:
             print("⚠️ Could not find end of devices_command")
    else:
        print("⚠️ Could not find devices_command")

    with open('homeai_bot.py', 'w') as f:
        f.writelines(lines)
    print("✅ Successfully Patched homeai_bot.py")

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 patch_bot.py

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
    # Restore backup? For now, user can see error.
fi
