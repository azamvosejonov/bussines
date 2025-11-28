# 🚀 Business Management System

**Universal Enterprise Business Management Platform**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.3+-red.svg)](https://flask.palletsprojects.com)

## 📋 Overview

This is a comprehensive business management system built with Flask that provides:

- ✅ **Web Dashboard** - Complete business analytics and management
- ✅ **Telegram Bot** - Mobile notifications and commands
- ✅ **QR Code System** - Inventory management with QR scanning
- ✅ **Tax Calculator** - Automatic tax calculations for multiple countries
- ✅ **Currency Converter** - Real-time currency exchange
- ✅ **Multi-user System** - Role-based access control
- ✅ **Dark Professional Theme** - Modern UI/UX design

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Steps

1. **Clone and Setup:**
```bash
cd /path/to/your/projects
git clone <repository-url>
cd biznes_uchun
```

2. **Create Virtual Environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration:**
```bash
# Copy and edit .env file
cp .env.example .env
# Edit .env with your settings
```

5. **Database Setup:**
```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

## 🚀 Running the Application

### Start Web Application
```bash
python main.py
```
Access at: http://127.0.0.1:5000

### Start Telegram Bot (in separate terminal)
```bash
python run_telegram_bot.py
```
Bot Username: @Business_Partner_uz_bot

## 🤖 Telegram Bot Features

### Commands
- `/start` - Initialize bot and link account
- `/stats` - Today's business statistics
- `/clockin` - Clock in for work
- `/clockout` - Clock out from work
- `/help` - Show all available commands

### Automatic Notifications
- 🔔 Payroll due alerts
- 📦 Low inventory alerts
- 💰 Overdue debt reminders
- 📊 Report generation notifications
- ⚠️ Emergency alerts

## 🎨 Features

### Core Modules
1. **User Management**
   - Multi-role system (Admin, Business Owner, HR, etc.)
   - Secure authentication
   - Profile management

2. **Business Analytics**
   - Real-time dashboards
   - Revenue/profit tracking
   - Customer analytics
   - Performance metrics

3. **Inventory Management**
   - QR code generation
   - Stock tracking
   - Low stock alerts
   - Transaction history

4. **Financial Tools**
   - Tax calculator (UZ, US, RU, KZ, TR)
   - Currency converter
   - Invoice management
   - Cash flow tracking

5. **Employee Management**
   - Time tracking
   - Payroll management
   - Performance monitoring
   - Leave management

## 📱 Mobile Integration

### Telegram Bot Setup
1. Open Telegram
2. Search for `@Business_Partner_uz_bot`
3. Send `/start` command
4. Your account will be automatically linked

### QR Code Scanning
- Generate QR codes for inventory items
- Scan using camera for instant stock updates
- Mobile-friendly interface

## 🔧 API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `POST /logout` - User logout

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics

### Business Management
- `GET /inventory/<biz_id>` - Inventory management
- `POST /inventory/<biz_id>/add` - Add inventory item
- `GET /inventory/<biz_id>/qr/<item_id>` - Generate QR code
- `GET /analytics/<biz_id>` - Business analytics

### Financial Tools
- `GET /tax-calculator` - Tax calculation interface
- `POST /tax-calculator/calculate` - Calculate taxes
- `GET /currency-converter` - Currency conversion
- `POST /currency-converter/convert` - Convert currencies

## 🎨 UI/UX Design

### Dark Professional Theme
- **Colors:** Black background, blue accents, professional gradients
- **Typography:** Inter font, optimized readability
- **Components:** Glassmorphism effects, smooth animations
- **Responsive:** Mobile-first design approach

### Key Design Elements
- Modern card layouts
- Gradient buttons
- Smooth transitions
- Professional color scheme
- Mobile-responsive

## 📊 Business Types Supported

- 🏪 **Retail Stores** - POS, inventory, customer management
- 🍽️ **Restaurants** - Menu management, table tracking, orders
- 🏭 **Manufacturing** - Production tracking, supply chain
- 💼 **Service Businesses** - Appointment scheduling, client management
- 🏢 **General Business** - Universal business operations

## 🔐 Security Features

- **Role-based Access Control** - Granular permissions
- **Secure Authentication** - Password hashing, session management
- **Data Validation** - Input sanitization and validation
- **Audit Logging** - Complete activity tracking
- **Telegram Integration** - Secure bot communication

## 🚀 Deployment

### Production Setup
1. Set environment variables for production
2. Configure database for production use
3. Set up web server (nginx + gunicorn recommended)
4. Configure SSL certificates
5. Set up monitoring and logging

### Environment Variables
```bash
SECRET_KEY=your_production_secret_key
DATABASE_URL=postgresql://user:pass@host:port/db
TELEGRAM_BOT_TOKEN=your_bot_token
FLASK_ENV=production
```

## 📈 Performance

- **Database Optimization** - Indexed queries, connection pooling
- **Caching** - Redis for session and data caching
- **CDN** - Static file delivery optimization
- **Async Operations** - Background task processing

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- 📧 Email: support@businessmanagement.com
- 💬 Telegram: @Business_Partner_uz_bot
- 📖 Documentation: [Link to docs]

## 🎉 Acknowledgments

- Flask framework
- Bootstrap CSS framework
- Font Awesome icons
- Telegram Bot API
- Open source community

---

**Built with ❤️ for modern businesses**

*Last updated: November 2025*
