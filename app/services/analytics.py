from app import db
from app.models import Sale, SaleItem, Product, Expense, Customer, Employee, Project, InventoryItem, KPI
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_, or_
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class BusinessAnalytics:
    @staticmethod
    def get_revenue_trends(business_id, months=12):
        """Get revenue trends over time"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=months*30)

        # Monthly revenue data
        revenue_data = db.session.query(
            extract('year', Sale.sale_date).label('year'),
            extract('month', Sale.sale_date).label('month'),
            func.sum(Sale.total).label('revenue')
        ).filter(
            Sale.business_id == business_id,
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).group_by(
            extract('year', Sale.sale_date),
            extract('month', Sale.sale_date)
        ).order_by(
            extract('year', Sale.sale_date),
            extract('month', Sale.sale_date)
        ).all()

        return [{
            'period': f"{int(r.year)}-{int(r.month):02d}",
            'revenue': float(r.revenue),
            'year': int(r.year),
            'month': int(r.month)
        } for r in revenue_data]

    @staticmethod
    def get_expense_breakdown(business_id, start_date=None, end_date=None):
        """Get detailed expense breakdown by category"""
        if not start_date:
            start_date = datetime.utcnow().date() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow().date()

        expenses = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total'),
            func.count(Expense.id).label('count')
        ).filter(
            Expense.business_id == business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).group_by(Expense.category).all()

        return [{
            'category': exp.category,
            'total': float(exp.total),
            'count': exp.count,
            'percentage': 0  # Will be calculated below
        } for exp in expenses]

    @staticmethod
    def calculate_profit_margins(business_id, period='monthly'):
        """Calculate profit margins over time"""
        periods = []
        if period == 'monthly':
            # Last 12 months
            for i in range(12):
                end_date = datetime.utcnow().date().replace(day=1) - timedelta(days=i*30)
                start_date = end_date.replace(day=1)

                revenue = db.session.query(func.sum(Sale.total)).filter(
                    Sale.business_id == business_id,
                    Sale.sale_date >= start_date,
                    Sale.sale_date < end_date + timedelta(days=30)
                ).scalar() or 0

                expenses = db.session.query(func.sum(Expense.amount)).filter(
                    Expense.business_id == business_id,
                    Expense.expense_date >= start_date,
                    Expense.expense_date < end_date + timedelta(days=30)
                ).scalar() or 0

                profit = revenue - expenses
                margin = (profit / revenue * 100) if revenue > 0 else 0

                periods.append({
                    'period': start_date.strftime('%Y-%m'),
                    'revenue': float(revenue),
                    'expenses': float(expenses),
                    'profit': float(profit),
                    'margin': float(margin)
                })

        return periods

    @staticmethod
    def forecast_revenue(business_id, months_ahead=3):
        """Forecast future revenue using linear regression"""
        revenue_data = BusinessAnalytics.get_revenue_trends(business_id, months=24)

        if len(revenue_data) < 6:
            return {"error": "Not enough historical data for forecasting"}

        # Prepare data for regression
        X = np.array(range(len(revenue_data))).reshape(-1, 1)
        y = np.array([r['revenue'] for r in revenue_data])

        # Train model
        model = LinearRegression()
        model.fit(X, y)

        # Forecast
        forecast_periods = range(len(revenue_data), len(revenue_data) + months_ahead)
        forecast_X = np.array(list(forecast_periods)).reshape(-1, 1)
        forecast_y = model.predict(forecast_X)

        forecasts = []
        for i, prediction in enumerate(forecast_y):
            forecast_date = datetime.utcnow() + timedelta(days=(i+1)*30)
            forecasts.append({
                'period': forecast_date.strftime('%Y-%m'),
                'predicted_revenue': max(0, float(prediction)),  # Ensure non-negative
                'confidence': 0.85  # Placeholder confidence level
            })

        return {
            'historical': revenue_data,
            'forecast': forecasts,
            'trend_slope': float(model.coef_[0]),
            'r_squared': float(model.score(X, y))
        }

    @staticmethod
    def get_top_performers(business_id, metric='revenue', period='monthly'):
        """Get top performing items/people/projects"""
        if metric == 'revenue':
            # Top revenue generating products
            top_products = db.session.query(
                Product.name.label('product_name'),
                func.sum(SaleItem.quantity * SaleItem.unit_price).label('total_revenue'),
                func.sum(SaleItem.quantity).label('total_quantity')
            ).join(SaleItem, Product.id == SaleItem.product_id).join(Sale, SaleItem.sale_id == Sale.id).filter(
                Sale.business_id == business_id
            ).group_by(Product.id, Product.name).order_by(
                func.sum(SaleItem.quantity * SaleItem.unit_price).desc()
            ).limit(10).all()

            return [{
                'name': p.product_name,
                'revenue': float(p.total_revenue),
                'quantity': float(p.total_quantity),
                'avg_price': float(p.total_revenue) / float(p.total_quantity) if p.total_quantity > 0 else 0
            } for p in top_products]

        elif metric == 'employees':
            # Top performing employees
            employees = db.session.query(
                Employee,
                func.sum(KPI.productivity_score).label('total_score'),
                func.count(KPI.id).label('kpi_count')
            ).join(KPI).filter(
                Employee.business_id == business_id
            ).group_by(Employee.id).order_by(
                func.avg(KPI.productivity_score).desc()
            ).limit(10).all()

            return [{
                'name': f"{emp.Employee.first_name} {emp.Employee.last_name}",
                'avg_score': float(emp.total_score) / float(emp.kpi_count) if emp.kpi_count > 0 else 0,
                'total_score': float(emp.total_score),
                'kpi_count': emp.kpi_count
            } for emp in employees]

    @staticmethod
    def get_business_insights(business_id):
        """Generate comprehensive business insights"""
        insights = {}

        # Revenue growth rate
        revenue_trends = BusinessAnalytics.get_revenue_trends(business_id, 6)
        if len(revenue_trends) >= 2:
            recent_avg = sum(r['revenue'] for r in revenue_trends[-3:]) / 3
            older_avg = sum(r['revenue'] for r in revenue_trends[:3]) / 3
            growth_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            insights['revenue_growth'] = {
                'rate': growth_rate,
                'trend': 'growing' if growth_rate > 5 else 'declining' if growth_rate < -5 else 'stable'
            }

        # Profit margin analysis
        profit_margins = BusinessAnalytics.calculate_profit_margins(business_id)
        if profit_margins:
            avg_margin = sum(p['margin'] for p in profit_margins) / len(profit_margins)
            insights['profit_margin'] = {
                'average': avg_margin,
                'status': 'healthy' if avg_margin > 20 else 'concerning' if avg_margin < 10 else 'moderate'
            }

        # Top performers
        top_products = BusinessAnalytics.get_top_performers(business_id, 'revenue')
        if top_products:
            insights['top_product'] = top_products[0]['name']

        return insights
