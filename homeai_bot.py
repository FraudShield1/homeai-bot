#!/usr/bin/env python3
"""
🏠 HomeAI Assistant Bot
Main entry point for the Telegram bot.
"""
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Import our modules
from llm_handler import LLMHandler
from ha_controller import HAController
from database import Database
from menu_handler import MenuHandler
from scenes import SceneManager
from document_manager import DocumentManager
from nextcloud_manager import NextcloudManager
from monitor import HomeMonitor
from network_scanner import NetworkScanner, DeviceDiscovery
from utils import (
    setup_logging,
    is_user_authorized,
    rate_limiter,
    parse_natural_command,
    format_device_list
)

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(id_str) for id_str in os.getenv("ALLOWED_USERS", "").split(",") if id_str]

# Global instances
app = None
db = None
ha = None
llm = None
menu = None
scenes = None
doc_manager = None
network_scanner = None
monitor = None
device_discovery = None

# Set up logging
logger = setup_logging()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        await update.message.reply_text("⛔ Unauthorized access.")
        return

    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)

    welcome_msg = f"""
🏠 **Welcome to HomeAI Assistant!**

Hi {user.first_name}! I'm your intelligent home automation assistant.

**Quick Commands:**
• `/status` - Home overview
• `/devices` - List devices
• `/scene` - Activate scenes
• `/menu` - Main menu

**Natural Language:**
Try saying things like:
• "Turn on living room lights"
• "Good morning"
• "Set temperature to 21"
• "What is 2+2?"

How can I help you today?
"""
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    help_text = """
📚 **Command List:**

**Control:**
• `/status` - Check home status
• `/devices` - List & control devices
• `/scene <name>` - Activate a scene
• `turn on/off <device>` - Control devices

**Smart Features:**
• `/scan` - Scan network for devices
• `/discover` - Full device discovery & analysis
• `analyze energy` - Get energy insights
• Send a photo 📸 - I'll analyze it!
• Send a voice note 🎤 - I'll transcribe it!

**System:**
• `/menu` - Interactive menu
• `/restart` - Restart the bot
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show home status overview"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    await update.message.chat.send_action(action="typing")
    
    try:
        states = await ha.get_all_states()
        
        # Calculate stats
        lights = [s for s in states if s.get("entity_id", "").startswith("light.")]
        lights_on = sum(1 for l in lights if l.get("state") == "on")
        lights_total = len(lights)
        
        switches = [s for s in states if s.get("entity_id", "").startswith("switch.")]
        switches_on = sum(1 for s in switches if s.get("state") == "on")
        switches_total = len(switches)
        
        # Climate
        climate_devices = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        climate_info = ""
        if climate_devices:
            for device in climate_devices[:2]:
                name = device.get("attributes", {}).get("friendly_name", "Climate")
                temp = device.get("attributes", {}).get("current_temperature", "N/A")
                target = device.get("attributes", {}).get("temperature", "N/A")
                climate_info += f"\n• {name}: {temp}°C (target: {target}°C)"
        
        if not climate_info:
            climate_info = "\n• No climate devices found"

        # Security
        locks = [s for s in states if s.get("entity_id", "").startswith("lock.")]
        locked_count = sum(1 for l in locks if l.get("state") == "locked")
        
        doors = [s for s in states if "door" in s.get("entity_id", "") and s.get("state") in ["on", "open"]]
        
        current_time = datetime.now().strftime("%I:%M %p")
        
        status_msg = """
🏠 **Home Status Overview**

**Lighting:**
💡 {}/{} lights on
🔌 {}/{} switches on

**Climate:**{}

**Security:**
🔒 {}/{} locks secured
🚪 {} door(s) open

**System:**
✅ Home Assistant connected
⏰ {}

Use `/devices` to see all devices or `/scene` for quick actions.
        """.format(
            lights_on, lights_total,
            switches_on, switches_total,
            climate_info,
            locked_count, len(locks),
            len(doors),
            current_time
        )
        
        await update.message.reply_text(status_msg, parse_mode="Markdown")
        db.log_command(update.effective_user.id, "/status", "status", True)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available devices cleanly"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    await update.message.reply_text("📋 Fetching devices...")
    
    try:
        states = await ha.get_all_states()
        msg = "🏠 **My Devices**\n\n"
        msg += format_device_list(states, max_items=40)
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        await update.message.reply_text(f"❌ Error listing devices: {str(e)}")


async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle natural language commands with Regex -> Smart Match -> General Chat Fallback"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    message_text = update.message.text.lower().strip()
    user_name = update.effective_user.first_name
    
    # Quick Shortcuts
    if message_text in ["gm", "good morning"]:
        await activate_scene_by_name(update, "morning")
        return
    elif message_text in ["leaving", "goodbye", "bye"]:
        await activate_scene_by_name(update, "away")
        return
    
    # 1. Regex Parsing
    command_info = parse_natural_command(message_text)
    
    # Wrapper to execute parsed command
    async def execute_command(cmd_info, is_retry=False):
        action = cmd_info.get("action")
        domain = cmd_info.get("domain")
        target = cmd_info.get("target")
        value = cmd_info.get("value")
        
        if not action or not domain: return False

        states = await ha.get_all_states()
        
        # Domain Filter
        candidates = []
        if domain: candidates = [s for s in states if s.get("entity_id", "").startswith(domain + ".")]
        if not candidates: candidates = states
        
        # Target Match (Fuzzy)
        final_devices = []
        if target and target not in ["all", "home", "house"]:
            t_clean = target.lower()
            for d in candidates:
                eid = d.get("entity_id", "").lower()
                fname = d.get("attributes", {}).get("friendly_name", "").lower()
                if t_clean in eid or t_clean in fname:
                    final_devices.append(d)
        else:
            final_devices = candidates

        # SMART DEVICE FALLBACK (LLM)
        if not final_devices:
            # If no devices found, and LLM is enabled, and we haven't retried yet...
            if not is_retry and llm.enabled and target:
                progress = await update.message.reply_text(f"🤔 Looking closely for '{target}'...")
                
                # Prepare clean list for LLM
                simple_list = []
                for d in candidates:
                    name = d.get("attributes", {}).get("friendly_name")
                    eid = d.get("entity_id")
                    if name: simple_list.append(f"{name} ({eid})")
                
                ctx = {
                    "user_command": message_text,
                    "target_searched": target,
                    "available_devices": simple_list[:100] # Limit tokens
                }
                
                # LLM Analysis
                new_cmd = await llm.analyze_command(message_text, ctx)
                await progress.delete()
                
                if new_cmd and (new_cmd.get("target") != target or new_cmd.get("domain") != domain):
                    # Recursive retry
                    return await execute_command(new_cmd, is_retry=True)
            
            # Still nothing found? Return False so we fall through to General Chat
            return False

        # Execute Actions
        success_count = 0
        executed_any = False
        
        for d in final_devices:
            d_domain = d["entity_id"].split(".")[0]
            svc = None
            if action in ["turn_on", "on"]: svc = "turn_on"
            elif action in ["turn_off", "off"]: svc = "turn_off"
            elif action in ["open"]: svc = "open_cover" if d_domain == "cover" else "turn_on"
            elif action in ["close"]: svc = "close_cover" if d_domain == "cover" else "turn_off"
            elif action in ["lock"]: svc = "lock"
            elif action in ["unlock"]: svc = "unlock"
            elif action == "set_temperature" and value:
                await ha.call_service(d_domain, "set_temperature", d["entity_id"], {"temperature": float(value)})
                executed_any = True
                success_count += 1
                continue
            
            if svc:
                if await ha.call_service(d_domain, svc, d["entity_id"]):
                    executed_any = True
                    success_count += 1
        
        # Send result
        t_name = target if target else "all"
        if executed_any:
            await update.message.reply_text(f"✅ Executed {action} on {success_count}/{len(final_devices)} devices.")
            db.log_command(update.effective_user.id, message_text, "natural_language", True)
            return True
        else:
            return False

    # Try execution if regex worked
    if command_info:
        if await execute_command(command_info):
            return

    # 3. GENERAL CHAT FALLBACK
    # If we are here, it wasn't a command, or the command utterly failed to match devices.
    if llm.enabled:
        await update.message.chat.send_action(action="typing")
        
        # Gather lite context
        states = await ha.get_all_states()
        summary = {
            "lights_on": sum(1 for s in states if "light" in s["entity_id"] and s["state"] == "on"),
            "temperature": [f"{s['attributes'].get('friendly_name')}: {s['state']}" for s in states if "sensor" in s["entity_id"] and "temperature" in s["entity_id"]],
            "locks": [f"{s['attributes'].get('friendly_name')}: {s['state']}" for s in states if "lock" in s["entity_id"]]
        }
        
        response = await llm.generate_smart_response(message_text, summary)
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            await update.message.reply_text("🤔 I'm stumped.")
    else:
        await update.message.reply_text("🤷 I don't understand that command, and AI is offline.")


async def scene_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle scene activation"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    scene_name = " ".join(context.args) if context.args else None
    
    if not scene_name:
        all_scenes = scenes.list_scenes()
        msg = "🎬 **Available Scenes:**\n\n"
        for s in all_scenes:
            msg += f"• **{s['name']}** - {s['description']}\n"
        msg += "\n**Usage:** `/scene <name>`"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    await activate_scene_by_name(update, scene_name)

async def activate_scene_by_name(update, scene_name):
    status_msg = await update.message.reply_text(f"🎬 Activating {scene_name}...")
    result = await scenes.activate_scene(scene_name)
    
    if result["success"]:
        await status_msg.edit_text(f"✅ **{scene_name.title()} Activated!**", parse_mode="Markdown")
    else:
        await status_msg.edit_text(f"❌ Failed: {result.get('error','Unknown')}")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu interactions"""
    query = update.callback_query
    await query.answer()
    await menu.handle_callback(query, context)

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return
    status = await update.message.reply_text("🔍 Scanning network...")
    devices = await network_scanner.scan_network()
    await status.edit_text(f"✅ Scan Complete. Found {len(devices)} devices.")

async def discover_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS): return
    status = await update.message.reply_text("🔍 Discovering devices (may take time)...")
    res = await device_discovery.discover_all_devices()
    msg = f"**Discovery Report**\nNetwork: {len(res['network_devices'])}\nHA: {len(res['ha_entities'])}"
    await status.edit_text(msg, parse_mode="Markdown")

async def proactive_alert_callback(alert_data: Dict):
    """Proactive alerts"""
    try:
        for uid in ALLOWED_USERS:
            await app.bot.send_message(chat_id=uid, text=alert_data["message"])
    except Exception as e:
        logger.error(f"Alert error: {e}")

def main():
    """Start the bot"""
    global app, db, ha, llm, menu, scenes, doc_manager, network_scanner, monitor, device_discovery
    
    # Initialize Core
    db = Database()
    ha = HAController()
    llm = LLMHandler()
    scenes = SceneManager(ha)
    doc_manager = DocumentManager(db)
    network_scanner = NetworkScanner()
    device_discovery = DeviceDiscovery(network_scanner, ha)
    
    # Initialize Configured Bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Initialize Menu & Monitor
    menu = MenuHandler(app, ha, scenes)
    monitor = HomeMonitor(ha, db, context=app) # Using Correct Class Name

    # Add Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("devices", devices_command))
    app.add_handler(CommandHandler("scene", scene_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("discover", discover_command))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Message Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))
    
    # Start Monitor
    loop = asyncio.get_event_loop()
    loop.create_task(monitor.start())
    
    logger.info("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
