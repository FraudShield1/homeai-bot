#!/bin/bash
#
# Quick Deploy to Raspberry Pi
# Usage: ./deploy_to_pi.sh [pi_ip_or_hostname]
#

# Default to homeassistant.local if no argument
PI_HOST="${1:-homeassistant.local}"

echo "=========================================="
echo "🚀 Deploying HomeAI Bot to Raspberry Pi"
echo "=========================================="
echo ""
echo "Target: pi@$PI_HOST"
echo ""

# Check if we can reach the Pi
echo "📡 Testing connection..."
if ping -c 1 -W 2 "$PI_HOST" > /dev/null 2>&1; then
    echo "✅ Raspberry Pi is reachable"
else
    echo "❌ Cannot reach $PI_HOST"
    echo "Try: ./deploy_to_pi.sh 192.168.1.X"
    exit 1
fi
echo ""

# Transfer files
echo "📦 Transferring files..."
rsync -avz --progress \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'data/homeai.db' \
  --exclude 'logs/*.log' \
  --exclude '.git' \
  ./ pi@$PI_HOST:~/homeai-bot/

if [ $? -eq 0 ]; then
    echo "✅ Files transferred successfully"
else
    echo "❌ Transfer failed"
    exit 1
fi
echo ""

# Run installation on Pi
echo "🔧 Running installation on Raspberry Pi..."
ssh pi@$PI_HOST << 'ENDSSH'
cd ~/homeai-bot
chmod +x launch.sh
./launch.sh
ENDSSH

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "📱 Test your bot in Telegram:"
echo "  /start"
echo "  /status"
echo "  gm"
echo ""
echo "🔧 SSH to Pi:"
echo "  ssh pi@$PI_HOST"
echo ""
echo "📊 View logs:"
echo "  ssh pi@$PI_HOST 'tail -f ~/homeai-bot/logs/bot.log'"
echo ""
