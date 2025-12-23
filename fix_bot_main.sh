#!/bin/bash
#
# 🚑 Emergency Fix for NameError and Main Loop
#
# This script rewrites the main() function in homeai_bot.py to use
# the CORRECT function names found in the file:
# - handle_text_message -> handle_natural_language
# - callback_handler -> callback_query_handler
# - ProactiveMonitor -> HomeMonitor
#

echo "🚑 Applying Final Main Logic Fix..."

cd ~/homeai-bot || exit

# 1. Ensure Import is correct (HomeMonitor)
sed -i 's/from monitor import ProactiveMonitor/from monitor import HomeMonitor/g' homeai_bot.py

# 2. Rewrite main() function using Python for safety
cat > fix_main_final.py << 'EOF'
import re

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # The Correct Main Function
    new_main = """def main():
    "Start the bot"
    global application, monitor
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    # 1. Initialize Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # 2. Initialize Monitor (using HomeMonitor and application context)
    # Ensure arguments match: ha, db, context
    try:
        monitor = HomeMonitor(ha, db, context=application)
    except NameError:
        # Fallback if HomeMonitor not imported, though sed should have fixed it
        logger.error("HomeMonitor class not found! Check imports.")
        return

    # 3. Add Command Handlers
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

    # 4. Add Message Handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # FIXED: Use handle_natural_language instead of handle_text_message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))
    
    # 5. Add Callback Handler
    # FIXED: Use callback_query_handler instead of callback_handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # 6. Add Error Handler
    application.add_error_handler(error_handler)
    
    # 7. Start Monitor on Post-Init
    async def start_monitor(app):
        if monitor:
            asyncio.create_task(monitor.start())
    
    application.post_init = start_monitor
    
    # 8. Run Bot
    logger.info("🤖 HomeAI Bot Started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
"""

    # Replace the existing main function
    # We look for 'def main():' and match until 'if __name__'
    pattern = r"def main\(\):.*?if __name__"
    
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_main + "\n\nif __name__", content, flags=re.DOTALL)
        with open('homeai_bot.py', 'w') as f:
            f.write(new_content)
        print("✅ Successfully replaced main() with CORRECT handlers")
    else:
        print("⚠️ Could not find main() block to replace")

except Exception as e:
    print(f"❌ Error: {e}")
EOF

python3 fix_main_final.py

echo "🔄 Restarting Bot..."
python3 homeai_bot.py
