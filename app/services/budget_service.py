from app import db
from app.models import Budget, BudgetItem, Expense, Sale
from datetime import datetime
from sqlalchemy import func, extract

class BudgetService:
    @staticmethod
    def create_budget(business_id, name, budget_type, year, month=None, quarter=None, description=None, user_id=None):
        """Create a new budget"""
        budget = Budget(
            business_id=business_id,
            name=name,
            description=description,
            budget_type=budget_type,
            year=year,
            month=month,
            quarter=quarter,
            created_by=user_id
        )
        db.session.add(budget)
        db.session.commit()
        return budget

    @staticmethod
    def add_budget_item(budget_id, category, subcategory, budgeted_amount, item_type, description=None):
        """Add an item to a budget"""
        item = BudgetItem(
            budget_id=budget_id,
            category=category,
            subcategory=subcategory,
            budgeted_amount=budgeted_amount,
            item_type=item_type,
            description=description
        )
        db.session.add(item)
        db.session.commit()

        # Update budget totals
        BudgetService.update_budget_totals(budget_id)
        return item

    @staticmethod
    def update_budget_totals(budget_id):
        """Update the total budgeted amounts for a budget"""
        budget = Budget.query.get(budget_id)
        if budget:
            income_total = db.session.query(func.sum(BudgetItem.budgeted_amount)).filter_by(
                budget_id=budget_id, item_type='income'
            ).scalar() or 0.0

            expense_total = db.session.query(func.sum(BudgetItem.budgeted_amount)).filter_by(
                budget_id=budget_id, item_type='expense'
            ).scalar() or 0.0

            budget.total_budgeted_income = income_total
            budget.total_budgeted_expenses = expense_total
            db.session.commit()

    @staticmethod
    def get_budget_actuals(budget_id):
        """Calculate actual amounts for budget items based on real transactions"""
        budget = Budget.query.get(budget_id)
        if not budget:
            return {}

        actuals = {}

        # Get actual expenses by category
        if budget.budget_type == 'monthly':
            start_date = datetime(budget.year, budget.month, 1)
            if budget.month == 12:
                end_date = datetime(budget.year + 1, 1, 1)
            else:
                end_date = datetime(budget.year, budget.month + 1, 1)
        elif budget.budget_type == 'yearly':
            start_date = datetime(budget.year, 1, 1)
            end_date = datetime(budget.year + 1, 1, 1)
        else:  # quarterly
            quarter_start_month = (budget.quarter - 1) * 3 + 1
            start_date = datetime(budget.year, quarter_start_month, 1)
            end_date = datetime(budget.year, quarter_start_month + 3, 1)

        # Get actual expenses
        expenses = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).filter(
            Expense.business_id == budget.business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date < end_date
        ).group_by(Expense.category).all()

        # Get actual sales/revenue
        sales_total = db.session.query(func.sum(Sale.total)).filter(
            Sale.business_id == budget.business_id,
            Sale.sale_date >= start_date,
            Sale.sale_date < end_date
        ).scalar() or 0.0

        actuals['revenue'] = sales_total

        for expense in expenses:
            actuals[expense.category.lower()] = expense.total

        return actuals

    @staticmethod
    def update_actual_amounts(budget_id):
        """Update actual amounts for all budget items"""
        budget = Budget.query.get(budget_id)
        if not budget:
            return

        actuals = BudgetService.get_budget_actuals(budget_id)

        # Update budget items with actual amounts
        for item in budget.items:
            if item.item_type == 'income':
                item.actual_amount = actuals.get('revenue', 0.0)
            else:
                # Try to match by category name
                category_key = item.category.lower().replace(' ', '_')
                item.actual_amount = actuals.get(category_key, actuals.get(item.category.lower(), 0.0))

        db.session.commit()

    @staticmethod
    def get_budget_analysis(budget_id):
        """Get detailed budget analysis with variances"""
        budget = Budget.query.get(budget_id)
        if not budget:
            return None

        # Update actual amounts first
        BudgetService.update_actual_amounts(budget_id)

        analysis = {
            'budget': budget,
            'items': [],
            'summary': {
                'total_budgeted_income': budget.total_budgeted_income,
                'total_budgeted_expenses': budget.total_budgeted_expenses,
                'total_actual_income': 0.0,
                'total_actual_expenses': 0.0,
                'income_variance': 0.0,
                'expense_variance': 0.0,
                'net_budgeted': budget.total_budgeted_income - budget.total_budgeted_expenses,
                'net_actual': 0.0,
                'net_variance': 0.0
            }
        }

        for item in budget.items:
            variance = item.actual_amount - item.budgeted_amount
            variance_percent = (variance / item.budgeted_amount * 100) if item.budgeted_amount != 0 else 0

            analysis['items'].append({
                'item': item,
                'variance': variance,
                'variance_percent': variance_percent,
                'status': 'over_budget' if variance > 0 and item.item_type == 'expense' else 'under_budget' if variance < 0 and item.item_type == 'expense' else 'on_track'
            })

            if item.item_type == 'income':
                analysis['summary']['total_actual_income'] += item.actual_amount
            else:
                analysis['summary']['total_actual_expenses'] += item.actual_amount

        # Calculate summary variances
        analysis['summary']['income_variance'] = analysis['summary']['total_actual_income'] - analysis['summary']['total_budgeted_income']
        analysis['summary']['expense_variance'] = analysis['summary']['total_actual_expenses'] - analysis['summary']['total_budgeted_expenses']
        analysis['summary']['net_actual'] = analysis['summary']['total_actual_income'] - analysis['summary']['total_actual_expenses']
        analysis['summary']['net_variance'] = analysis['summary']['net_actual'] - analysis['summary']['net_budgeted']

        return analysis

    @staticmethod
    def get_expense_analysis(business_id, start_date=None, end_date=None):
        """Analyze expenses by category"""
        if not start_date:
            start_date = datetime(datetime.now().year, 1, 1)
        if not end_date:
            end_date = datetime.now()

        expenses = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total_amount'),
            func.count(Expense.id).label('transaction_count'),
            func.avg(Expense.amount).label('avg_amount')
        ).filter(
            Expense.business_id == business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all()

        total_expenses = sum(exp.total_amount for exp in expenses)

        analysis = []
        for exp in expenses:
            percentage = (exp.total_amount / total_expenses * 100) if total_expenses > 0 else 0
            analysis.append({
                'category': exp.category,
                'total_amount': exp.total_amount,
                'transaction_count': exp.transaction_count,
                'avg_amount': exp.avg_amount,
                'percentage': percentage
            })

        return {
            'expenses': analysis,
            'total_expenses': total_expenses,
            'period': {'start': start_date, 'end': end_date}
        }
