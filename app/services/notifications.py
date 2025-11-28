import os
import asyncio
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Mail, Message
from telegram import Bot
from app import db
from app.models import (
    User, Business, Employee, Product, Payroll, Notification,
    AlertRule, InventoryAlert, DebtReminder, Expense
)

mail = Mail()

class NotificationService:
    def __init__(self):
        self.telegram_bot = None
        if os.getenv('TELEGRAM_BOT_TOKEN'):
            self.telegram_bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

    async def send_telegram_message(self, chat_id, message):
        """Send message via Telegram"""
        if self.telegram_bot:
            try:
                await self.telegram_bot.send_message(chat_id=chat_id, text=message)
                return True
            except Exception as e:
                current_app.logger.error(f"Telegram send failed: {e}")
                return False
        return False

    def send_email(self, to_email, subject, body):
        """Send email notification"""
        try:
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@business.com')
            )
            mail.send(msg)
            return True
        except Exception as e:
            current_app.logger.error(f"Email send failed: {e}")
            return False

    def create_notification(self, business_id, user_id, title, message, notification_type='in_app', priority='normal'):
        """Create a notification record"""
        notification = Notification(
            business_id=business_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    async def send_notification(self, notification):
        """Send notification via appropriate channel"""
        success = False

        if notification.notification_type == 'telegram':
            # Get user's telegram chat ID (assuming it's stored in user profile)
            user = User.query.get(notification.user_id)
            if hasattr(user, 'telegram_chat_id') and user.telegram_chat_id:
                success = await self.send_telegram_message(user.telegram_chat_id, notification.message)

        elif notification.notification_type == 'email':
            user = User.query.get(notification.user_id)
            success = self.send_email(user.email, notification.title, notification.message)

        # Update notification status
        notification.status = 'sent' if success else 'failed'
        notification.sent_at = datetime.utcnow()
        db.session.commit()

        return success

class AlertChecker:
    def __init__(self):
        self.notification_service = NotificationService()

    def check_salary_alerts(self):
        """Check for upcoming salary payments"""
        today = datetime.utcnow().date()
        alert_date = today + timedelta(days=3)  # Alert 3 days before

        # Get all businesses and their owners
        businesses = Business.query.all()

        for business in businesses:
            # Check if salary alert rule exists and is active
            alert_rule = AlertRule.query.filter_by(
                business_id=business.id,
                alert_type='salary_due',
                is_active=True
            ).first()

            if alert_rule:
                # Get employees whose salary is due soon
                employees = Employee.query.filter_by(business_id=business.id, is_active=True).all()

                for employee in employees:
                    # Assuming monthly salary on the hire date
                    if employee.hire_date.day == alert_date.day:
                        message = f"🔔 Salary Alert: {employee.first_name} {employee.last_name}'s salary of ${employee.base_salary} is due in 3 days"
                        self.notification_service.create_notification(
                            business.id,
                            business.owner_id,
                            "Upcoming Salary Payment",
                            message,
                            'telegram' if alert_rule.telegram_enabled else 'email',
                            'high'
                        )

    def check_inventory_alerts(self):
        """Check for low inventory"""
        businesses = Business.query.all()

        for business in businesses:
            alert_rule = AlertRule.query.filter_by(
                business_id=business.id,
                alert_type='inventory_low',
                is_active=True
            ).first()

            if alert_rule:
                # Check products with low stock
                products = Product.query.filter_by(business_id=business.id).all()

                for product in products:
                    if product.quantity <= product.min_quantity:
                        message = f"⚠️ Low Inventory Alert: {product.name} has only {product.quantity} units left (minimum: {product.min_quantity})"
                        self.notification_service.create_notification(
                            business.id,
                            business.owner_id,
                            "Low Inventory Alert",
                            message,
                            'telegram' if alert_rule.telegram_enabled else 'email',
                            'high'
                        )

    def check_debt_alerts(self):
        """Check for overdue debts"""
        today = datetime.utcnow().date()

        businesses = Business.query.all()

        for business in businesses:
            alert_rule = AlertRule.query.filter_by(
                business_id=business.id,
                alert_type='debt_overdue',
                is_active=True
            ).first()

            if alert_rule:
                # Check overdue debts
                overdue_debts = DebtReminder.query.filter(
                    DebtReminder.business_id == business.id,
                    DebtReminder.due_date < today,
                    DebtReminder.status == 'active'
                ).all()

                for debt in overdue_debts:
                    days_overdue = (today - debt.due_date).days
                    message = f"🚨 Overdue Debt Alert: {debt.debtor_name} owes ${debt.amount} ({days_overdue} days overdue)"
                    self.notification_service.create_notification(
                        business.id,
                        business.owner_id,
                        "Overdue Debt Alert",
                        message,
                        'telegram' if alert_rule.telegram_enabled else 'email',
                        'urgent'
                    )

    def check_expense_reminders(self):
        """Check for planned expenses"""
        today = datetime.utcnow().date()
        reminder_date = today + timedelta(days=1)  # Remind 1 day before

        businesses = Business.query.all()

        for business in businesses:
            alert_rule = AlertRule.query.filter_by(
                business_id=business.id,
                alert_type='expense_reminder',
                is_active=True
            ).first()

            if alert_rule:
                # Check planned expenses (assuming there's a planned_date field or similar)
                # For now, we'll check recurring expenses or scheduled payments
                planned_expenses = Expense.query.filter(
                    Expense.business_id == business.id,
                    Expense.expense_date == reminder_date
                ).all()

                for expense in planned_expenses:
                    message = f"📅 Expense Reminder: Planned expense of ${expense.amount} for {expense.category} tomorrow"
                    self.notification_service.create_notification(
                        business.id,
                        business.owner_id,
                        "Expense Reminder",
                        message,
                        'telegram' if alert_rule.telegram_enabled else 'email',
                        'normal'
                    )

    def check_report_alerts(self):
        """Check if it's time to send reports"""
        today = datetime.utcnow().date()

        businesses = Business.query.all()

        for business in businesses:
            alert_rule = AlertRule.query.filter_by(
                business_id=business.id,
                alert_type='report_time',
                is_active=True
            ).first()

            if alert_rule:
                # Check if today is report day (e.g., end of month, week, etc.)
                # For simplicity, let's assume monthly reports on the last day of month
                tomorrow = today + timedelta(days=1)
                if tomorrow.month != today.month:  # Last day of month
                    message = f"📊 Report Time: Monthly report is due tomorrow. Generate and send reports to stakeholders."
                    self.notification_service.create_notification(
                        business.id,
                        business.owner_id,
                        "Report Generation Reminder",
                        message,
                        'telegram' if alert_rule.telegram_enabled else 'email',
                        'normal'
                    )

    async def run_all_checks(self):
        """Run all alert checks"""
        try:
            self.check_salary_alerts()
            self.check_inventory_alerts()
            self.check_debt_alerts()
            self.check_expense_reminders()
            self.check_report_alerts()

            # Send pending notifications
            pending_notifications = Notification.query.filter_by(status='pending').all()

            for notification in pending_notifications:
                await self.notification_service.send_notification(notification)

            current_app.logger.info("Alert checks completed successfully")
        except Exception as e:
            current_app.logger.error(f"Alert check failed: {e}")

# Global instance
alert_checker = AlertChecker()
