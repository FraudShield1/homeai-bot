#!/bin/bash
#
# HomeAI Bot - Complete Installation & Launch Script
# Run this script to install and start your bot
#

set -e  # Exit on error

echo "=========================================="
echo "🏠 HomeAI Bot - Installation & Launch"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running on macOS or Linux
OS_TYPE=$(uname -s)
echo "Detected OS: $OS_TYPE"
echo ""

# Step 1: Check Python version
echo "📋 Step 1: Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
else
    print_error "Python 3 not found. Please install Python 3.9 or higher"
    exit 1
fi
echo ""

# Step 2: Check if .env exists
echo "📋 Step 2: Checking configuration..."
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    echo "Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "IMPORTANT: Edit .env with your credentials before continuing!"
        echo ""
        echo "Press Enter when you've edited .env, or Ctrl+C to exit and edit it manually"
        read
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_success ".env file exists"
fi
echo ""

# Step 3: Create directories
echo "📋 Step 3: Creating directories..."
mkdir -p data data/uploads logs backups config
print_success "Directories created"
echo ""

# Step 4: Install Python dependencies
echo "📋 Step 4: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "Installing packages (this may take a few minutes)..."
    pip3 install -q -r requirements.txt
    print_success "Python packages installed"
else
    print_error "requirements.txt not found"
    exit 1
fi
echo ""

# Step 5: Install Tesseract (optional)
echo "📋 Step 5: Checking Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    TESSERACT_VERSION=$(tesseract --version 2>&1 | head -n1)
    print_success "Tesseract installed: $TESSERACT_VERSION"
else
    print_warning "Tesseract not installed (OCR will be disabled)"
    echo "To install:"
    if [ "$OS_TYPE" = "Darwin" ]; then
        echo "  brew install tesseract"
    else
        echo "  sudo apt-get install tesseract-ocr"
    fi
fi
echo ""

# Step 6: Test imports
echo "📋 Step 6: Testing Python imports..."
python3 << 'EOF'
import sys
try:
    from ha_controller import HomeAssistantController
    from database import Database
    from llm_handler import LLMHandler
    from scenes import SceneManager
    from document_manager import DocumentManager
    from nextcloud_manager import NextcloudManager
    from monitor import ProactiveMonitor
    from network_scanner import NetworkScanner
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    print_error "Module import failed"
    exit 1
fi
echo ""

# Step 7: Initialize database
echo "📋 Step 7: Initializing database..."
python3 << 'EOF'
from database import Database
import os

db = Database("data/homeai.db")
print("✅ Database initialized")

# Check if default scenes exist
scenes = db.get_all_scenes()
print(f"✅ Found {len(scenes)} default scenes")
EOF

if [ $? -ne 0 ]; then
    print_error "Database initialization failed"
    exit 1
fi
echo ""

# Step 8: Verify configuration
echo "📋 Step 8: Verifying configuration..."
python3 << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

required = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "TELEGRAM_ALLOWED_USERS": os.getenv("TELEGRAM_ALLOWED_USERS"),
    "HA_URL": os.getenv("HA_URL"),
    "HA_TOKEN": os.getenv("HA_TOKEN"),
}

missing = []
for key, value in required.items():
    if not value or value == "your_" in value:
        missing.append(key)
        print(f"❌ {key} not configured")
    else:
        print(f"✅ {key} configured")

if missing:
    print(f"\n⚠️  Missing required configuration: {', '.join(missing)}")
    print("Please edit .env file with your credentials")
    exit(1)

# Check optional
if os.getenv("GOOGLE_API_KEY"):
    print("✅ Google Gemini API key configured")
if os.getenv("ANTHROPIC_API_KEY"):
    print("✅ Anthropic API key configured")
if os.getenv("NEXTCLOUD_ENABLED") == "true":
    print("✅ Nextcloud enabled")
EOF

if [ $? -ne 0 ]; then
    print_error "Configuration verification failed"
    print_warning "Edit .env file with your credentials and run this script again"
    exit 1
fi
echo ""

# Step 9: Stop any existing bot instance
echo "📋 Step 9: Checking for existing bot process..."
if pgrep -f "homeai_bot.py" > /dev/null; then
    print_warning "Stopping existing bot process..."
    pkill -f "homeai_bot.py"
    sleep 2
    print_success "Existing process stopped"
else
    print_success "No existing process found"
fi
echo ""

# Step 10: Start the bot
echo "📋 Step 10: Starting HomeAI Bot..."
echo ""
echo "=========================================="
echo "🚀 Launching bot..."
echo "=========================================="
echo ""

# Start bot in background
nohup python3 homeai_bot.py > logs/bot.log 2>&1 &
BOT_PID=$!

echo "Bot started with PID: $BOT_PID"
echo "Waiting for startup..."
sleep 5

# Check if bot is still running
if ps -p $BOT_PID > /dev/null; then
    print_success "Bot is running!"
    echo ""
    echo "=========================================="
    echo "✅ Installation Complete!"
    echo "=========================================="
    echo ""
    echo "📱 Next Steps:"
    echo "1. Open Telegram"
    echo "2. Find your bot"
    echo "3. Send: /start"
    echo "4. Try: gm (morning routine)"
    echo ""
    echo "📊 Bot Status:"
    echo "  PID: $BOT_PID"
    echo "  Logs: logs/bot.log"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  View logs:    tail -f logs/bot.log"
    echo "  Stop bot:     pkill -f homeai_bot.py"
    echo "  Restart bot:  ./launch.sh"
    echo ""
    echo "🎉 Your HomeAI bot is ready!"
    echo ""
else
    print_error "Bot failed to start"
    echo ""
    echo "Check logs for errors:"
    echo "  tail -50 logs/bot.log"
    echo ""
    exit 1
fi
