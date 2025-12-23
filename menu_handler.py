"""
Menu Handler for HomeAI Bot (v2.0) - Inline Version
Implements 'Apple-Design' Menu System
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class MenuHandler:
    """Manages all bot menus, dashboards, and navigation flows"""
    
    def __init__(self, ha_controller, db):
        self.ha = ha_controller
        self.db = db

    async def send_main_menu(self, update: Update, text: str = "📱 **HomeAI Control Center**"):
        """Sends the Main Menu as Floating Inline Buttons"""
        buttons = [
            [InlineKeyboardButton("🏠 Status Dashboard", callback_data="cmd_status"),
             InlineKeyboardButton("💡 Quick Controls", callback_data="cmd_quick")],
            [InlineKeyboardButton("🎬 Scenes", callback_data="cmd_scenes"),
             InlineKeyboardButton("📊 Analytics", callback_data="cmd_analytics")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="cmd_settings")]
        ]
        markup = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")

    async def generate_dashboard(self, context_data: dict) -> tuple[str, InlineKeyboardMarkup]:
        """
        Generates the 'Visual Status Dashboard' box
        """
        lights = context_data.get("lights", {"on": 0, "total": 0})
        temp = context_data.get("temp", "N/A")
        doors = context_data.get("doors_open", [])
        
        # Status indicators
        light_status = "● ON" if lights["on"] > 0 else "○ OFF"
        security_status = "⚠️ Alert" if doors else "🛡️ Secure"
        
        dashboard = f"""
🏠 **Home Status** ({context_data.get('time', '')})

┌─ 💡 **Lighting** ─────────┐
│ Active: {lights['on']}/{lights['total']}       {light_status}     │
└───────────────────────┘

┌─ 🌡️ **Climate** ──────────┐
│ Avg Temp: {temp}°C      │
│ Status: ✓ Optimal     │
└───────────────────────┘

┌─ 🔒 **Security** ─────────┐
│ Doors Open: {len(doors)}         │
│ System: {security_status}    │
└───────────────────────┘
"""
        buttons = [
            [InlineKeyboardButton("💡 Control Lights", callback_data="lights_menu"),
             InlineKeyboardButton("🔄 Refresh", callback_data="dashboard_refresh")],
             [InlineKeyboardButton("⬅️ Menu", callback_data="main_menu_return")]
        ]
        
        return dashboard, InlineKeyboardMarkup(buttons)

    async def get_quick_controls(self, home_state: dict) -> tuple[str, InlineKeyboardMarkup]:
        text = "💡 **Quick Actions**"
        buttons = []
        
        if home_state.get('lights_on', 0) > 0:
            buttons.append([InlineKeyboardButton("🌑 Lights OFF", callback_data="action_lights_off_all")])
        else:
            buttons.append([InlineKeyboardButton("☀️ Lights ON", callback_data="action_lights_on_all")])
            
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu_return")])
        
        return text, InlineKeyboardMarkup(buttons)

    async def get_scene_menu(self, level="categories", category=None) -> tuple[str, InlineKeyboardMarkup]:
        if level == "categories":
            text = "🎬 **Scene Categories**"
            buttons = [
                [InlineKeyboardButton("🌅 Morning", callback_data="scenes_cat_morning"),
                 InlineKeyboardButton("🌙 Evening", callback_data="scenes_cat_evening")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu_return")]
            ]
            return text, InlineKeyboardMarkup(buttons)
        elif level == "specific":
            text = f"🌅 **{category.title()}**"
            buttons = [[InlineKeyboardButton(f"Activate {category}", callback_data=f"scene_activate_{category}")],
                       [InlineKeyboardButton("⬅️ Back", callback_data="cmd_scenes")]]
            return text, InlineKeyboardMarkup(buttons)
        return "Error", None
