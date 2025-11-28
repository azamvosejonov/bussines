import requests
from datetime import datetime, timedelta
from app import db
from app.models import CurrencyRate

class CurrencyService:
    # Base URL for currency exchange API (you can use a free API like exchangerate-api.com)
    API_BASE_URL = "https://api.exchangerate-api.com/v4/latest/USD"

    # Supported currencies
    SUPPORTED_CURRENCIES = ['USD', 'EUR', 'RUB', 'UZS', 'KZT', 'TRY', 'GBP', 'CNY']

    @staticmethod
    def get_exchange_rate(from_currency, to_currency):
        """Get exchange rate between two currencies"""
        try:
            # Check if we have recent rates in database (within last hour)
            recent_rate = CurrencyRate.query.filter_by(
                from_currency=from_currency,
                to_currency=to_currency
            ).filter(
                CurrencyRate.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).first()

            if recent_rate:
                return recent_rate.rate

            # Fetch from API
            response = requests.get(CurrencyService.API_BASE_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                usd_rates = data.get('rates', {})

                # Calculate cross rate
                if from_currency == 'USD':
                    rate = usd_rates.get(to_currency, 1.0)
                elif to_currency == 'USD':
                    rate = 1.0 / usd_rates.get(from_currency, 1.0)
                else:
                    # Cross rate calculation
                    from_rate = usd_rates.get(from_currency, 1.0)
                    to_rate = usd_rates.get(to_currency, 1.0)
                    rate = to_rate / from_rate

                # Save to database
                currency_rate = CurrencyRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    date=datetime.utcnow().date(),
                    source='API'
                )
                db.session.add(currency_rate)
                db.session.commit()

                return rate

        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
            db.session.rollback()  # Rollback on error

        return 1.0  # Fallback to 1:1 rate

    @staticmethod
    def convert_currency(amount, from_currency, to_currency):
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount

        rate = CurrencyService.get_exchange_rate(from_currency, to_currency)
        return amount * rate

    @staticmethod
    def update_currency_rates():
        """Update all currency rates"""
        try:
            response = requests.get(CurrencyService.API_BASE_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                usd_rates = data.get('rates', {})

                # Update rates for common currency pairs
                pairs = [
                    ('USD', 'EUR'), ('USD', 'RUB'), ('USD', 'UZS'),
                    ('USD', 'KZT'), ('USD', 'TRY'), ('EUR', 'RUB'),
                    ('EUR', 'UZS'), ('RUB', 'UZS')
                ]

                for from_curr, to_curr in pairs:
                    try:
                        if from_curr == 'USD':
                            rate = usd_rates.get(to_curr, 1.0)
                        elif to_curr == 'USD':
                            rate = 1.0 / usd_rates.get(from_curr, 1.0)
                        else:
                            from_rate = usd_rates.get(from_curr, 1.0)
                            to_rate = usd_rates.get(to_curr, 1.0)
                            rate = to_rate / from_rate

                        # Check if rate exists
                        existing = CurrencyRate.query.filter_by(
                            from_currency=from_curr,
                            to_currency=to_curr
                        ).first()

                        if existing:
                            existing.rate = rate
                        else:
                            new_rate = CurrencyRate(
                                from_currency=from_curr,
                                to_currency=to_curr,
                                rate=rate,
                                date=datetime.utcnow().date(),
                                source='API'
                            )
                            db.session.add(new_rate)

                    except Exception as e:
                        print(f"Error updating {from_curr} to {to_curr}: {e}")
                        continue

                db.session.commit()
                print("✅ Currency rates updated successfully")

        except Exception as e:
            print(f"❌ Error updating currency rates: {e}")
            db.session.rollback()  # Rollback on error

    @staticmethod
    def get_supported_currencies():
        """Get list of supported currencies"""
        return CurrencyService.SUPPORTED_CURRENCIES

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
