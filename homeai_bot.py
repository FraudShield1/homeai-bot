"""
HomeAI Telegram Bot - Enhanced Main Application
Production-ready home automation assistant with LLM, scenes, documents, and monitoring
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
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
import json

# Import our modules
from ha_controller import HomeAssistantController
from database import Database
from llm_handler import LLMHandler
from scenes import SceneManager
from document_manager import DocumentManager
from nextcloud_manager import NextcloudManager
from monitor import ProactiveMonitor
from network_scanner import NetworkScanner, DeviceDiscovery
from utils import (
    setup_logging,
    is_user_authorized,
    rate_limiter,
    format_device_list,
    parse_natural_command,
)

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(uid.strip()) for uid in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if uid.strip()]
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

# Initialize components
ha = HomeAssistantController(HA_URL, HA_TOKEN)
db = Database(os.getenv("DATABASE_PATH", "data/homeai.db"))
llm = LLMHandler(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model=os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")
)
scenes = SceneManager(db, ha)
doc_manager = DocumentManager(db)
nextcloud = NextcloudManager()
network_scanner = NetworkScanner()
device_discovery = DeviceDiscovery(ha)
monitor = None  # Will be initialized after app creation


# Command Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message and setup"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        await update.message.reply_text("⛔ Unauthorized access. Your user ID has been logged.")
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        return

    user = update.effective_user
    
    # Add user to database
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_msg = f"""
🏠 **Welcome to HomeAI Assistant!**

Hi {user.first_name}! I'm your intelligent home automation assistant.

**Quick Commands:**
• `/status` - Home overview
• `/devices` - List all devices
• `/scene` - Activate scenes
• `/help` - Full command list

**Natural Language:**
Just tell me what you want:
• "turn on bedroom lights"
• "set temperature to 21"
• "gm" - Good morning routine
• "leaving" - Away mode

**Scenes Available:**
• `gm` or `/scene morning` - Morning routine
• `leaving` or `/scene away` - Away mode
• `/scene movie` - Movie mode
• `/scene night` - Night mode

I understand context, learn your preferences, and send proactive alerts!

Let's get started! Try `/status` to see your home.
    """
    
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")
    logger.info(f"User {user.id} ({user.first_name}) started bot")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show home status overview"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    await update.message.reply_text("🔍 Checking home status...")
    
    try:
        states = await ha.get_all_states()
        
        # Categorize devices
        lights_on = sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on")
        lights_total = sum(1 for s in states if s.get("entity_id", "").startswith("light."))
        
        switches_on = sum(1 for s in states if s.get("entity_id", "").startswith("switch.") and s.get("state") == "on")
        switches_total = sum(1 for s in states if s.get("entity_id", "").startswith("switch."))
        
        # Get climate info
        climate_devices = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        climate_info = ""
        if climate_devices:
            for device in climate_devices[:2]:
                name = device.get("attributes", {}).get("friendly_name", "Climate")
                temp = device.get("attributes", {}).get("current_temperature", "N/A")
                target = device.get("attributes", {}).get("temperature", "N/A")
                climate_info += f"\n• {name}: {temp}°C (target: {target}°C)"
        
        # Get security status
        locks = [s for s in states if s.get("entity_id", "").startswith("lock.")]
        locked_count = sum(1 for l in locks if l.get("state") == "locked")
        
        doors = [s for s in states if "door" in s.get("entity_id", "") and s.get("state") in ["on", "open"]]
        
        # Format time separately to avoid f-string backslash issue
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
            climate_info if climate_info else "\n• No climate devices found",
            locked_count, len(locks),
            len(doors),
            current_time
        )
        
        await update.message.reply_text(status_msg, parse_mode="Markdown")
        db.log_command(update.effective_user.id, "/status", "status", True)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(
            f"❌ Error getting home status. Is Home Assistant reachable?\nError: {str(e)}"
        )


async def scene_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate or list scenes"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    if not context.args:
        # List available scenes
        all_scenes = scenes.list_scenes()
        
        msg = "🎬 **Available Scenes:**\n\n"
        for scene in all_scenes:
            msg += f"• **{scene['name']}** - {scene['description']}\n"
        
        msg += "\n**Usage:** `/scene <name>`\n"
        msg += "**Quick commands:** `gm`, `leaving`, `movie mode`"
        
        # Add inline keyboard
        keyboard = [
            [InlineKeyboardButton("🌅 Morning", callback_data="scene_morning"),
             InlineKeyboardButton("👋 Away", callback_data="scene_away")],
            [InlineKeyboardButton("🎬 Movie", callback_data="scene_movie"),
             InlineKeyboardButton("🌙 Night", callback_data="scene_night")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    # Activate scene
    scene_name = " ".join(context.args).lower()
    await activate_scene_by_name(update, scene_name)


async def activate_scene_by_name(update, scene_name: str):
    """Helper to activate a scene"""
    status_msg = await update.message.reply_text(f"🎬 Activating {scene_name} scene...")
    
    try:
        result = await scenes.activate_scene(scene_name)
        
        if result["success"]:
            executed = len(result["actions_executed"])
            failed = len(result["actions_failed"])
            
            msg = f"✅ **{scene_name.title()} Scene Activated!**\n\n"
            msg += f"• {executed} actions executed\n"
            if failed > 0:
                msg += f"• {failed} actions failed\n"
            
            await status_msg.edit_text(msg, parse_mode="Markdown")
            db.log_command(update.effective_user.id, f"/scene {scene_name}", "scene", True)
        else:
            error = result.get("error", "Unknown error")
            await status_msg.edit_text(f"❌ Failed to activate scene: {error}")
            
    except Exception as e:
        logger.error(f"Error activating scene: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    status_msg = await update.message.reply_text("📸 Processing photo...")
    
    try:
        # Download photo
        photo = update.message.photo[-1]  # Get highest resolution
        file = await context.bot.get_file(photo.file_id)
        
        # Save to temp location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"photo_{timestamp}.jpg"
        local_path = f"data/uploads/{filename}"
        os.makedirs("data/uploads", exist_ok=True)
        await file.download_to_drive(local_path)
        
        # Get caption
        caption = update.message.caption or ""
        
        # Process photo
        result = await doc_manager.process_photo(local_path, update.effective_user.id, caption)
        
        if result["success"]:
            msg = "✅ **Photo Processed!**\n\n"
            
            if result["ocr_text"]:
                msg += f"**OCR Text:**\n{result['ocr_text'][:200]}...\n\n"
            
            if result["tags"]:
                msg += f"**Tags:** {', '.join(result['tags'])}\n\n"
            
            if result.get("metadata", {}).get("amount"):
                amount = result["metadata"]["amount"]
                msg += f"**Amount:** ${amount:.2f}\n"
            
            # Upload to Nextcloud if enabled
            if nextcloud.enabled:
                year_folder = datetime.now().strftime("%Y")
                folder = f"Documents/Receipts/{year_folder}"
                nextcloud.create_folder(folder)
                if nextcloud.upload_file(local_path, f"{folder}/{filename}"):
                    msg += "\n☁️ Uploaded to Nextcloud"
            
            await status_msg.edit_text(msg, parse_mode="Markdown")
            db.log_command(update.effective_user.id, "photo_upload", "document", True)
        else:
            await status_msg.edit_text(f"❌ Error processing photo: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    status_msg = await update.message.reply_text("📄 Processing document...")
    
    try:
        document = update.message.document
        file = await context.bot.get_file(document.file_id)
        
        # Save document
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = document.file_name or f"doc_{timestamp}.pdf"
        local_path = f"data/uploads/{filename}"
        os.makedirs("data/uploads", exist_ok=True)
        await file.download_to_drive(local_path)
        
        # Get caption
        caption = update.message.caption or ""
        
        # Process document
        result = await doc_manager.process_document(local_path, update.effective_user.id, caption)
        
        if result["success"]:
            msg = f"✅ **Document Saved!**\n\n**File:** {filename}\n"
            
            if result["tags"]:
                msg += f"**Tags:** {', '.join(result['tags'])}\n"
            
            # Upload to Nextcloud
            if nextcloud.enabled:
                year_folder = datetime.now().strftime("%Y")
                folder = f"Documents/{year_folder}"
                nextcloud.create_folder(folder)
                if nextcloud.upload_file(local_path, f"{folder}/{filename}"):
                    msg += "\n☁️ Uploaded to Nextcloud"
            
            await status_msg.edit_text(msg, parse_mode="Markdown")
            db.log_command(update.effective_user.id, "document_upload", "document", True)
        else:
            await status_msg.edit_text(f"❌ Error processing document: {result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def scan_network_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scan network for devices"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    status_msg = await update.message.reply_text("🔍 Scanning network...\nThis may take 1-2 minutes.")
    
    try:
        # Scan network
        devices = await network_scanner.scan_network()
        
        # Format report
        report = network_scanner.format_devices_report(devices)
        
        # Find Home Assistant
        ha_device = await network_scanner.find_home_assistant()
        
        if ha_device:
            report += f"\n✅ **Home Assistant Found!**\n"
            report += f"IP: {ha_device['ip']}\n"
            if ha_device.get('hostname'):
                report += f"Hostname: {ha_device['hostname']}\n"
            report += f"\nUse this in your .env file:\n"
            report += f"`HA_URL=http://{ha_device['ip']}:8123`"
        else:
            report += "\n⚠️ Home Assistant not found on network.\n"
            report += "Make sure it's running and accessible."
        
        await status_msg.edit_text(report, parse_mode="Markdown")
        db.log_command(update.effective_user.id, "/scan", "network_scan", True)
        
    except Exception as e:
        logger.error(f"Error scanning network: {e}")
        await status_msg.edit_text(f"❌ Error scanning network: {str(e)}")


async def discover_devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Discover and analyze all devices"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    status_msg = await update.message.reply_text(
        "🔍 Discovering devices...\n"
        "• Scanning network\n"
        "• Checking Home Assistant\n"
        "• Analyzing configuration\n\n"
        "This may take 2-3 minutes."
    )
    
    try:
        # Full discovery
        results = await device_discovery.discover_all_devices()
        
        # Format report
        msg = "**🏠 Device Discovery Report**\n\n"
        
        # Network devices
        msg += f"**Network Devices:** {len(results['network_devices'])}\n"
        msg += f"**HA Entities:** {len(results['ha_entities'])}\n\n"
        
        # Suggestions
        if results['suggestions']:
            msg += "**💡 Suggestions:**\n"
            for suggestion in results['suggestions']:
                msg += f"{suggestion}\n"
            msg += "\n"
        
        # Top devices
        msg += "**Top Network Devices:**\n"
        for device in results['network_devices'][:5]:
            dtype = device['device_type'].replace('_', ' ').title()
            msg += f"• {device['ip']} - {dtype}"
            if device.get('hostname'):
                msg += f" ({device['hostname']})"
            msg += "\n"
        
        if len(results['network_devices']) > 5:
            msg += f"... and {len(results['network_devices']) - 5} more\n"
        
        msg += "\nUse `/scan` for detailed network scan."
        
        await status_msg.edit_text(msg, parse_mode="Markdown")
        db.log_command(update.effective_user.id, "/discover", "device_discovery", True)
        
    except Exception as e:
        logger.error(f"Error discovering devices: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def search_documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search documents"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/search <query>` or `/search #tag`\n"
            "Example: `/search office receipts` or `/search #expenses`",
            parse_mode="Markdown"
        )
        return
    
    query = " ".join(context.args)
    
    # Extract tags
    tags = [word.lstrip('#') for word in context.args if word.startswith('#')]
    search_query = " ".join([word for word in context.args if not word.startswith('#')])
    
    results = doc_manager.search_documents(
        update.effective_user.id,
        query=search_query if search_query else None,
        tags=tags if tags else None
    )
    
    if results:
        msg = f"🔍 **Found {len(results)} document(s):**\n\n"
        for doc in results[:10]:
            msg += f"• **{doc['filename']}**\n"
            if doc.get('tags'):
                msg += f"  Tags: {', '.join(doc['tags'])}\n"
            if doc.get('metadata', {}).get('amount'):
                msg += f"  Amount: ${doc['metadata']['amount']:.2f}\n"
            msg += f"  Date: {doc['uploaded_at'][:10]}\n\n"
        
        if len(results) > 10:
            msg += f"... and {len(results) - 10} more"
        
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("No documents found matching your query.")


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Scene activation
    if data.startswith("scene_"):
        scene_name = data.replace("scene_", "")
        await query.edit_message_text(f"🎬 Activating {scene_name} scene...")
        
        result = await scenes.activate_scene(scene_name)
        
        if result["success"]:
            executed = len(result["actions_executed"])
            msg = f"✅ **{scene_name.title()} Scene Activated!**\n\n• {executed} actions executed"
            await query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await query.edit_message_text(f"❌ Failed: {result.get('error', 'Unknown')}")


async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle natural language commands with LLM fallback"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    message_text = update.message.text.lower().strip()
    
    # Quick scene shortcuts
    if message_text in ["gm", "good morning"]:
        await activate_scene_by_name(update, "morning")
        return
    elif message_text in ["leaving", "goodbye", "bye"]:
        await activate_scene_by_name(update, "away")
        return
    elif message_text in ["movie mode", "movie time"]:
        await activate_scene_by_name(update, "movie")
        return
    elif message_text in ["good night", "gn"]:
        await activate_scene_by_name(update, "night")
        return
    
    # Try rule-based parsing first
    command_info = parse_natural_command(message_text)
    
    # If rule-based fails, try LLM
    if not command_info and llm.enabled:
        states = await ha.get_all_states()
        context_data = {
            "total_lights": sum(1 for s in states if s.get("entity_id", "").startswith("light.")),
            "lights_on": sum(1 for s in states if s.get("entity_id", "").startswith("light.") and s.get("state") == "on")
        }
        command_info = await llm.analyze_command(message_text, context_data)
    
    if not command_info:
        await update.message.reply_text(
            "I'm not sure what you want me to do. Try:\n"
            "• 'turn on bedroom lights'\n"
            "• 'set temperature to 21'\n"
            "• 'gm' for morning routine\n"
            "Or use `/help` for all commands."
        )
        return
    
    # Execute the parsed command (reusing existing logic from original bot)
    action = command_info.get("action")
    domain = command_info.get("domain")
    target = command_info.get("target")
    value = command_info.get("value")
    
    try:
        states = await ha.get_all_states()
        
        if domain == "light":
            devices = [s for s in states if s.get("entity_id", "").startswith("light.")]
        elif domain == "climate":
            devices = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        elif domain == "lock":
            devices = [s for s in states if s.get("entity_id", "").startswith("lock.")]
        elif domain == "cover":
            devices = [s for s in states if s.get("entity_id", "").startswith("cover.")]
        else:
            devices = states
        
        # Filter by target
        if target and target != "all":
            devices = [d for d in devices 
                      if target in d.get("entity_id", "").lower()
                      or target in d.get("attributes", {}).get("friendly_name", "").lower()]
        
        if not devices:
            await update.message.reply_text(f"❌ No {domain} devices found matching '{target}'")
            return
        
        # Execute action
        success_count = 0
        
        if action in ["on", "off"]:
            for device in devices:
                service = f"turn_{action}"
                result = await ha.call_service(domain, service, device.get("entity_id"))
                if result:
                    success_count += 1
        
        elif action == "set_temperature" and value:
            for device in devices:
                result = await ha.call_service(
                    domain, 
                    "set_temperature", 
                    device.get("entity_id"),
                    {"temperature": float(value)}
                )
                if result:
                    success_count += 1
        
        # Send confirmation
        target_text = f" for {target}" if target and target != "all" else ""
        value_text = f" to {value}" if value else ""
        await update.message.reply_text(
            f"✅ {action.title()}{value_text} {success_count}/{len(devices)} {domain}(s){target_text}"
        )
        
        db.log_command(update.effective_user.id, message_text, "natural_language", True)
        
    except Exception as e:
        logger.error(f"Error executing natural language command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def proactive_alert_callback(alert_data: Dict):
    """Callback for proactive alerts from monitor"""
    try:
        # Send alert to all authorized users
        for user_id in ALLOWED_USERS:
            message = alert_data["message"]
            
            # Add action buttons if provided
            if alert_data.get("actions"):
                keyboard = []
                for action in alert_data["actions"]:
                    keyboard.append([InlineKeyboardButton(action["text"], callback_data=action["callback"])])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=reply_markup
                )
            else:
                await application.bot.send_message(chat_id=user_id, text=message)
                
    except Exception as e:
        logger.error(f"Error sending proactive alert: {e}")


# Keep all other command handlers from original file
async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all available devices"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    await update.message.reply_text("📋 Fetching device list...")
    
    try:
        states = await ha.get_all_states()
        
        # Group by domain
        devices_by_type = {}
        for state in states:
            entity_id = state.get("entity_id", "")
            domain = entity_id.split(".")[0]
            
            if domain not in ["light", "switch", "climate", "lock", "cover", "fan", "sensor"]:
                continue
            
            if domain not in devices_by_type:
                devices_by_type[domain] = []
            
            devices_by_type[domain].append({
                "id": entity_id,
                "name": state.get("attributes", {}).get("friendly_name", entity_id),
                "state": state.get("state", "unknown")
            })
        
        # Format message
        msg = "🏠 **Available Devices:**\n\n"
        
        emojis = {
            "light": "💡",
            "switch": "🔌",
            "climate": "🌡️",
            "lock": "🔒",
            "cover": "🪟",
            "fan": "💨",
            "sensor": "📊"
        }
        
        for domain, devices in sorted(devices_by_type.items()):
            emoji = emojis.get(domain, "•")
            msg += f"**{emoji} {domain.title()}s ({len(devices)}):**\n"
            for device in devices[:10]:
                state_icon = "✅" if device["state"] in ["on", "open", "unlocked"] else "⭕"
                msg += f"{state_icon} {device['name']} ({device['state']})\n"
            
            if len(devices) > 10:
                msg += f"... and {len(devices) - 10} more\n"
            msg += "\n"
        
        if not devices_by_type:
            msg = "No controllable devices found. Check your Home Assistant configuration."
        
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        await update.message.reply_text(f"❌ Error listing devices: {str(e)}")


async def lights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Control lights"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/lights on|off [room_name]`\n"
            "Examples:\n"
            "• `/lights on` - Turn all lights on\n"
            "• `/lights off bedroom` - Turn off bedroom lights",
            parse_mode="Markdown"
        )
        return
    
    action = context.args[0].lower()
    room = " ".join(context.args[1:]) if len(context.args) > 1 else None
    
    if action not in ["on", "off"]:
        await update.message.reply_text("Action must be 'on' or 'off'")
        return
    
    try:
        states = await ha.get_all_states()
        lights = [s for s in states if s.get("entity_id", "").startswith("light.")]
        
        if room:
            lights = [l for l in lights if room.lower() in l.get("entity_id", "").lower() 
                     or room.lower() in l.get("attributes", {}).get("friendly_name", "").lower()]
        
        if not lights:
            await update.message.reply_text(f"❌ No lights found{' in ' + room if room else ''}")
            return
        
        success_count = 0
        for light in lights:
            entity_id = light.get("entity_id")
            result = await ha.call_service("light", "turn_" + action, entity_id)
            if result:
                success_count += 1
        
        room_text = f" in {room}" if room else ""
        await update.message.reply_text(
            f"✅ Turned {action} {success_count}/{len(lights)} light(s){room_text}"
        )
        
    except Exception as e:
        logger.error(f"Error controlling lights: {e}")
        await update.message.reply_text(f"❌ Error controlling lights: {str(e)}")


async def climate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set temperature"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/climate <temperature> [room]`\n"
            "Examples:\n"
            "• `/climate 21` - Set all thermostats to 21°C\n"
            "• `/climate 19 bedroom` - Set bedroom to 19°C",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_temp = float(context.args[0])
        room = " ".join(context.args[1:]) if len(context.args) > 1 else None
        
        if target_temp < 10 or target_temp > 35:
            await update.message.reply_text("⚠️ Temperature must be between 10°C and 35°C")
            return
        
        states = await ha.get_all_states()
        climate_devices = [s for s in states if s.get("entity_id", "").startswith("climate.")]
        
        if room:
            climate_devices = [c for c in climate_devices 
                             if room.lower() in c.get("entity_id", "").lower()
                             or room.lower() in c.get("attributes", {}).get("friendly_name", "").lower()]
        
        if not climate_devices:
            await update.message.reply_text(f"❌ No climate devices found{' in ' + room if room else ''}")
            return
        
        success_count = 0
        for device in climate_devices:
            entity_id = device.get("entity_id")
            result = await ha.call_service(
                "climate", 
                "set_temperature", 
                entity_id,
                {"temperature": target_temp}
            )
            if result:
                success_count += 1
        
        room_text = f" in {room}" if room else ""
        await update.message.reply_text(
            f"✅ Set {success_count}/{len(climate_devices)} thermostat(s){room_text} to {target_temp}°C"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid temperature. Please provide a number.")
    except Exception as e:
        logger.error(f"Error setting climate: {e}")
        await update.message.reply_text(f"❌ Error setting climate: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message"""
    if not is_user_authorized(update.effective_user.id, ALLOWED_USERS):
        return

    help_text = """
🏠 **HomeAI Assistant - Command Reference**

**Basic Commands:**
• `/start` - Welcome & introduction
• `/status` - Home overview
• `/devices` - List all devices
• `/scene` - Activate scenes
• `/help` - This message

**Device Control:**
• `/lights on|off [room]` - Control lights
• `/climate <temp> [room]` - Set temperature

**Document Management:**
• Send photos - Auto OCR & save
• Send documents - Auto organize
• `/search <query>` - Search documents

**Network Discovery:**
• `/scan` - Scan WiFi for devices
• `/discover` - Full device analysis

**Scenes & Shortcuts:**
• `gm` - Good morning routine
• `leaving` - Away mode
• `movie mode` - Movie scene
• `gn` - Good night routine

**Natural Language:**
Just type what you want:
• "turn on bedroom lights"
• "set temperature to 21"
• "is the front door locked?"

**Features:**
✅ Intelligent command understanding
✅ Proactive alerts & monitoring
✅ Document OCR & organization
✅ Scene automation
✅ Pattern learning

Version 2.0 | Built with ❤️ and AI
    """
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. The issue has been logged.\n"
            "Try again or use `/help` for assistance."
        )


def main():
    """Start the bot"""
    global application, monitor
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env file")
        return
    
    if not ALLOWED_USERS:
        logger.error("TELEGRAM_ALLOWED_USERS not set in .env file")
        return
    
    if not HA_URL or not HA_TOKEN:
        logger.error("Home Assistant credentials not set in .env file")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Initialize proactive monitor
    monitor = ProactiveMonitor(db, ha, proactive_alert_callback)
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("devices", devices_command))
    application.add_handler(CommandHandler("lights", lights_command))
    application.add_handler(CommandHandler("climate", climate_command))
    application.add_handler(CommandHandler("scene", scene_command))
    application.add_handler(CommandHandler("search", search_documents_command))
    application.add_handler(CommandHandler("scan", scan_network_command))
    application.add_handler(CommandHandler("discover", discover_devices_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start proactive monitor
    async def start_monitor(app):
        await monitor.start()
    
    application.post_init = start_monitor
    
    # Start bot
    logger.info("🤖 HomeAI Bot starting...")
    logger.info(f"Authorized users: {ALLOWED_USERS}")
    logger.info(f"Home Assistant URL: {HA_URL}")
    logger.info(f"LLM enabled: {llm.enabled}")
    logger.info(f"Nextcloud enabled: {nextcloud.enabled}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
