from app import db
from app.models import Campaign, CampaignEmployee, CampaignExpense, CampaignRevenue, CampaignTask, CampaignReport, CampaignTimeEntry
from datetime import datetime, date
from sqlalchemy import func, and_

class CampaignService:
    @staticmethod
    def create_campaign(business_id, name, campaign_type, manager_id=None, budget=0.0,
                       start_date=None, end_date=None, description=None, user_id=None):
        """Create a new campaign"""
        campaign = Campaign(
            business_id=business_id,
            name=name,
            description=description,
            campaign_type=campaign_type,
            manager_id=manager_id,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
            created_by=user_id
        )
        db.session.add(campaign)
        db.session.commit()
        return campaign

    @staticmethod
    def add_employee_to_campaign(campaign_id, employee_id, role=None, hourly_rate=0.0):
        """Add an employee to a campaign"""
        assignment = CampaignEmployee(
            campaign_id=campaign_id,
            employee_id=employee_id,
            role=role,
            hourly_rate=hourly_rate
        )
        db.session.add(assignment)
        db.session.commit()
        return assignment

    @staticmethod
    def add_campaign_expense(campaign_id, category, description, amount, expense_date,
                           vendor=None, user_id=None):
        """Add an expense to a campaign"""
        expense = CampaignExpense(
            campaign_id=campaign_id,
            category=category,
            description=description,
            amount=amount,
            expense_date=expense_date,
            vendor=vendor,
            created_by=user_id
        )
        db.session.add(expense)
        db.session.commit()

        # Update campaign totals
        CampaignService.update_campaign_totals(campaign_id)
        return expense

    @staticmethod
    def add_campaign_revenue(campaign_id, source, description, amount, revenue_date,
                           customer_id=None, user_id=None):
        """Add revenue to a campaign"""
        revenue = CampaignRevenue(
            campaign_id=campaign_id,
            source=source,
            description=description,
            amount=amount,
            revenue_date=revenue_date,
            customer_id=customer_id,
            recorded_by=user_id
        )
        db.session.add(revenue)
        db.session.commit()

        # Update campaign totals
        CampaignService.update_campaign_totals(campaign_id)
        return revenue

    @staticmethod
    def update_campaign_totals(campaign_id):
        """Update total expenses and revenue for a campaign"""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return

        # Calculate total expenses
        total_expenses = db.session.query(func.sum(CampaignExpense.amount)).filter_by(
            campaign_id=campaign_id
        ).scalar() or 0.0

        # Calculate total revenue
        total_revenue = db.session.query(func.sum(CampaignRevenue.amount)).filter_by(
            campaign_id=campaign_id
        ).scalar() or 0.0

        campaign.total_expenses = total_expenses
        campaign.total_revenue = total_revenue
        db.session.commit()

    @staticmethod
    def get_campaign_profit_loss(campaign_id):
        """Calculate profit/loss for a campaign"""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return None

        # Ensure totals are up to date
        CampaignService.update_campaign_totals(campaign_id)

        profit_loss = campaign.total_revenue - campaign.total_expenses
        roi = (profit_loss / campaign.total_expenses * 100) if campaign.total_expenses > 0 else 0

        return {
            'campaign': campaign,
            'total_revenue': campaign.total_revenue,
            'total_expenses': campaign.total_expenses,
            'profit_loss': profit_loss,
            'roi_percentage': roi,
            'is_profitable': profit_loss > 0,
            'budget_remaining': campaign.budget - campaign.total_expenses if campaign.budget > 0 else 0,
            'budget_utilization': (campaign.total_expenses / campaign.budget * 100) if campaign.budget > 0 else 0
        }

    @staticmethod
    def get_campaign_analytics(campaign_id, start_date=None, end_date=None):
        """Get detailed analytics for a campaign"""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return None

        if not start_date:
            start_date = campaign.start_date or date.today().replace(day=1)
        if not end_date:
            end_date = campaign.end_date or date.today()

        # Expense breakdown by category
        expense_breakdown = db.session.query(
            CampaignExpense.category,
            func.sum(CampaignExpense.amount).label('total')
        ).filter(
            and_(
                CampaignExpense.campaign_id == campaign_id,
                CampaignExpense.expense_date >= start_date,
                CampaignExpense.expense_date <= end_date
            )
        ).group_by(CampaignExpense.category).all()

        # Revenue breakdown by source
        revenue_breakdown = db.session.query(
            CampaignRevenue.source,
            func.sum(CampaignRevenue.amount).label('total')
        ).filter(
            and_(
                CampaignRevenue.campaign_id == campaign_id,
                CampaignRevenue.revenue_date >= start_date,
                CampaignRevenue.revenue_date <= end_date
            )
        ).group_by(CampaignRevenue.source).all()

        # Employee hours and costs
        employee_stats = db.session.query(
            CampaignEmployee.employee_id,
            CampaignEmployee.role,
            func.sum(CampaignTimeEntry.hours).label('total_hours'),
            func.sum(CampaignTimeEntry.hours * CampaignEmployee.hourly_rate).label('total_cost')
        ).join(
            CampaignTimeEntry, CampaignEmployee.employee_id == CampaignTimeEntry.employee_id
        ).filter(
            and_(
                CampaignEmployee.campaign_id == campaign_id,
                CampaignTimeEntry.date >= start_date,
                CampaignTimeEntry.date <= end_date
            )
        ).group_by(CampaignEmployee.employee_id, CampaignEmployee.role).all()

        # Task completion stats
        task_stats = db.session.query(
            CampaignTask.status,
            func.count(CampaignTask.id).label('count')
        ).filter_by(campaign_id=campaign_id).group_by(CampaignTask.status).all()

        return {
            'campaign': campaign,
            'period': {'start': start_date, 'end': end_date},
            'expense_breakdown': [{'category': e.category, 'amount': e.total} for e in expense_breakdown],
            'revenue_breakdown': [{'source': r.source, 'amount': r.total} for r in revenue_breakdown],
            'employee_stats': [{
                'employee_id': e.employee_id,
                'role': e.role,
                'total_hours': e.total_hours or 0,
                'total_cost': e.total_cost or 0
            } for e in employee_stats],
            'task_stats': [{'status': t.status, 'count': t.count} for t in task_stats]
        }

    @staticmethod
    def get_campaigns_summary(business_id):
        """Get summary of all campaigns for a business"""
        campaigns = Campaign.query.filter_by(business_id=business_id).all()

        summary = []
        for campaign in campaigns:
            # Ensure totals are up to date
            CampaignService.update_campaign_totals(campaign.id)

            profit_loss = campaign.total_revenue - campaign.total_expenses
            progress = CampaignService.calculate_campaign_progress(campaign.id)

            summary.append({
                'campaign': campaign,
                'profit_loss': profit_loss,
                'is_profitable': profit_loss > 0,
                'progress_percentage': progress,
                'active_employees': len(campaign.employees),
                'pending_tasks': len([t for t in campaign.tasks if t.status in ['todo', 'in_progress']])
            })

        return summary

    @staticmethod
    def calculate_campaign_progress(campaign_id):
        """Calculate overall progress percentage for a campaign"""
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return 0

        tasks = campaign.tasks
        if not tasks:
            return 0

        completed_tasks = len([t for t in tasks if t.status == 'completed'])
        total_tasks = len(tasks)

        if total_tasks == 0:
            return 0

        # Weight by task priority
        weighted_progress = 0
        total_weight = 0

        for task in tasks:
            weight = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}.get(task.priority, 2)
            total_weight += weight

            if task.status == 'completed':
                weighted_progress += weight

        return int((weighted_progress / total_weight * 100) if total_weight > 0 else 0)

    @staticmethod
    def log_time_entry(campaign_id, employee_id, hours, date, description=None, task_id=None, user_id=None):
        """Log time entry for an employee on a campaign"""
        time_entry = CampaignTimeEntry(
            campaign_id=campaign_id,
            employee_id=employee_id,
            task_id=task_id,
            date=date,
            hours=hours,
            description=description
        )
        db.session.add(time_entry)
        db.session.commit()

        # Update task actual hours if task_id is provided
        if task_id:
            task = CampaignTask.query.get(task_id)
            if task:
                # Recalculate actual hours for the task
                actual_hours = db.session.query(func.sum(CampaignTimeEntry.hours)).filter_by(
                    task_id=task_id
                ).scalar() or 0.0
                task.actual_hours = actual_hours
                db.session.commit()

        return time_entry
