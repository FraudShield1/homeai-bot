#!/bin/bash
#
# Fix App Definition in Main
# 
# The issue is likely that 'app' is not defined before it is used in monitor init.
# We will rewrite the main() function to be strictly correct.
#

echo "🔧 Fixing Main Loop..."

cd ~/homeai-bot

cat > fix_main.py << 'EOF'
import sys
import re

try:
    with open('homeai_bot.py', 'r') as f:
        content = f.read()

    # We will replace the entire main() function to ensure correct order
    # This is safer than regex patching specific lines now
    
    new_main = """def main():
    if not TELEGRAM_TOKEN:
        logger.error("No token found")
        return

    # 1. Initialize App FIRST
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. Add Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("menu", lambda u,c: menu.send_main_menu(u)))
    
    # Text handler (Menu Taps + Natural Language)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 3. Start Monitor (NOW app exists)
    global monitor
    monitor = HomeMonitor(ha, db, context=app)
    # Schedule monitor start
    loop = asyncio.get_event_loop()
    loop.create_task(monitor.start())
    
    logger.info("🤖 HomeAI Bot v2.0 Started")
    app.run_polling()
"""

    # We need to find where main starts and ends
    # It probably starts with "def main():" and goes to "if __name__"
    
    # Regex to find the main block
    # Match from 'def main():' until 'if __name__'
    pattern = r"def main\(\):.*?if __name__"
    
    # Check if we can find it
    if re.search(pattern, content, re.DOTALL):
         # Replace
         content = re.sub(pattern, new_main + "\n\nif __name__", content, flags=re.DOTALL)
         with open('homeai_bot.py', 'w') as f:
             f.write(content)
         print("✅ Replaced main() with correct order")
    else:
         print("⚠️ Could not locate main function block")

except Exception as e:
    print(e)
EOF

python3 fix_main.py

echo "Restarting..."
python3 homeai_bot.py
