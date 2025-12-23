#!/bin/bash
# Quick test script for HomeAI Bot
# Tests basic functionality without running the full bot

echo "🧪 HomeAI Bot - Quick Test Script"
echo "=================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found!"
    exit 1
fi
echo "✅ Python OK"
echo ""

# Check if .env exists
echo "📋 Checking configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo "   ⚠️  IMPORTANT: Edit .env with your credentials before running the bot!"
else
    echo "✅ .env file exists"
fi
echo ""

# Check required Python packages
echo "📋 Checking dependencies..."
python3 -c "import telegram" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ python-telegram-bot not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "✅ python-telegram-bot installed"

python3 -c "import aiohttp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ aiohttp not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "✅ aiohttp installed"

python3 -c "from dotenv import load_dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ python-dotenv not installed"
    echo "   Run: pip install -r requirements.txt"
    exit 1
fi
echo "✅ python-dotenv installed"
echo ""

# Check optional dependencies
echo "📋 Checking optional dependencies..."

python3 -c "import anthropic" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ anthropic installed (LLM features available)"
else
    echo "⚠️  anthropic not installed (LLM features disabled)"
fi

python3 -c "from PIL import Image" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ PIL installed (image processing available)"
else
    echo "⚠️  PIL not installed (image processing disabled)"
fi

which tesseract >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ tesseract installed (OCR available)"
else
    echo "⚠️  tesseract not installed (OCR disabled)"
    echo "   Install: brew install tesseract (macOS) or sudo apt install tesseract-ocr (Linux)"
fi
echo ""

# Check file structure
echo "📋 Checking file structure..."
required_files=(
    "homeai_bot.py"
    "ha_controller.py"
    "database.py"
    "utils.py"
    "llm_handler.py"
    "scenes.py"
    "document_manager.py"
    "nextcloud_manager.py"
    "monitor.py"
    "requirements.txt"
)

all_files_present=true
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file missing!"
        all_files_present=false
    fi
done

if [ "$all_files_present" = false ]; then
    echo ""
    echo "❌ Some required files are missing!"
    exit 1
fi
echo ""

# Create necessary directories
echo "📋 Creating directories..."
mkdir -p data/uploads logs backups config
echo "✅ Directories created"
echo ""

# Test imports
echo "📋 Testing Python imports..."
python3 << 'EOF'
import sys
try:
    from ha_controller import HomeAssistantController
    print("✅ ha_controller imports OK")
except Exception as e:
    print(f"❌ ha_controller import failed: {e}")
    sys.exit(1)

try:
    from database import Database
    print("✅ database imports OK")
except Exception as e:
    print(f"❌ database import failed: {e}")
    sys.exit(1)

try:
    from llm_handler import LLMHandler
    print("✅ llm_handler imports OK")
except Exception as e:
    print(f"❌ llm_handler import failed: {e}")
    sys.exit(1)

try:
    from scenes import SceneManager
    print("✅ scenes imports OK")
except Exception as e:
    print(f"❌ scenes import failed: {e}")
    sys.exit(1)

try:
    from document_manager import DocumentManager
    print("✅ document_manager imports OK")
except Exception as e:
    print(f"❌ document_manager import failed: {e}")
    sys.exit(1)

try:
    from nextcloud_manager import NextcloudManager
    print("✅ nextcloud_manager imports OK")
except Exception as e:
    print(f"❌ nextcloud_manager import failed: {e}")
    sys.exit(1)

try:
    from monitor import ProactiveMonitor
    print("✅ monitor imports OK")
except Exception as e:
    print(f"❌ monitor import failed: {e}")
    sys.exit(1)

print("✅ All imports successful!")
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Import test failed!"
    exit 1
fi
echo ""

# Test database initialization
echo "📋 Testing database initialization..."
python3 << 'EOF'
from database import Database
import os

# Use test database
db = Database("data/test.db")
print("✅ Database initialized")

# Test adding a user
db.add_user(123456789, "test_user", "Test", "User")
print("✅ User added")

# Test getting user
user = db.get_user(123456789)
if user:
    print(f"✅ User retrieved: {user['username']}")
else:
    print("❌ Failed to retrieve user")

# Test preferences
db.set_preference(123456789, "test_key", "test_value")
value = db.get_preference(123456789, "test_key")
if value == "test_value":
    print("✅ Preferences working")
else:
    print("❌ Preferences failed")

# Test scenes
all_scenes = db.get_all_scenes()
print(f"✅ Found {len(all_scenes)} default scenes")

# Cleanup
os.remove("data/test.db")
print("✅ Database test complete")
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Database test failed!"
    exit 1
fi
echo ""

echo "=================================="
echo "✅ All tests passed!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
echo "   - TELEGRAM_ALLOWED_USERS (from @userinfobot)"
echo "   - HA_URL (your Home Assistant URL)"
echo "   - HA_TOKEN (from HA Profile → Tokens)"
echo ""
echo "2. Optional: Add API keys for advanced features:"
echo "   - ANTHROPIC_API_KEY (for LLM intelligence)"
echo "   - NEXTCLOUD_URL, USERNAME, PASSWORD (for document sync)"
echo ""
echo "3. Run the bot:"
echo "   python3 homeai_bot.py"
echo ""
echo "4. Test in Telegram:"
echo "   - Send /start to your bot"
echo "   - Try 'gm' for morning routine"
echo "   - Send /status for home overview"
echo ""
echo "Happy automating! 🏠✨"
