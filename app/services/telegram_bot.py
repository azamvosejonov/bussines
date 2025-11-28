import os
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app import db
from app.models import User, Business

class TelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.application = None

        if self.token:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()

    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("clockin", self.clock_in_command))
        self.application.add_handler(CommandHandler("clockout", self.clock_out_command))

        # Message handler for registration
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        user = update.effective_user

        # Check if user exists in our system
        db_user = User.query.filter_by(username=user.username).first() if user.username else None

        if db_user:
            # Link Telegram chat ID to user
            db_user.telegram_chat_id = str(chat_id)
            db.session.commit()

            welcome_message = f"""
👋 Salom, {db_user.username}!

Sizning Telegram hisobingiz muvaffaqiyatli bog'landi.

Mavjud buyruqlar:
/stats - Bugungi statistika
/clockin - Ishga kelish
/clockout - Ishdan ketish
/help - Yordam

Barcha bildirishnomalar shu yerga keladi! 🚀
"""
        else:
            welcome_message = """
👋 Salom!

Bu biznes boshqaruv tizimi uchun Telegram bot.

Iltimos, veb-saytda ro'yxatdan o'ting va keyin /start buyrug'ini qayta yuboring.

Yordam uchun: /help
"""

        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 *Biznes Boshqaruv Bot Yordami*

*Asosiy buyruqlar:*
/start - Botni ishga tushirish
/stats - Bugungi statistika
/clockin - Ishga kelish
/clockout - Ishdan ketish

*Avtomatik bildirishnomalar:*
• Oylik ish haqi yaqinlashganda
• Omborda mahsulot tugayotganda
• Qarz muddati o'tganda
• Xarajat eslatmalari
• Hisobot vaqti kelganda

*Qo'shimcha yordam:*
Bot sizning biznes faoliyatingizni kuzatib boradi va muhim voqealar haqida xabar beradi.

Savollaringiz bo'lsa, admin bilan bog'laning.
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        chat_id = update.effective_chat.id
        user = User.query.filter_by(telegram_chat_id=str(chat_id)).first()

        if not user:
            await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz. Iltimos, veb-saytda ro'yxatdan o'ting.")
            return

        # Get user's businesses
        businesses = Business.query.filter_by(owner_id=user.id).all()

        if not businesses:
            await update.message.reply_text("❌ Sizda biznes mavjud emas.")
            return

        stats_message = f"📊 *{user.username} uchun statistika*\n\n"

        for business in businesses:
            # Today's sales
            from datetime import datetime
            today = datetime.utcnow().date()
            from app.models import Sale
            today_sales = Sale.query.filter(
                Sale.business_id == business.id,
                db.func.date(Sale.sale_date) == today
            ).all()
            total_sales = sum(s.total for s in today_sales)

            # Today's expenses
            from app.models import Expense
            today_expenses = Expense.query.filter(
                Expense.business_id == business.id,
                db.func.date(Expense.expense_date) == today
            ).all()
            total_expenses = sum(e.amount for e in today_expenses)

            # Active employees
            from app.models import Employee
            active_employees = Employee.query.filter_by(business_id=business.id, is_active=True).count()

            stats_message += f"🏢 *{business.name}*\n"
            stats_message += f"💰 Bugungi savdo: ${total_sales:.2f}\n"
            stats_message += f"💸 Bugungi xarajat: ${total_expenses:.2f}\n"
            stats_message += f"👥 Faol xodimlar: {active_employees}\n"
            stats_message += f"📈 Sof foyda: ${(total_sales - total_expenses):.2f}\n\n"

        await update.message.reply_text(stats_message, parse_mode='Markdown')

    async def clock_in_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clockin command"""
        chat_id = update.effective_chat.id
        user = User.query.filter_by(telegram_chat_id=str(chat_id)).first()

        if not user:
            await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz.")
            return

        # Find employee record
        from app.models import Employee
        employee = Employee.query.filter_by(user_id=user.id).first()

        if not employee:
            await update.message.reply_text("❌ Siz xodim sifatida ro'yxatdan o'tmagansiz.")
            return

        # Check if already clocked in today
        from app.models import Shift
        from datetime import datetime
        today = datetime.utcnow().date()
        existing_shift = Shift.query.filter(
            Shift.employee_id == employee.id,
            db.func.date(Shift.start_time) == today,
            Shift.status.in_(['in_progress', 'scheduled'])
        ).first()

        if existing_shift and existing_shift.status == 'in_progress':
            await update.message.reply_text("⚠️ Siz allaqachon ishga kelgansiz!")
            return

        # Create new shift
        shift = Shift(
            business_id=employee.business_id,
            employee_id=employee.id,
            branch_id=employee.branch_id,
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        db.session.add(shift)
        db.session.commit()

        await update.message.reply_text("✅ Muvaffaqiyatli ishga keldingiz! Ishingizni boshlang. 😊")

    async def clock_out_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clockout command"""
        chat_id = update.effective_chat.id
        user = User.query.filter_by(telegram_chat_id=str(chat_id)).first()

        if not user:
            await update.message.reply_text("❌ Siz ro'yxatdan o'tmagansiz.")
            return

        # Find employee record
        from app.models import Employee
        employee = Employee.query.filter_by(user_id=user.id).first()

        if not employee:
            await update.message.reply_text("❌ Siz xodim sifatida ro'yxatdan o'tmagansiz.")
            return

        # Find active shift
        from app.models import Shift
        from datetime import datetime
        today = datetime.utcnow().date()
        active_shift = Shift.query.filter(
            Shift.employee_id == employee.id,
            db.func.date(Shift.start_time) == today,
            Shift.status == 'in_progress'
        ).first()

        if not active_shift:
            await update.message.reply_text("⚠️ Siz bugun ishga kelmagansiz yoki allaqachon ishni tugatgansiz.")
            return

        # Clock out
        end_time = datetime.utcnow()
        active_shift.end_time = end_time
        active_shift.status = 'completed'
        db.session.commit()

        # Calculate hours worked
        duration = end_time - active_shift.start_time
        hours = duration.total_seconds() / 3600

        await update.message.reply_text(f"✅ Ishdan ketdingiz! Bugun {hours:.2f} soat ishladingiz. Dam oling! 😊")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        await update.message.reply_text("🤖 Buyruqni tushunmadim. Yordam uchun /help yozing.")

    def run(self):
        """Start the bot"""
        if self.application:
            print("🤖 Telegram bot ishga tushmoqda...")
            self.application.run_polling()
        else:
            print("❌ Telegram bot token topilmadi!")

# Global bot instance
telegram_bot = TelegramBot()
