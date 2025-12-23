#!/usr/bin/env python3
"""
Setup Wizard for HomeAI Bot
Interactive configuration assistant
"""

import os
import sys
from pathlib import Path


def print_header():
    """Print welcome header"""
    print("\n" + "="*60)
    print("🏠 HomeAI Bot - Setup Wizard")
    print("="*60 + "\n")


def check_python_version():
    """Check Python version"""
    print("📋 Checking Python version...")
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_dependencies():
    """Check if dependencies are installed"""
    print("\n📋 Checking dependencies...")
    
    required = [
        ("telegram", "python-telegram-bot"),
        ("aiohttp", "aiohttp"),
        ("dotenv", "python-dotenv"),
    ]
    
    missing = []
    for module, package in required:
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing dependencies. Install with:")
        print(f"   pip install -r requirements.txt")
        return False
    
    return True


def get_telegram_credentials():
    """Get Telegram credentials from user"""
    print("\n📱 Telegram Configuration")
    print("-" * 40)
    
    print("\n1. Create a bot:")
    print("   • Open Telegram and message @BotFather")
    print("   • Send: /newbot")
    print("   • Follow instructions")
    print("   • Copy the bot token")
    
    token = input("\nEnter your bot token: ").strip()
    
    print("\n2. Get your user ID:")
    print("   • Message @userinfobot on Telegram")
    print("   • Copy your user ID (number)")
    
    user_id = input("\nEnter your user ID: ").strip()
    
    return token, user_id


def get_home_assistant_credentials():
    """Get Home Assistant credentials"""
    print("\n🏠 Home Assistant Configuration")
    print("-" * 40)
    
    print("\nOption 1: Auto-detect (recommended)")
    print("Option 2: Manual entry")
    
    choice = input("\nChoose option (1/2): ").strip()
    
    if choice == "1":
        print("\n🔍 Scanning network for Home Assistant...")
        try:
            # Import scanner
            from network_scanner import NetworkScanner
            import asyncio
            
            scanner = NetworkScanner()
            ha_device = asyncio.run(scanner.find_home_assistant())
            
            if ha_device:
                print(f"\n✅ Found Home Assistant!")
                print(f"   IP: {ha_device['ip']}")
                if ha_device.get('hostname'):
                    print(f"   Hostname: {ha_device['hostname']}")
                
                ha_url = f"http://{ha_device['ip']}:8123"
                use_auto = input(f"\nUse {ha_url}? (y/n): ").strip().lower()
                
                if use_auto == 'y':
                    pass
                else:
                    ha_url = input("Enter Home Assistant URL: ").strip()
            else:
                print("\n⚠️  Home Assistant not found on network")
                ha_url = input("Enter Home Assistant URL manually: ").strip()
        except Exception as e:
            print(f"\n⚠️  Auto-detection failed: {e}")
            ha_url = input("Enter Home Assistant URL manually: ").strip()
    else:
        ha_url = input("\nEnter Home Assistant URL (e.g., http://192.168.1.100:8123): ").strip()
    
    print("\n3. Create a Long-Lived Access Token:")
    print("   • Open Home Assistant")
    print("   • Click your profile (bottom left)")
    print("   • Scroll to 'Long-Lived Access Tokens'")
    print("   • Click 'Create Token'")
    print("   • Name it 'HomeAI Bot'")
    print("   • Copy the token")
    
    ha_token = input("\nEnter Home Assistant token: ").strip()
    
    return ha_url, ha_token


def get_optional_features():
    """Ask about optional features"""
    print("\n⚙️  Optional Features")
    print("-" * 40)
    
    features = {}
    
    # LLM
    print("\n🤖 LLM Intelligence (Anthropic Claude)")
    print("   Enables: Smart responses, energy analysis, pattern learning")
    enable_llm = input("   Enable? (y/n): ").strip().lower() == 'y'
    
    if enable_llm:
        print("\n   Get API key from: https://console.anthropic.com")
        features['anthropic_key'] = input("   Enter Anthropic API key: ").strip()
    
    # Nextcloud
    print("\n☁️  Nextcloud Integration")
    print("   Enables: Document sync, cloud storage")
    enable_nextcloud = input("   Enable? (y/n): ").strip().lower() == 'y'
    
    if enable_nextcloud:
        features['nextcloud_url'] = input("   Nextcloud URL: ").strip()
        features['nextcloud_user'] = input("   Username: ").strip()
        features['nextcloud_pass'] = input("   App Password: ").strip()
    
    return features


def create_env_file(config):
    """Create .env file from configuration"""
    print("\n📝 Creating .env file...")
    
    env_content = f"""# Telegram Settings
TELEGRAM_BOT_TOKEN={config['telegram_token']}
TELEGRAM_ALLOWED_USERS={config['telegram_user_id']}

# Home Assistant
HA_URL={config['ha_url']}
HA_TOKEN={config['ha_token']}

# LLM Integration (Optional)
ANTHROPIC_API_KEY={config.get('anthropic_key', '')}
LLM_MODEL=claude-3-5-haiku-20241022
ENABLE_LLM={'true' if config.get('anthropic_key') else 'false'}
MAX_DAILY_LLM_CALLS=100

# Nextcloud Integration (Optional)
NEXTCLOUD_URL={config.get('nextcloud_url', '')}
NEXTCLOUD_USERNAME={config.get('nextcloud_user', '')}
NEXTCLOUD_PASSWORD={config.get('nextcloud_pass', '')}
NEXTCLOUD_ENABLED={'true' if config.get('nextcloud_url') else 'false'}

# System Settings
LOG_LEVEL=INFO
ENABLE_CACHING=true
CACHE_TTL=300

# Database
DATABASE_PATH=data/homeai.db

# Monitoring & Alerts
ENABLE_PROACTIVE_ALERTS=true
MOTION_ALERT_DELAY=300
DOOR_OPEN_ALERT_DELAY=1800
WATER_LEAK_ALERT=true

# Automation
ENABLE_PATTERN_LEARNING=true
AUTO_AWAY_MODE=true
AUTO_ARRIVAL_MODE=true

# Rate Limiting
MAX_REQUESTS_PER_MINUTE=30
MAX_REQUESTS_PER_HOUR=500
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created")


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    dirs = ['data', 'data/uploads', 'logs', 'backups', 'config']
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✅ {d}/")


def print_next_steps():
    """Print next steps"""
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    
    print("\n📝 Next Steps:\n")
    print("1. Start the bot:")
    print("   python3 homeai_bot.py")
    print()
    print("2. Test in Telegram:")
    print("   • Find your bot")
    print("   • Send: /start")
    print("   • Try: gm (morning routine)")
    print("   • Send: /status")
    print()
    print("3. Explore features:")
    print("   • /scan - Scan network for devices")
    print("   • /scene - Activate scenes")
    print("   • Send photos - Auto OCR & save")
    print("   • /help - Full command list")
    print()
    print("📚 Documentation:")
    print("   • README.md - Full documentation")
    print("   • QUICKSTART.md - Quick start guide")
    print()
    print("Happy automating! 🏠✨\n")


def main():
    """Main setup wizard"""
    print_header()
    
    # Check requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # Gather configuration
    config = {}
    
    # Telegram
    config['telegram_token'], config['telegram_user_id'] = get_telegram_credentials()
    
    # Home Assistant
    config['ha_url'], config['ha_token'] = get_home_assistant_credentials()
    
    # Optional features
    optional = get_optional_features()
    config.update(optional)
    
    # Create files
    create_env_file(config)
    create_directories()
    
    # Done!
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
