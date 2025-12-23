# 🏠 HomeAI Quick Reference

## Telegram Bot Commands

### Basic Commands
| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message | `/start` |
| `/status` | Home overview | `/status` |
| `/devices` | List all devices | `/devices` |
| `/help` | Show help | `/help` |

### Device Control
| Command | Description | Example |
|---------|-------------|---------|
| `/lights on\|off [room]` | Control lights | `/lights on bedroom` |
| `/climate <temp> [room]` | Set temperature | `/climate 21 living room` |

### Natural Language (Just type these)
```
turn on bedroom lights
turn off all lights
set temperature to 21
what's the temperature?
is the front door locked?
open garage door
close living room blinds
```

---

## Raspberry Pi Commands

### Service Control
```bash
# Start bot
sudo systemctl start homeai

# Stop bot
sudo systemctl stop homeai

# Restart bot
sudo systemctl restart homeai

# Check status
sudo systemctl status homeai

# Enable auto-start
sudo systemctl enable homeai

# Disable auto-start
sudo systemctl disable homeai
```

### View Logs
```bash
# Live tail (follow)
journalctl -u homeai -f

# Last 100 lines
journalctl -u homeai -n 100

# Today's logs
journalctl -u homeai --since today

# Application log file
tail -f ~/homeai/logs/homeai.log

# Error log file
tail -f ~/homeai/logs/homeai_error.log
```

### Helper Scripts
```bash
cd ~/homeai

# Manual start (testing)
./start.sh

# Stop service
./stop.sh

# Check status
./status.sh

# Create backup
./backup.sh
```

---

## Configuration

### Edit Settings
```bash
nano ~/homeai/.env
```

### Important Settings
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_ALLOWED_USERS=123456789,987654321

# Home Assistant
HA_URL=http://192.168.1.100:8123
HA_TOKEN=your_token

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Caching
ENABLE_CACHING=true
CACHE_TTL=300  # seconds
```

### Apply Changes
```bash
sudo systemctl restart homeai
```

---

## Troubleshooting

### Bot Not Responding
```bash
# 1. Check if running
sudo systemctl status homeai

# 2. Check logs
journalctl -u homeai -n 50

# 3. Restart
sudo systemctl restart homeai
```

### Connection Issues
```bash
# Test Home Assistant
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://YOUR_HA_URL/api/

# Test Redis
redis-cli ping
# Should return: PONG

# Test network
ping 192.168.1.100  # Your HA IP
```

### Permission Issues
```bash
# Fix file permissions
cd ~/homeai
chmod 600 .env
chmod +x *.sh

# Fix log directory
sudo chown -R $USER:$USER logs/
```

---

## Maintenance Tasks

### Daily (Automatic)
- Service monitoring
- Log rotation

### Weekly
```bash
# Check status
sudo systemctl status homeai

# Review logs
tail -100 ~/homeai/logs/homeai.log

# Check disk space
df -h
```

### Monthly
```bash
# System update
sudo apt update && sudo apt upgrade -y

# Create backup
cd ~/homeai && ./backup.sh

# Check Pi temperature
vcgencmd measure_temp

# Clean old logs
sudo journalctl --vacuum-time=30d
```

---

## File Locations

```
~/homeai/
├── bot.py              # Main bot code
├── ha_controller.py    # HA interface
├── utils.py           # Utilities
├── .env               # Config (SECRET!)
├── requirements.txt   # Dependencies
├── logs/              # Log files
│   ├── homeai.log
│   └── homeai_error.log
├── backups/           # Backup files
└── data/              # App data
```

---

## Common Issues & Fixes

### "Unauthorized access"
**Problem:** Your user ID not in allowed list  
**Fix:**
```bash
# Get your ID from @userinfobot
# Add to .env
nano ~/homeai/.env
# Add: TELEGRAM_ALLOWED_USERS=123456789
sudo systemctl restart homeai
```

### "Connection to HA failed"
**Problem:** Can't reach Home Assistant  
**Fix:**
```bash
# Verify HA is running
# Check HA_URL in .env
nano ~/homeai/.env
# Verify token is correct
```

### "Service failed to start"
**Problem:** Error in configuration  
**Fix:**
```bash
# Check logs for specific error
journalctl -u homeai -n 50
# Common: missing dependencies
cd ~/homeai
source venv/bin/activate
pip install -r requirements.txt
```

### Redis connection error
**Problem:** Redis not running  
**Fix:**
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

---

## Security Checklist

- [ ] Changed default Pi password
- [ ] `.env` file permissions set to 600
- [ ] Firewall enabled (ufw)
- [ ] Only authorized Telegram users
- [ ] Home Assistant token secured
- [ ] Regular backups enabled
- [ ] SSH keys configured (no password auth)
- [ ] System kept updated

---

## Performance Monitoring

### Check System Resources
```bash
# CPU usage
top

# Memory usage
free -h

# Disk usage
df -h

# Temperature
vcgencmd measure_temp

# All at once
htop
```

### Bot Statistics
```bash
# Count commands processed today
grep "$(date +%Y-%m-%d)" ~/homeai/logs/homeai.log | grep -c "SUCCESS"

# Recent errors
grep ERROR ~/homeai/logs/homeai_error.log | tail -20

# Active connections
sudo ss -tulpn | grep python
```

---

## Backup & Restore

### Create Backup
```bash
cd ~/homeai
./backup.sh
```

### List Backups
```bash
ls -lh ~/homeai/backups/
```

### Restore from Backup
```bash
# Stop service
sudo systemctl stop homeai

# Extract backup
cd ~/homeai
tar -xzf backups/homeai_backup_YYYYMMDD_HHMMSS.tar.gz

# Restart service
sudo systemctl start homeai
```

### Auto-Backup (Daily)
```bash
# Edit crontab
crontab -e

# Add line:
0 3 * * * /home/pi/homeai/backup.sh
```

---

## Network Information

### Find Pi's IP Address
```bash
hostname -I
```

### Check Connectivity
```bash
# To Home Assistant
ping -c 4 192.168.1.100

# Internet connectivity
ping -c 4 8.8.8.8

# DNS resolution
ping -c 4 google.com
```

---

## Update Instructions

### Update Bot Code
```bash
cd ~/homeai
# Edit files
nano bot.py
# Restart
sudo systemctl restart homeai
```

### Update Dependencies
```bash
cd ~/homeai
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
sudo systemctl restart homeai
```

### Update System
```bash
sudo apt update
sudo apt upgrade -y
sudo reboot  # If kernel updated
```

---

## Emergency Commands

### Force Stop
```bash
sudo systemctl stop homeai
sudo killall python3  # If service won't stop
```

### Reset to Defaults
```bash
cd ~/homeai
cp .env.template .env
nano .env  # Re-enter credentials
sudo systemctl restart homeai
```

### Full Reinstall
```bash
# Backup data first!
cd ~/homeai && ./backup.sh

# Remove and reinstall
cd ~
rm -rf homeai
./install.sh
# Then restore from backup
```

---

## Getting Help

### Check Logs First
```bash
# Application logs
tail -100 ~/homeai/logs/homeai.log

# System logs
journalctl -u homeai -n 100

# Error logs only
journalctl -u homeai -p err
```

### Test Components

**Home Assistant:**
```bash
cd ~/homeai && source venv/bin/activate
python3 -c "
from ha_controller import HomeAssistantController
import asyncio, os
from dotenv import load_dotenv
load_dotenv()
async def test():
    ha = HomeAssistantController(os.getenv('HA_URL'), os.getenv('HA_TOKEN'))
    print('Connected:', await ha.test_connection())
asyncio.run(test())
"
```

**Telegram:**
```bash
# Send test message to your bot
# Check if it appears in logs:
journalctl -u homeai -f
```

---

## Useful Pi Commands

```bash
# System info
uname -a

# Pi model
cat /proc/device-tree/model

# Temperature
vcgencmd measure_temp

# Disk usage
df -h

# Memory usage
free -h

# Running processes
ps aux | grep python

# Uptime
uptime
```

---

## Quick Start Checklist

- [ ] Pi updated: `sudo apt update && sudo apt upgrade -y`
- [ ] Installation run: `./install.sh`
- [ ] Bot files copied: `bot.py`, `ha_controller.py`, `utils.py`
- [ ] `.env` configured with all credentials
- [ ] Telegram bot created (@BotFather)
- [ ] User ID obtained (@userinfobot)
- [ ] HA token created
- [ ] Bot tested: `./start.sh`
- [ ] Service enabled: `sudo systemctl enable homeai`
- [ ] Service started: `sudo systemctl start homeai`
- [ ] Bot responding in Telegram
- [ ] First backup created: `./backup.sh`

---

**Keep this page bookmarked for quick reference!**
