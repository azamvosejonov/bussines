# Business Management System - Notification Setup

## 🚨 Notification System Setup

This system provides comprehensive notifications for business alerts via Telegram and Email.

### Features

✅ **Salary Alerts** - Admin notified when employee salaries are due (3 days before)
✅ **Inventory Alerts** - Warnings when products are running low
✅ **Debt Alerts** - Notifications when debts become overdue
✅ **Expense Reminders** - Reminders for planned expenses
✅ **Report Time Alerts** - Automatic reminders to generate reports
✅ **Telegram Bot Integration** - Real-time notifications via Telegram
✅ **Email Notifications** - Professional email alerts

## 🔧 Setup Instructions

### 1. Environment Variables

Add these to your `.env` file:

```env
# Telegram Bot Setup
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

### 2. Telegram Bot Setup

1. **Create a Telegram Bot:**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot`
   - Follow instructions to create your bot
   - Copy the API token

2. **Get Your Chat ID:**
   - Start a conversation with your bot
   - Send `/start`
   - The bot will automatically link your Telegram account

3. **Run the Telegram Bot:**
   ```bash
   python run_telegram_bot.py
   ```

### 3. Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password:**
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
   - Use this password in `MAIL_PASSWORD`

### 4. Configure Alert Rules

1. **Login** to your business dashboard
2. **Go to** "Roles" → Select your business → "Manage Alerts"
3. **Create Alert Rules** for:
   - Salary Due (3 days advance warning)
   - Low Inventory (minimum stock alerts)
   - Debt Overdue (overdue payment alerts)
   - Expense Reminders (planned expense notifications)
   - Report Time (monthly report reminders)

## 🤖 Telegram Bot Commands

- `/start` - Link your Telegram account
- `/help` - Show available commands
- `/stats` - Get today's business statistics
- `/clockin` - Clock in for work
- `/clockout` - Clock out from work

## 📧 Email Notifications

The system automatically sends professional emails for:
- Report deliveries
- Urgent business alerts
- Monthly summaries

## 🔄 Automatic Background Tasks

The system runs automatic checks every hour:
- Salary due dates
- Inventory levels
- Debt deadlines
- Expense schedules
- Report generation times

## 📱 Real-time Notifications

- **Navbar Badge:** Shows unread notification count
- **Dropdown Menu:** Quick view of recent alerts
- **Telegram Alerts:** Instant notifications on your phone
- **Email Alerts:** Professional formatted emails

## 🛠️ Technical Details

### Database Tables Created:
- `notification` - Stores all notifications
- `alert_rule` - Configurable alert rules
- `inventory_alert` - Product stock monitoring
- `debt_reminder` - Customer/supplier debt tracking

### Background Services:
- APScheduler runs every hour
- Telegram bot runs continuously
- Email service for report delivery

## 🎯 Usage Examples

### Salary Alert:
*"🔔 Salary Alert: Anvar's salary of $500 is due in 3 days"*

### Inventory Alert:
*"⚠️ Low Inventory Alert: Coca Cola has only 5 units left (minimum: 10)"*

### Debt Alert:
*"🚨 Overdue Debt Alert: ABC Company owes $1200 (15 days overdue)"*

### Report Reminder:
*"📊 Report Time: Monthly report is due tomorrow. Generate and send reports."*

## 🚀 Getting Started

1. Set up environment variables
2. Configure Telegram bot
3. Set up email credentials
4. Run the main application
5. Run the Telegram bot separately
6. Configure alert rules in the web interface

The notification system will automatically start monitoring and alerting based on your configured rules!
