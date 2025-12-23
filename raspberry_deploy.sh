#!/bin/bash
#
# 🚀 FINAL DEPLOYMENT SCRIPT (v2.0)
# Run this on Raspberry Pi to pull changes and launch the new App
#

echo "🚀 Starting Deployment of HomeAI v2.0..."

# 1. Stop existing bot
echo "🛑 Stopping old bot..."
pkill -f homeai_bot.py || true

# 2. Go to directory and pull
cd ~/homeai-bot || exit
echo "📥 Pulling latest code..."
git pull

# 3. Apply DB Migrations
echo "💾 Checking Database..."
cat > migrate_db.py << 'EOF'
import sqlite3
try:
    conn = sqlite3.connect("data/homeai.db")
    c = conn.cursor()
    c.execute("ALTER TABLE users ADD COLUMN preferences TEXT")
    conn.commit()
    print("✅ Migrated DB")
except Exception as e:
    print(f"ℹ️ DB Migration note: {e}")
EOF
python3 migrate_db.py

# 4. START THE BOT
echo "✅ Deployment Complete!"
echo "👉 Starting HomeAI v2.0..."
python3 homeai_bot.py
