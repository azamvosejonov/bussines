from app import db
from app.models import (
    Project, Task, Customer, CustomerInteraction, Invoice, InvoiceItem,
    CashFlow, Payroll, Employee, Business, BusinessSettings, Shift, KPI
)
from datetime import datetime, timedelta
from sqlalchemy import func

class ProjectService:
    @staticmethod
    def calculate_project_profit(project_id):
        """Calculate project profitability"""
        project = Project.query.get(project_id)
        if not project:
            return None

        # Calculate total expenses for this project
        project_expenses = db.session.query(func.sum(CashFlow.amount)).filter(
            CashFlow.project_id == project_id,
            CashFlow.transaction_type == 'expense'
        ).scalar() or 0

        # Calculate total income from this project
        project_income = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.project_id == project_id,
            Invoice.status == 'paid'
        ).scalar() or 0

        # Update project actual cost and profit
        project.actual_cost = project_expenses
        project.profit = project_income - project_expenses

        # Calculate progress based on completed tasks
        total_tasks = len(project.tasks)
        completed_tasks = len([t for t in project.tasks if t.status == 'done'])
        project.progress_percentage = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

        db.session.commit()

        return {
            'project_id': project_id,
            'budget': project.budget,
            'actual_cost': project.actual_cost,
            'income': project_income,
            'profit': project.profit,
            'progress': project.progress_percentage
        }

class CRMService:
    @staticmethod
    def calculate_customer_lifetime_value(customer_id):
        """Calculate customer's lifetime value"""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None

        # Calculate total spent and purchases
        total_spent = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.customer_id == customer_id,
            Invoice.status == 'paid'
        ).scalar() or 0

        total_purchases = db.session.query(func.count(Invoice.id)).filter(
            Invoice.customer_id == customer_id,
            Invoice.status == 'paid'
        ).scalar() or 0

        # Calculate average order value
        avg_order_value = total_spent / total_purchases if total_purchases > 0 else 0

        # Update customer data
        customer.total_spent = total_spent
        customer.total_purchases = total_purchases
        customer.lifetime_value = total_spent  # Can be enhanced with future value predictions

        db.session.commit()

        return {
            'customer_id': customer_id,
            'total_spent': total_spent,
            'total_purchases': total_purchases,
            'avg_order_value': avg_order_value,
            'lifetime_value': customer.lifetime_value,
            'last_visit': customer.last_visit
        }

class PayrollService:
    @staticmethod
    def calculate_employee_payroll(employee_id, period_start, period_end):
        """Calculate detailed payroll for an employee"""
        employee = Employee.query.get(employee_id)
        if not employee:
            return None

        # Base salary
        base_salary = employee.base_salary

        # Calculate worked hours for the period
        total_worked_hours = 0
        shifts = Shift.query.filter(
            Shift.employee_id == employee_id,
            Shift.start_time >= period_start,
            Shift.end_time <= period_end,
            Shift.status == 'completed'
        ).all()

        for shift in shifts:
            if shift.start_time and shift.end_time:
                duration = shift.end_time - shift.start_time
                total_worked_hours += duration.total_seconds() / 3600

        # Hourly rate calculation (if applicable)
        hourly_rate = base_salary / 160 if employee.salary_type == 'monthly' else employee.base_salary

        # Calculate bonuses from KPIs
        total_bonus = 0
        kpis = KPI.query.filter(
            KPI.employee_id == employee_id,
            KPI.date >= period_start,
            KPI.date <= period_end
        ).all()

        for kpi in kpis:
            if kpi.productivity_score > 80:  # High performance bonus
                total_bonus += base_salary * 0.1  # 10% bonus

        # Calculate penalties (example: absences, late arrivals)
        total_penalties = 0
        # Add penalty logic based on attendance, etc.

        # Calculate final salary
        if employee.salary_type == 'monthly':
            final_salary = base_salary + total_bonus - total_penalties
        else:
            final_salary = (total_worked_hours * hourly_rate) + total_bonus - total_penalties

        return {
            'employee_id': employee_id,
            'employee_name': f"{employee.first_name} {employee.last_name}",
            'period_start': period_start,
            'period_end': period_end,
            'base_salary': base_salary,
            'worked_hours': total_worked_hours,
            'hourly_rate': hourly_rate,
            'bonuses': total_bonus,
            'penalties': total_penalties,
            'final_salary': final_salary
        }

class CashFlowService:
    @staticmethod
    def get_business_cash_flow(business_id, start_date, end_date):
        """Get comprehensive cash flow analysis"""
        # Income transactions
        income_transactions = CashFlow.query.filter(
            CashFlow.business_id == business_id,
            CashFlow.transaction_type == 'income',
            CashFlow.transaction_date >= start_date,
            CashFlow.transaction_date <= end_date
        ).all()

        # Expense transactions
        expense_transactions = CashFlow.query.filter(
            CashFlow.business_id == business_id,
            CashFlow.transaction_type == 'expense',
            CashFlow.transaction_date >= start_date,
            CashFlow.transaction_date <= end_date
        ).all()

        # Calculate totals
        total_income = sum(t.amount for t in income_transactions)
        total_expenses = sum(t.amount for t in expense_transactions)
        net_profit = total_income - total_expenses

        # Group by categories
        income_by_category = {}
        expense_by_category = {}

        for transaction in income_transactions:
            income_by_category[transaction.category] = income_by_category.get(transaction.category, 0) + transaction.amount

        for transaction in expense_transactions:
            expense_by_category[transaction.category] = expense_by_category.get(transaction.category, 0) + transaction.amount

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'income_by_category': income_by_category,
            'expense_by_category': expense_by_category,
            'transactions': {
                'income': [{'date': t.transaction_date, 'category': t.category, 'amount': t.amount, 'description': t.description}
                          for t in income_transactions],
                'expenses': [{'date': t.transaction_date, 'category': t.category, 'amount': t.amount, 'description': t.description}
                           for t in expense_transactions]
            }
        }

class InvoiceService:
    @staticmethod
    def generate_invoice_number(business_id):
        """Generate unique invoice number"""
        today = datetime.now().date()
        date_prefix = today.strftime('%Y%m%d')

        # Count existing invoices for today
        existing_count = Invoice.query.filter(
            Invoice.business_id == business_id,
            Invoice.invoice_number.like(f'{date_prefix}%')
        ).count()

        invoice_number = f"{date_prefix}{(existing_count + 1):03d}"
        return invoice_number

    @staticmethod
    def calculate_invoice_totals(invoice):
        """Calculate totals for an invoice"""
        subtotal = sum(item.total_price for item in invoice.items)
        tax_amount = subtotal * (invoice.business.settings.tax_rate / 100) if invoice.business.settings else 0
        total_amount = subtotal + tax_amount - invoice.discount_amount

        invoice.total_amount = total_amount
        invoice.tax_amount = tax_amount

        db.session.commit()
        return invoice
