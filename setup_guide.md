# 🏠 HomeAI - Complete Setup Guide

## Phase 1: Basic Bot (You Are Here!)

This guide will get your HomeAI bot running in **30 minutes**.

---

## Prerequisites

✅ **Hardware:**
- Raspberry Pi 5 (8GB) - You have this!
- MicroSD card (32GB+) or USB SSD (recommended)
- Power supply
- Network connection

✅ **Software:**
- Home Assistant running and accessible
- Telegram account

---

## Step 1: Prepare Raspberry Pi (5 minutes)

### SSH into Your Pi

```bash
ssh pi@raspberrypi.local
# Default password: raspberry (change this!)
```

### Update System

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 2: Get Telegram Credentials (5 minutes)

### A. Create Telegram Bot

1. Open Telegram
2. Search for **@BotFather**
3. Send: `/newbot`
4. Choose a name: `My Home AI`
5. Choose username: `yourhome_ai_bot` (must end in `_bot`)
6. **Copy the token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### B. Get Your User ID

1. Search for **@userinfobot** on Telegram
2. Start a chat
3. **Copy your user ID** (a number like: `123456789`)

---

## Step 3: Get Home Assistant Token (3 minutes)

1. Open your Home Assistant web interface
2. Click your **profile** (bottom left)
3. Scroll to **Long-Lived Access Tokens**
4. Click **Create Token**
5. Name it: `HomeAI Bot`
6. **Copy the token** (long string starting with `eyJ...`)

---

## Step 4: Install HomeAI (10 minutes)

### A. Download Installation Script

```bash
# SSH into your Pi, then:
cd ~
curl -O https://raw.githubusercontent.com/yourusername/homeai/main/install.sh
chmod +x install.sh
```

### B. Run Installation

```bash
./install.sh
```

This will:
- Install all dependencies
- Create project structure
- Setup firewall
- Configure Redis
- Create systemd service

### C. Add Bot Code

The installation created `~/homeai/` directory. Now add the code files:

```bash
cd ~/homeai
```

**Copy these 3 files into the directory:**
1. `bot.py` - Main bot code
2. `ha_controller.py` - Home Assistant interface
3. `utils.py` - Helper functions

You can either:
- **Option A:** Use `nano` editor:
  ```bash
  nano bot.py
  # Paste the code, press Ctrl+X, Y, Enter
  ```

- **Option B:** Use SFTP to upload files from your computer

---

## Step 5: Configure (5 minutes)

### Edit Configuration File

```bash
cd ~/homeai
nano .env
```

### Fill in Your Credentials

```bash
# Telegram Settings
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USERS=123456789

# Home Assistant
HA_URL=http://192.168.1.100:8123  # Your HA URL
HA_TOKEN=eyJ...your_token_here

# System Settings (leave as default)
LOG_LEVEL=INFO
ENABLE_CACHING=true
MAX_DAILY_API_CALLS=100
CACHE_TTL=300
```

**Press:** `Ctrl+X`, then `Y`, then `Enter` to save

---

## Step 6: Test the Bot (2 minutes)

### Manual Test Run

```bash
cd ~/homeai
./start.sh
```

You should see:
```
🤖 HomeAI Bot starting...
Authorized users: [123456789]
Home Assistant URL: http://192.168.1.100:8123
```

### Test in Telegram

1. Open Telegram
2. Search for your bot: `@yourhome_ai_bot`
3. Send: `/start`

You should get a welcome message! 🎉

### Try Some Commands

```
/status
/devices
turn on living room lights
what's the temperature?
```

### Stop Test Mode

Press `Ctrl+C` in the terminal

---

## Step 7: Enable Auto-Start

### Enable Systemd Service

```bash
sudo systemctl enable homeai
sudo systemctl start homeai
```

### Verify It's Running

```bash
sudo systemctl status homeai
```

Should show: `Active: active (running)`

### Check Logs

```bash
# Live log view
journalctl -u homeai -f

# Or check log file
tail -f ~/homeai/logs/homeai.log
```

---

## ✅ You're Done!

Your bot is now running 24/7 and will auto-start on reboot!

---

## Common Commands

### Start/Stop/Restart

```bash
sudo systemctl start homeai    # Start
sudo systemctl stop homeai     # Stop
sudo systemctl restart homeai  # Restart
sudo systemctl status homeai   # Check status
```

### View Logs

```bash
# Live logs
journalctl -u homeai -f

# Last 100 lines
journalctl -u homeai -n 100

# Application log file
tail -f ~/homeai/logs/homeai.log
```

### Update Bot

```bash
cd ~/homeai
# Edit files
nano bot.py

# Restart to apply changes
sudo systemctl restart homeai
```

### Backup

```bash
cd ~/homeai
./backup.sh
```

---

## Troubleshooting

### Bot Not Responding

**Check if it's running:**
```bash
sudo systemctl status homeai
```

**Check logs for errors:**
```bash
journalctl -u homeai -n 50
```

**Common issues:**
- Wrong bot token → Edit `.env`, restart
- Wrong user ID → Check with @userinfobot
- Home Assistant unreachable → Check HA_URL in `.env`

### "Unauthorized Access" Message

Your Telegram user ID is not in `TELEGRAM_ALLOWED_USERS`.

1. Message @userinfobot to get your ID
2. Edit `.env`:
   ```bash
   nano ~/homeai/.env
   ```
3. Add your user ID to `TELEGRAM_ALLOWED_USERS`
4. Restart:
   ```bash
   sudo systemctl restart homeai
   ```

### Home Assistant Connection Failed

**Test connection:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://192.168.1.100:8123/api/
```

Should return: `{"message": "API running."}`

**Fix:**
- Check HA is running
- Verify URL in `.env` (include http://)
- Verify token is correct
- Check firewall on HA machine

### Redis Connection Error

```bash
# Check Redis status
sudo systemctl status redis-server

# Restart if needed
sudo systemctl restart redis-server
```

---

## What You Can Do Now

### Basic Commands

✅ Control all lights and switches  
✅ Set temperature  
✅ Check device status  
✅ Natural language commands  
✅ Real-time home overview  

### Natural Language Examples

```
turn on bedroom lights
turn off all lights
set living room to 22 degrees
is the front door locked?
what's the temperature in bedroom?
open garage door
close all blinds
```

---

## Next Steps (Phase 2+)

Once you're comfortable with the basic bot, you can add:

### Phase 2: LLM Intelligence
- Smart command understanding
- Context-aware responses
- Energy optimization suggestions
- Conversational interaction

### Phase 3: Document Management
- Upload files via Telegram
- Auto-organize to Google Drive
- OCR for receipts
- Search documents

### Phase 4: Proactive Features
- Automatic notifications
- Scheduled actions
- Pattern learning
- Energy reports

### Phase 5: Advanced
- Voice commands
- Image analysis
- Security monitoring
- Multi-user support

---

## Security Recommendations

### Essential

1. **Change default Pi password:**
   ```bash
   passwd
   ```

2. **Limit SSH access:**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   # Use SSH keys instead
   ```

3. **Keep .env secret:**
   ```bash
   chmod 600 ~/homeai/.env
   # NEVER commit to Git!
   ```

4. **Regular updates:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### Recommended

1. **Use SSD instead of SD card** (longer life)
2. **Add UPS** (prevent corruption from power loss)
3. **Setup automatic backups** (run `./backup.sh` daily)
4. **Monitor logs** for suspicious activity
5. **Use strong passwords** everywhere

---

## Performance Tips

### Optimize for Pi 5

```bash
# Check temperature
vcgencmd measure_temp

# If >70°C, consider:
# - Better case/heatsink
# - Active cooling
```

### Reduce Logging (if disk fills up)

Edit `.env`:
```bash
LOG_LEVEL=WARNING  # Instead of INFO
```

### Clear Old Logs

```bash
# Manual cleanup
rm ~/homeai/logs/*.log.old

# Or setup log rotation (automatic)
sudo nano /etc/logrotate.d/homeai
```

---

## Getting Help

### Check Documentation
- README.md in project folder
- Logs: `~/homeai/logs/homeai.log`
- System logs: `journalctl -u homeai`

### Test Individual Components

**Home Assistant Connection:**
```bash
cd ~/homeai
source venv/bin/activate
python3 -c "
from ha_controller import HomeAssistantController
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    ha = HomeAssistantController(os.getenv('HA_URL'), os.getenv('HA_TOKEN'))
    connected = await ha.test_connection()
    print(f'Connected: {connected}')
    
asyncio.run(test())
"
```

---

## Maintenance Schedule

### Daily (Automatic)
- Logs rotate
- Service monitoring

### Weekly (5 minutes)
```bash
# Check status
sudo systemctl status homeai

# Review logs
tail -100 ~/homeai/logs/homeai.log
```

### Monthly (15 minutes)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Create backup
cd ~/homeai && ./backup.sh

# Check disk space
df -h

# Check temperature
vcgencmd measure_temp
```

---

## Congratulations! 🎉

You now have a production-ready home automation assistant!

**What you've built:**
- ✅ 24/7 Telegram bot
- ✅ Natural language control
- ✅ Auto-restart on failure
- ✅ Secure & monitored
- ✅ Ready for expansion

**Start using it and enjoy your smart home!**
