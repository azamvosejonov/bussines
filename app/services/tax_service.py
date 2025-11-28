# Tax calculation service
class TaxService:
    # Tax rates by country and business type
    TAX_RATES = {
        'UZ': {
            'retail': 12.0,
            'restaurant': 12.0,
            'service': 12.0,
            'manufacturing': 12.0,
            'it': 12.0
        },
        'US': {
            'retail': 8.25,  # Average US sales tax
            'restaurant': 8.25,
            'service': 8.25,
            'manufacturing': 8.25,
            'it': 8.25
        },
        'RU': {
            'retail': 20.0,
            'restaurant': 20.0,
            'service': 20.0,
            'manufacturing': 20.0,
            'it': 20.0
        },
        'KZ': {
            'retail': 12.0,
            'restaurant': 12.0,
            'service': 12.0,
            'manufacturing': 12.0,
            'it': 12.0
        },
        'TR': {
            'retail': 18.0,
            'restaurant': 18.0,
            'service': 18.0,
            'manufacturing': 18.0,
            'it': 18.0
        }
    }

    @staticmethod
    def get_tax_rate(country_code, business_type='retail'):
        """Get tax rate for a specific country and business type"""
        if country_code in TaxService.TAX_RATES:
            if business_type in TaxService.TAX_RATES[country_code]:
                return TaxService.TAX_RATES[country_code][business_type]
        return 0.0

    @staticmethod
    def calculate_tax(amount, country_code, business_type='retail', custom_rate=None):
        """Calculate tax for an amount"""
        if custom_rate is not None:
            tax_rate = custom_rate
        else:
            tax_rate = TaxService.get_tax_rate(country_code, business_type)

        return (amount * tax_rate) / 100

    @staticmethod
    def calculate_total_with_tax(amount, country_code, business_type='retail', custom_rate=None):
        """Calculate total amount including tax"""
        tax_amount = TaxService.calculate_tax(amount, country_code, business_type, custom_rate)
        return amount + tax_amount

    @staticmethod
    def get_available_countries():
        """Get list of available countries for tax calculation"""
        return list(TaxService.TAX_RATES.keys())

    @staticmethod
    def get_business_types():
        """Get list of available business types"""
        return ['retail', 'restaurant', 'service', 'manufacturing', 'it']
