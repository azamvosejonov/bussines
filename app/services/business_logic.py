from app import db
from app.models import Recipe, RecipeIngredient, Product, Sale, SaleItem, BusinessSettings, AuditLog
from flask import session
from datetime import datetime

class RecipeService:
    @staticmethod
    def calculate_recipe_cost(recipe):
        """Calculate total cost of recipe based on ingredients"""
        total_cost = 0
        for ingredient in recipe.ingredients:
            if ingredient.product.cost_price and ingredient.quantity:
                total_cost += ingredient.product.cost_price * ingredient.quantity
        return total_cost

    @staticmethod
    def deduct_inventory_for_sale(sale_items, business_id, user_id):
        """Automatically deduct inventory when items are sold"""
        from app.models import Business

        business = Business.query.get(business_id)
        if not business or not business.settings or not business.settings.enable_recipes:
            return True  # Skip if recipes not enabled

        deductions = []

        for sale_item in sale_items:
            # Check if this product has recipes
            recipe = Recipe.query.filter_by(
                business_id=business_id,
                name=sale_item.product_name,
                is_active=True
            ).first()

            if recipe:
                # Deduct ingredients for this recipe
                for ingredient in recipe.ingredients:
                    deduction_amount = ingredient.quantity * sale_item.quantity

                    if ingredient.product.quantity >= deduction_amount:
                        ingredient.product.quantity -= deduction_amount
                        deductions.append({
                            'product_id': ingredient.product.id,
                            'product_name': ingredient.product.name,
                            'deducted': deduction_amount,
                            'remaining': ingredient.product.quantity
                        })
                    else:
                        # Insufficient stock - could trigger alert
                        print(f"Insufficient stock for {ingredient.product.name}: needed {deduction_amount}, available {ingredient.product.quantity}")

        # Log the deductions
        if deductions:
            for deduction in deductions:
                RecipeService.log_inventory_change(
                    business_id,
                    user_id,
                    deduction['product_id'],
                    -deduction['deducted'],  # Negative for deduction
                    f"Sale deduction for recipe item",
                    f"Remaining: {deduction['remaining']}"
                )

        db.session.commit()
        return True

    @staticmethod
    def log_inventory_change(business_id, user_id, product_id, quantity_change, reason, details=None):
        """Log inventory changes for audit trail"""
        audit_log = AuditLog(
            business_id=business_id,
            user_id=user_id,
            action='inventory_change',
            table_name='product',
            record_id=product_id,
            old_values={'quantity_change': quantity_change},
            new_values={'reason': reason, 'details': details}
        )
        db.session.add(audit_log)

    @staticmethod
    def check_inventory_levels(business_id):
        """Check for low inventory levels and trigger alerts"""
        from app.models import InventoryAlert, Product

        products = Product.query.filter_by(business_id=business_id).all()
        alerts_triggered = []

        for product in products:
            if product.quantity <= product.min_quantity:
                # Check if alert already exists
                existing_alert = InventoryAlert.query.filter_by(
                    business_id=business_id,
                    product_id=product.id
                ).first()

                if not existing_alert:
                    alert = InventoryAlert(
                        business_id=business_id,
                        product_id=product.id,
                        alert_threshold=product.min_quantity,
                        current_quantity=product.quantity
                    )
                    db.session.add(alert)
                    alerts_triggered.append(product.name)

        if alerts_triggered:
            db.session.commit()

        return alerts_triggered

class ProfitCalculator:
    @staticmethod
    def calculate_business_profit(business_id, start_date, end_date):
        """Calculate comprehensive business profit"""
        from app.models import Sale, Expense, Employee, Payroll

        # Total Revenue
        total_revenue = db.session.query(db.func.sum(Sale.total)).filter(
            Sale.business_id == business_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).scalar() or 0

        # Total Expenses
        total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.business_id == business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).scalar() or 0

        # Employee Salaries
        salary_expenses = db.session.query(db.func.sum(Payroll.amount)).filter(
            Payroll.business_id == business_id,
            Payroll.pay_date >= start_date,
            Payroll.pay_date <= end_date
        ).scalar() or 0

        # Business settings for tax and bonus rates
        business = db.session.query(Business).filter_by(id=business_id).first()
        tax_rate = business.settings.tax_rate if business.settings else 0
        bonus_rate = business.settings.bonus_rate if business.settings else 0

        # Calculate tax
        tax_amount = total_revenue * (tax_rate / 100)

        # Calculate bonuses (from revenue)
        bonus_amount = total_revenue * (bonus_rate / 100)

        # Net profit before distributions
        gross_profit = total_revenue - total_expenses - salary_expenses - tax_amount

        # Net profit after bonuses
        net_profit = gross_profit - bonus_amount

        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'salary_expenses': salary_expenses,
            'tax_amount': tax_amount,
            'bonus_amount': bonus_amount,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'period_days': (end_date - start_date).days + 1
        }

    @staticmethod
    def calculate_employee_share(business_id, employee_id, start_date, end_date):
        """Calculate employee's profit share"""
        from app.models import Employee

        employee = Employee.query.get(employee_id)
        if not employee:
            return 0

        # Get business profit for the period
        profit_data = ProfitCalculator.calculate_business_profit(business_id, start_date, end_date)

        # Employee's share percentage (could be from employee record or business settings)
        share_percentage = getattr(employee, 'profit_share_percentage', 0) or 0

        # Calculate share amount
        share_amount = profit_data['net_profit'] * (share_percentage / 100)

        return {
            'employee_id': employee_id,
            'employee_name': employee.first_name + ' ' + employee.last_name,
            'share_percentage': share_percentage,
            'share_amount': share_amount,
            'period_start': start_date,
            'period_end': end_date
        }

class AuditService:
    @staticmethod
    def log_action(business_id, user_id, action, table_name=None, record_id=None,
                   old_values=None, new_values=None, ip_address=None, user_agent=None):
        """Log user actions for audit trail"""
        meta_data = {
            'table_name': table_name,
            'record_id': record_id,
            'old_values': old_values,
            'new_values': new_values,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        # Remove None values from meta_data
        meta_data = {k: v for k, v in meta_data.items() if v is not None}
        
        audit_log = AuditLog(
            business_id=business_id,
            user_id=user_id,
            action=action,
            meta=meta_data
        )
        db.session.add(audit_log)
        db.session.commit()

    @staticmethod
    def log_login(user_id, business_id=None, ip_address=None, user_agent=None):
        """Log user login"""
        AuditService.log_action(
            business_id=business_id,
            user_id=user_id,
            action='login',
            table_name='user',
            record_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_data_change(business_id, user_id, table_name, record_id, action,
                       old_values=None, new_values=None):
        """Log data modifications"""
        AuditService.log_action(
            business_id=business_id,
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values
        )
