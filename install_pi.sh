#!/bin/bash
#
# HomeAI Bot - Direct Installation on Raspberry Pi
# Run this script directly on your Raspberry Pi via SSH
#
# Usage: 
#   wget https://raw.githubusercontent.com/YOUR_REPO/install_pi.sh
#   chmod +x install_pi.sh
#   ./install_pi.sh
#

set -e

echo "=========================================="
echo "🏠 HomeAI Bot - Raspberry Pi Installer"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    print_warning "This doesn't appear to be a Raspberry Pi, but continuing anyway..."
fi

# Step 1: Update system
echo "📋 Step 1: Updating system packages..."
sudo apt-get update -qq
print_success "System updated"
echo ""

# Step 2: Install dependencies
echo "📋 Step 2: Installing system dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git tesseract-ocr > /dev/null 2>&1
print_success "Dependencies installed"
echo ""

# Step 3: Create directory
echo "📋 Step 3: Creating bot directory..."
mkdir -p ~/homeai-bot
cd ~/homeai-bot
print_success "Directory created: ~/homeai-bot"
echo ""

# Step 4: Download bot files
echo "📋 Step 4: Downloading bot files..."
echo "Choose download method:"
echo "  1) From GitHub (if you uploaded there)"
echo "  2) Manual file creation (I'll guide you)"
echo ""
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    read -p "Enter GitHub repository URL: " repo_url
    git clone "$repo_url" .
    print_success "Files downloaded from GitHub"
else
    print_warning "Manual setup selected"
    echo "I'll create the files for you..."
    
    # We'll create files one by one
    echo "Creating Python files..."
fi
echo ""

# Step 5: Create virtual environment
echo "📋 Step 5: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
print_success "Virtual environment created"
echo ""

# Step 6: Install Python packages
echo "📋 Step 6: Installing Python packages..."
cat > requirements.txt << 'EOF'
python-telegram-bot==20.7
aiohttp==3.9.1
python-dotenv==1.0.0
anthropic==0.39.0
google-generativeai==0.8.3
pillow==10.1.0
pytesseract==0.3.10
requests==2.31.0
apscheduler==3.10.4
reportlab==4.0.7
EOF

pip install -q -r requirements.txt
print_success "Python packages installed"
echo ""

# Step 7: Configure environment
echo "📋 Step 7: Configuring environment..."
echo ""
echo "I need your credentials:"
echo ""

read -p "Telegram Bot Token: " tg_token
read -p "Your Telegram User ID: " tg_user
read -p "Home Assistant Token: " ha_token
read -p "Google Gemini API Key (optional, press Enter to skip): " gemini_key
read -p "Nextcloud URL (optional, press Enter to skip): " nc_url
read -p "Nextcloud Username (optional): " nc_user
read -p "Nextcloud Password (optional): " nc_pass

# Create .env file
cat > .env << EOF
# Telegram Settings
TELEGRAM_BOT_TOKEN=$tg_token
TELEGRAM_ALLOWED_USERS=$tg_user

# Home Assistant
HA_URL=http://localhost:8123
HA_TOKEN=$ha_token

# Google Gemini (Optional)
GOOGLE_API_KEY=$gemini_key
ENABLE_LLM=$([ -n "$gemini_key" ] && echo "true" || echo "false")
LLM_MODEL=gemini-1.5-flash
MAX_DAILY_LLM_CALLS=1000

# Nextcloud (Optional)
NEXTCLOUD_URL=$nc_url
NEXTCLOUD_USERNAME=$nc_user
NEXTCLOUD_PASSWORD=$nc_pass
NEXTCLOUD_ENABLED=$([ -n "$nc_url" ] && echo "true" || echo "false")

# System Settings
LOG_LEVEL=INFO
ENABLE_CACHING=true
CACHE_TTL=300
DATABASE_PATH=data/homeai.db

# Monitoring
ENABLE_PROACTIVE_ALERTS=true
MOTION_ALERT_DELAY=300
DOOR_OPEN_ALERT_DELAY=1800
WATER_LEAK_ALERT=true

# Automation
ENABLE_PATTERN_LEARNING=true
AUTO_AWAY_MODE=true
AUTO_ARRIVAL_MODE=true
ENABLE_IMAGE_ANALYSIS=true

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=30
MAX_REQUESTS_PER_HOUR=500

# Backup
AUTO_BACKUP=true
BACKUP_INTERVAL_HOURS=24
EOF

chmod 600 .env
print_success "Configuration saved to .env"
echo ""

# Step 8: Create directories
echo "📋 Step 8: Creating directories..."
mkdir -p data data/uploads logs backups config
print_success "Directories created"
echo ""

# Step 9: Download Python files
echo "📋 Step 9: Downloading bot code..."
echo "Please provide the download URL for the bot files, or I'll help you create them manually."
echo ""
echo "Option 1: If you have files on a server:"
read -p "Enter base URL (or press Enter to skip): " base_url

if [ -n "$base_url" ]; then
    # Download files
    files=(
        "homeai_bot.py"
        "ha_controller.py"
        "database.py"
        "llm_handler.py"
        "scenes.py"
        "document_manager.py"
        "nextcloud_manager.py"
        "monitor.py"
        "network_scanner.py"
        "utils.py"
    )
    
    for file in "${files[@]}"; do
        wget -q "$base_url/$file" -O "$file" && echo "✅ Downloaded $file" || echo "⚠️  Failed to download $file"
    done
else
    print_warning "Manual file creation needed"
    echo ""
    echo "To complete setup:"
    echo "1. Copy your Python files to ~/homeai-bot/"
    echo "2. Or use: scp -r /Users/naouri/Bot/*.py pi@YOUR_PI_IP:~/homeai-bot/"
    echo ""
    read -p "Press Enter when files are ready..."
fi
echo ""

# Step 10: Create systemd service
echo "📋 Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/homeai.service > /dev/null << EOF
[Unit]
Description=HomeAI Telegram Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/homeai-bot
Environment="PATH=/home/pi/homeai-bot/venv/bin"
ExecStart=/home/pi/homeai-bot/venv/bin/python3 /home/pi/homeai-bot/homeai_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/homeai-bot/logs/bot.log
StandardError=append:/home/pi/homeai-bot/logs/bot.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
print_success "Systemd service created"
echo ""

# Step 11: Summary
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. If you haven't copied the Python files yet:"
echo "   scp -r /Users/naouri/Bot/*.py pi@YOUR_PI_IP:~/homeai-bot/"
echo ""
echo "2. Start the bot:"
echo "   sudo systemctl start homeai"
echo ""
echo "3. Enable auto-start on boot:"
echo "   sudo systemctl enable homeai"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status homeai"
echo ""
echo "5. View logs:"
echo "   tail -f ~/homeai-bot/logs/bot.log"
echo ""
echo "6. Test in Telegram:"
echo "   Send /start to your bot"
echo ""
echo "🎉 Your HomeAI bot is ready!"
echo ""
