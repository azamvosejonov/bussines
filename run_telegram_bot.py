#!/usr/bin/env python3
"""
Telegram Bot Runner for Business Management System
Run this script separately from the main Flask app.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import and run the Telegram bot
from services.telegram_bot import telegram_bot

if __name__ == '__main__':
    print("🚀 Starting Business Management Telegram Bot...")
    print("🤖 Bot Username: @Business_Partner_uz_bot")
    print("📱 Bot Token: Configured ✓")
    print("🌐 Web App: Running on http://127.0.0.1:5000")
    print("")
    print("📋 Available Commands:")
    print("  /start   - Botni ishga tushirish")
    print("  /stats   - Bugungi statistika")
    print("  /clockin - Ishga kelish")
    print("  /clockout- Ishdan ketish")
    print("  /help    - Yordam")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    telegram_bot.run()
