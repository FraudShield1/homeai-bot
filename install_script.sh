#!/bin/bash
# HomeAI Installation Script
# Run this on your Raspberry Pi 5

set -e  # Exit on error

echo "🏠 HomeAI Installation Script"
echo "=============================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Update system
echo ""
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt install -y \
    git \
    redis-server \
    sqlite3 \
    nginx \
    ufw \
    curl \
    wget

# Setup firewall
echo ""
echo "🔒 Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "✅ Firewall configured"

# Create project directory
echo ""
echo "📁 Setting up project directory..."
PROJECT_DIR="$HOME/homeai"

if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Directory $PROJECT_DIR already exists"
    read -p "Remove and reinstall? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$PROJECT_DIR"
    else
        echo "Installation cancelled"
        exit 1
    fi
fi

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create subdirectories
mkdir -p logs backups config data

# Create virtual environment
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo ""
echo "📦 Installing Python dependencies..."
cat > requirements.txt << 'EOF'
python-telegram-bot==20.7
aiohttp==3.9.1
python-dotenv==1.0.0
requests==2.31.0
redis==5.0.1
EOF

pip install --upgrade pip
pip install -r requirements.txt

# Create .env template
echo ""
echo "⚙️  Creating configuration template..."
cat > .env.template << 'EOF'
# Telegram Settings
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=

# Home Assistant
HA_URL=http://192.168.1.100:8123
HA_TOKEN=

# LLM (Optional)
ANTHROPIC_API_KEY=
LLM_MODEL=claude-haiku-4.5-20251001

# System
LOG_LEVEL=INFO
ENABLE_CACHING=true
MAX_DAILY_API_CALLS=100
CACHE_TTL=300
EOF

cp .env.template .env
chmod 600 .env

echo "✅ Configuration template created at $PROJECT_DIR/.env"

# Setup Redis
echo ""
echo "🔴 Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server
echo "✅ Redis started"

# Create systemd service
echo ""
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/homeai.service > /dev/null << EOF
[Unit]
Description=HomeAI Telegram Bot
After=network.target redis-server.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/bot.py
Restart=on-failure
RestartSec=30
StandardOutput=append:$PROJECT_DIR/logs/homeai.log
StandardError=append:$PROJECT_DIR/logs/homeai_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service created"

# Create helper scripts
echo ""
echo "📝 Creating helper scripts..."

# Start script
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python bot.py
EOF
chmod +x start.sh

# Stop script
cat > stop.sh << 'EOF'
#!/bin/bash
sudo systemctl stop homeai
echo "HomeAI stopped"
EOF
chmod +x stop.sh

# Status script
cat > status.sh << 'EOF'
#!/bin/bash
sudo systemctl status homeai
EOF
chmod +x status.sh

# Update script
cat > update.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "Updating HomeAI..."
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart homeai
echo "✅ Update complete"
EOF
chmod +x update.sh

# Backup script
cat > backup.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/homeai_backup_$DATE.tar.gz"

echo "Creating backup..."
tar -czf "$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='logs/*.log' \
    --exclude='backups/*.tar.gz' \
    .

echo "✅ Backup created: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
EOF
chmod +x backup.sh

echo "✅ Helper scripts created"

# Create README
cat > README.md << 'EOF'
# HomeAI - Telegram Bot for Home Assistant

## Quick Start

1. Edit `.env` file with your credentials:
   ```bash
   nano .env
   ```

2. Add your bot files (bot.py, ha_controller.py, utils.py)

3. Test the bot:
   ```bash
   ./start.sh
   ```

4. Enable auto-start:
   ```bash
   sudo systemctl enable homeai
   sudo systemctl start homeai
   ```

## Commands

- `./start.sh` - Start bot manually (for testing)
- `./stop.sh` - Stop the bot
- `./status.sh` - Check bot status
- `./update.sh` - Update and restart bot
- `./backup.sh` - Create backup

## Systemd Service

- Start: `sudo systemctl start homeai`
- Stop: `sudo systemctl stop homeai`
- Restart: `sudo systemctl restart homeai`
- Status: `sudo systemctl status homeai`
- Logs: `journalctl -u homeai -f`

## Logs

- Application: `logs/homeai.log`
- Errors: `logs/homeai_error.log`
- System: `journalctl -u homeai`

## Directory Structure

```
~/homeai/
├── bot.py              # Main bot code
├── ha_controller.py    # Home Assistant interface
├── utils.py           # Helper functions
├── .env               # Configuration (KEEP SECRET!)
├── requirements.txt   # Python dependencies
├── logs/              # Log files
├── backups/           # Backup files
└── data/              # Application data
```
EOF

echo ""
echo "✅ Installation complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Get Telegram Bot Token:"
echo "   - Open Telegram, message @BotFather"
echo "   - Send: /newbot"
echo "   - Follow instructions"
echo ""
echo "2. Get your Telegram User ID:"
echo "   - Message @userinfobot"
echo "   - Copy the number"
echo ""
echo "3. Get Home Assistant Token:"
echo "   - Open Home Assistant"
echo "   - Profile → Long-Lived Access Tokens"
echo "   - Create token"
echo ""
echo "4. Edit configuration:"
echo "   cd $PROJECT_DIR"
echo "   nano .env"
echo ""
echo "5. Add the bot code files to: $PROJECT_DIR"
echo "   - bot.py"
echo "   - ha_controller.py"
echo "   - utils.py"
echo ""
echo "6. Test the bot:"
echo "   cd $PROJECT_DIR"
echo "   ./start.sh"
echo ""
echo "7. Enable auto-start:"
echo "   sudo systemctl enable homeai"
echo "   sudo systemctl start homeai"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installation directory: $PROJECT_DIR"
echo ""
