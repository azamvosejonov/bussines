from app import db
from app.models import MarketingCampaign, CampaignPerformance, ContractTemplate, Contract, ContractVersion, CurrencyRate, TaxRate
from datetime import datetime, timedelta
import requests
from sqlalchemy import or_

class MarketingService:
    @staticmethod
    def calculate_campaign_roi(campaign_id):
        """Calculate ROI for a marketing campaign"""
        campaign = MarketingCampaign.query.get(campaign_id)
        if not campaign:
            return None

        if campaign.spent_amount > 0:
            roi = ((campaign.revenue_generated - campaign.spent_amount) / campaign.spent_amount) * 100
        else:
            roi = 0

        campaign.roi_percentage = roi
        db.session.commit()

        return {
            'campaign_id': campaign_id,
            'spent': campaign.spent_amount,
            'revenue': campaign.revenue_generated,
            'roi_percentage': roi,
            'status': 'excellent' if roi > 200 else 'good' if roi > 100 else 'poor' if roi > 0 else 'loss'
        }

    @staticmethod
    def get_campaign_performance(campaign_id, days=30):
        """Get detailed campaign performance over time"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

        performance_data = CampaignPerformance.query.filter(
            CampaignPerformance.campaign_id == campaign_id,
            CampaignPerformance.date >= start_date,
            CampaignPerformance.date <= end_date
        ).order_by(CampaignPerformance.date).all()

        return [{
            'date': p.date.strftime('%Y-%m-%d'),
            'impressions': p.impressions,
            'clicks': p.clicks,
            'conversions': p.conversions,
            'spend': float(p.spend),
            'revenue': float(p.revenue),
            'ctr': (p.clicks / p.impressions * 100) if p.impressions > 0 else 0,
            'cpc': (p.spend / p.clicks) if p.clicks > 0 else 0
        } for p in performance_data]

class ContractService:
    @staticmethod
    def generate_contract_from_template(template_id, contract_data):
        """Generate contract content from template"""
        template = ContractTemplate.query.get(template_id)
        if not template:
            return None

        content = template.template_content

        # Replace variables in template
        for key, value in contract_data.items():
            placeholder = f"{{{{ {key} }}}}"
            content = content.replace(placeholder, str(value))

        return content

    @staticmethod
    def create_contract_version(contract_id, new_content, changes_description, user_id):
        """Create a new version of a contract"""
        contract = Contract.query.get(contract_id)
        if not contract:
            return None

        # Get latest version number
        latest_version = ContractVersion.query.filter_by(contract_id=contract_id).order_by(
            ContractVersion.version_number.desc()
        ).first()

        version_number = (latest_version.version_number + 1) if latest_version else 1

        version = ContractVersion(
            contract_id=contract_id,
            version_number=version_number,
            content=new_content,
            changes_description=changes_description,
            created_by=user_id
        )

        db.session.add(version)
        db.session.commit()

        return version

    @staticmethod
    def check_expiring_contracts(days_ahead=30):
        """Find contracts expiring within specified days"""
        expiry_date = datetime.utcnow().date() + timedelta(days=days_ahead)

        expiring_contracts = Contract.query.filter(
            Contract.expiry_date <= expiry_date,
            Contract.expiry_date >= datetime.utcnow().date(),
            Contract.status == 'active'
        ).all()

        return [{
            'contract_id': c.id,
            'contract_number': c.contract_number,
            'title': c.title,
            'party_b_name': c.party_b_name,
            'expiry_date': c.expiry_date.strftime('%Y-%m-%d'),
            'days_until_expiry': (c.expiry_date - datetime.utcnow().date()).days
        } for c in expiring_contracts]

class CurrencyService:
    @staticmethod
    def update_currency_rates():
        """Update currency exchange rates from external API"""
        # This would typically call a real API like Open Exchange Rates or Central Bank API
        # For demo purposes, we'll use static rates

        currencies = ['USD', 'EUR', 'RUB']
        base_rates = {
            'USD': 1.0,
            'EUR': 1.08,
            'RUB': 0.0098,
            'UZS': 0.000078
        }

        today = datetime.utcnow().date()

        # Update rates for UZS to other currencies
        for currency in currencies:
            # Check if rate already exists for today
            existing = CurrencyRate.query.filter_by(
                from_currency='UZS',
                to_currency=currency,
                date=today
            ).first()

            if not existing:
                rate = CurrencyRate(
                    from_currency='UZS',
                    to_currency=currency,
                    rate=1 / base_rates[currency],  # UZS to currency rate
                    date=today,
                    source='demo_rates'
                )
                db.session.add(rate)

        db.session.commit()
        return True

    @staticmethod
    def convert_currency(amount, from_currency, to_currency, date=None):
        """Convert amount between currencies"""
        if from_currency == to_currency:
            return amount

        if not date:
            date = datetime.utcnow().date()

        # Get exchange rate
        rate_record = CurrencyRate.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency,
            date=date
        ).first()

        if rate_record:
            return amount * rate_record.rate
        else:
            # Try reverse rate
            reverse_rate = CurrencyRate.query.filter_by(
                from_currency=to_currency,
                to_currency=from_currency,
                date=date
            ).first()

            if reverse_rate:
                return amount / reverse_rate.rate

        # If no rate found, return original amount
        return float(amount)

    @staticmethod
    def get_exchange_rate(from_currency, to_currency, date=None):
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return 1.0

        if not date:
            date = datetime.utcnow().date()

        # Get exchange rate from database
        rate_record = CurrencyRate.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency,
            date=date
        ).first()

        if rate_record:
            return rate_record.rate
        else:
            # Try reverse rate
            reverse_rate = CurrencyRate.query.filter_by(
                from_currency=to_currency,
                to_currency=from_currency,
                date=date
            ).first()

            if reverse_rate:
                return 1.0 / reverse_rate.rate

        # Return 1.0 as fallback (no conversion)
        return 1.0

    @staticmethod
    def format_currency(amount, currency_code):
        """Format currency amount with proper symbol"""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'RUB': '₽',
            'UZS': 'сўм',
            'KZT': '₸',
            'TRY': '₺',
            'GBP': '£',
            'CNY': '¥'
        }

        symbol = symbols.get(currency_code, currency_code)
        return f"{symbol}{amount:,.2f}"

    @staticmethod
    def update_currency_rates():
        """Update currency rates - placeholder for now"""
        # This would normally fetch rates from an API
        # For now, just return success
        return True

class TaxService:
    @staticmethod
    def calculate_tax(amount, tax_type, country='Uzbekistan', region=None):
        """Calculate tax amount based on type and location"""
        tax_rate = TaxRate.query.filter(
            TaxRate.country == country,
            TaxRate.tax_type == tax_type,
            TaxRate.is_active == True,
            or_(TaxRate.region == region, TaxRate.region.is_(None))
        ).order_by(TaxRate.effective_from.desc()).first()

        if tax_rate:
            return amount * (tax_rate.rate_percentage / 100)
        else:
            # Default rates if no specific rate found
            default_rates = {
                'vat': 15,  # Uzbekistan VAT rate
                'income_tax': 12,
                'corporate_tax': 20
            }
            rate = default_rates.get(tax_type, 0)
            return amount * (rate / 100)

    @staticmethod
    def get_tax_rates(country='Uzbekistan'):
        """Get all active tax rates for a country"""
        tax_rates = TaxRate.query.filter_by(
            country=country,
            is_active=True
        ).order_by(TaxRate.tax_type, TaxRate.effective_from.desc()).all()

        rates = {}
        for rate in tax_rates:
            if rate.tax_type not in rates:
                rates[rate.tax_type] = {
                    'rate': rate.rate_percentage,
                    'description': rate.description,
                    'effective_from': rate.effective_from.strftime('%Y-%m-%d')
                }

    @staticmethod
    def get_available_countries():
        """Get list of available countries for tax calculation"""
        return ['UZ', 'US', 'RU', 'KZ', 'TR']

    @staticmethod
    def get_tax_rate(country_code, business_type='retail'):
        """Get tax rate for a specific country and business type"""
        # Default tax rates by country
        default_rates = {
            'UZ': {'retail': 12.0, 'restaurant': 12.0, 'service': 12.0, 'manufacturing': 12.0, 'it': 12.0},
            'US': {'retail': 8.25, 'restaurant': 8.25, 'service': 8.25, 'manufacturing': 8.25, 'it': 8.25},
            'RU': {'retail': 20.0, 'restaurant': 20.0, 'service': 20.0, 'manufacturing': 20.0, 'it': 20.0},
            'KZ': {'retail': 12.0, 'restaurant': 12.0, 'service': 12.0, 'manufacturing': 12.0, 'it': 12.0},
            'TR': {'retail': 18.0, 'restaurant': 18.0, 'service': 18.0, 'manufacturing': 18.0, 'it': 18.0}
        }
        
        return default_rates.get(country_code, {}).get(business_type, 0.0)
