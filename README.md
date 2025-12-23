# HomeAI Bot - Complete Smart Home Assistant

A production-ready Telegram bot for Home Assistant with LLM intelligence, scene automation, document management, and proactive monitoring.

## 🌟 Features

- **🏠 Full Home Control** - Lights, climate, locks, covers, switches, and more
- **🤖 LLM Intelligence** - Claude-powered smart responses and energy analysis
- **🎬 Scene Automation** - Pre-configured scenes (morning, away, movie, night)
- **📄 Document Management** - OCR, auto-tagging, Nextcloud sync
- **🔔 Proactive Alerts** - Automatic notifications for doors, leaks, motion
- **💬 Natural Language** - Conversational command understanding
- **👥 Multi-User Ready** - Permission-based access control

## 📁 Project Structure

```
Bot/
├── homeai_bot.py           # Main bot application
├── ha_controller.py        # Home Assistant API client
├── database.py             # SQLite database manager
├── llm_handler.py          # Anthropic Claude integration
├── scenes.py               # Scene management
├── document_manager.py     # Document processing & OCR
├── nextcloud_manager.py    # Nextcloud integration
├── monitor.py              # Proactive monitoring
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
├── setup_guide.md          # Detailed setup instructions
└── quick_reference.md      # Command reference
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9+
- Home Assistant running and accessible
- Telegram account
- (Optional) Anthropic API key for LLM features
- (Optional) Nextcloud for document storage

### 2. Installation

```bash
# Clone or download the project
cd /Users/naouri/Bot

# Install dependencies
pip install -r requirements.txt

# For OCR support (optional)
brew install tesseract  # macOS
# or
sudo apt install tesseract-ocr  # Linux/Raspberry Pi
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required settings:**
- `TELEGRAM_BOT_TOKEN` - Get from @BotFather on Telegram
- `TELEGRAM_ALLOWED_USERS` - Your user ID from @userinfobot
- `HA_URL` - Your Home Assistant URL (e.g., http://192.168.1.100:8123)
- `HA_TOKEN` - Long-lived access token from HA Profile

**Optional settings:**
- `ANTHROPIC_API_KEY` - For LLM features
- `NEXTCLOUD_URL`, `NEXTCLOUD_USERNAME`, `NEXTCLOUD_PASSWORD` - For document sync

### 4. Run

```bash
# Test run
python homeai_bot.py

# Or use systemd service (see setup_guide.md)
sudo systemctl start homeai
```

### 5. Test in Telegram

1. Find your bot on Telegram
2. Send `/start`
3. Try commands like:
   - `/status` - Home overview
   - `gm` - Morning routine
   - `turn on bedroom lights`
   - Send a photo of a receipt

## 💡 Usage Examples

### Quick Shortcuts
```
gm              → Morning routine
leaving         → Away mode
movie mode      → Movie scene
gn              → Night mode
```

### Natural Language
```
turn on bedroom lights
set temperature to 21
is the front door locked?
it's too bright in here
```

### Commands
```
/status         → Home overview
/devices        → List all devices
/scene          → Activate scenes
/lights on      → Turn on all lights
/climate 21     → Set temperature
/search #tag    → Search documents
/help           → Full command list
```

### Document Management
```
1. Send photo of receipt
2. Add caption: "office expenses"
3. Bot will:
   - OCR the text
   - Extract amount and date
   - Tag as #office #expenses
   - Upload to Nextcloud
   - Make it searchable
```

## 🎬 Available Scenes

- **🌅 Morning** - Lights on (60%), temperature up, blinds open, coffee maker on
- **👋 Away** - All lights off, locks secured, temperature down, security armed
- **🎬 Movie** - Dim lights (30%), close blinds, turn on TV/soundbar
- **🌙 Night** - Secure home, lower temperature, dim bedroom light
- **🏠 Home** - Welcome settings, comfortable temperature, entrance lights

## 🔔 Proactive Alerts

The bot automatically monitors and alerts you for:

- 🚪 Doors/windows left open (30+ minutes)
- 👤 Motion detection
- 💧 Water leaks (critical)
- 🌡️ Temperature anomalies
- ⚠️ Devices going offline

## 🧠 LLM Features (Optional)

With Anthropic API key configured:

- **Smart Command Parsing** - Understands complex requests
- **Energy Analysis** - "optimize my energy usage" → detailed suggestions
- **Pattern Learning** - Detects routines and suggests automations
- **Weekly Reports** - Intelligence summaries of your home

## 📊 System Requirements

**Minimum:**
- Python 3.9+
- 100MB RAM
- 50MB disk space

**Recommended:**
- Python 3.11+
- 200MB RAM
- 500MB disk space (for documents)

**Tested on:**
- Raspberry Pi 5 (8GB)
- macOS
- Ubuntu/Debian Linux

## 🔧 Troubleshooting

### Bot doesn't respond
```bash
# Check if running
ps aux | grep homeai_bot

# Check logs
tail -f logs/homeai.log

# Verify credentials in .env
```

### Home Assistant connection fails
```bash
# Test HA connection
curl -H "Authorization: Bearer YOUR_TOKEN" http://YOUR_HA_URL/api/

# Should return: {"message": "API running."}
```

### OCR not working
```bash
# Install Tesseract
brew install tesseract  # macOS
sudo apt install tesseract-ocr  # Linux

# Verify installation
tesseract --version
```

## 📚 Documentation

- [`setup_guide.md`](file:///Users/naouri/Bot/setup_guide.md) - Detailed setup instructions
- [`quick_reference.md`](file:///Users/naouri/Bot/quick_reference.md) - Command reference
- [`.env.example`](file:///Users/naouri/Bot/.env.example) - Configuration options

## 🔐 Security

- User authentication via Telegram user IDs
- `.env` file for sensitive credentials (never commit!)
- Rate limiting to prevent abuse
- Secure token storage
- Optional permission levels for multi-user

## 🛣️ Roadmap

**Phase 3 (Next):**
- [ ] Network scanner for auto-discovery
- [ ] Auto-detect Home Assistant devices
- [ ] WiFi device scanning

**Phase 4 (Future):**
- [ ] Voice message processing
- [ ] Camera feed viewing
- [ ] Energy usage tracking
- [ ] Advanced pattern learning

## 📝 License

This project is for personal use. Modify as needed for your setup.

## 🤝 Contributing

This is a personal project, but feel free to fork and customize for your needs!

## 💬 Support

For issues or questions:
1. Check the logs: `logs/homeai.log`
2. Review `setup_guide.md`
3. Verify `.env` configuration

## 🎉 Credits

Built with:
- [python-telegram-bot](https://python-telegram-bot.org/)
- [Home Assistant](https://www.home-assistant.io/)
- [Anthropic Claude](https://www.anthropic.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Nextcloud](https://nextcloud.com/)

---

**Ready to make your home smarter!** 🏠✨

Start with `/start` in Telegram and explore the features!
