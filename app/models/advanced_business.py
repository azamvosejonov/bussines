from app import db
from datetime import datetime

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0.0)
    total_value = db.Column(db.Float, default=0.0)
    min_stock_level = db.Column(db.Integer, default=0)
    max_stock_level = db.Column(db.Integer, default=1000)
    location = db.Column(db.String(100))
    supplier = db.Column(db.String(100))
    qr_code_data = db.Column(db.Text)  # Store QR code data
    barcode = db.Column(db.String(100))
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='inventory_items')

    def generate_qr_data(self):
        """Generate QR code data for this inventory item"""
        return f"INV-{self.business_id}-{self.id}-{self.name}-{self.quantity}"

class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'adjustment'
    quantity = db.Column(db.Integer, nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200))
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    inventory_item = db.relationship('InventoryItem', backref='transactions')
    user = db.relationship('User', backref='inventory_transactions')

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # e.g., "Lavash"
    description = db.Column(db.Text)
    selling_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, default=0)  # Calculated from ingredients
    category = db.Column(db.String(50), default='food')  # food, drink, etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    business = db.relationship('Business', backref='recipes')

class RecipeIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Amount needed per recipe
    unit = db.Column(db.String(20), default='pieces')  # pieces, grams, ml, etc.

    # Relationships
    recipe = db.relationship('Recipe', backref='recipe_ingredients')
    product = db.relationship('Product', backref='recipe_ingredients')

class BusinessSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False, unique=True)
    currency = db.Column(db.String(10), default='UZS')
    timezone = db.Column(db.String(50), default='Asia/Tashkent')
    business_hours_start = db.Column(db.String(10), default='09:00')
    business_hours_end = db.Column(db.String(10), default='18:00')

    # Tax and bonus settings
    tax_rate = db.Column(db.Float, default=0.0)  # Percentage
    bonus_rate = db.Column(db.Float, default=0.0)  # Percentage for employees

    # Business type specific settings
    business_type = db.Column(db.String(50), default='retail')  # retail, restaurant, service, etc.
    allow_negative_stock = db.Column(db.Boolean, default=False)
    auto_calculate_profit = db.Column(db.Boolean, default=True)

    # Restaurant specific settings
    enable_recipes = db.Column(db.Boolean, default=False)
    enable_table_management = db.Column(db.Boolean, default=False)

    # Integration settings
    telegram_bot_enabled = db.Column(db.Boolean, default=False)
    email_notifications_enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserPreferences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    theme = db.Column(db.String(20), default='light')  # light, dark, custom
    background_image = db.Column(db.String(255))  # URL or path to background image
    background_color = db.Column(db.String(7), default='#ffffff')  # Hex color
    navbar_color = db.Column(db.String(7), default='#007bff')  # Bootstrap primary color
    nav_link_color = db.Column(db.String(7), default='#ffffff')  # Navigation link text color
    accent_color = db.Column(db.String(7), default='#28a745')  # Bootstrap success color
    custom_css = db.Column(db.Text)  # Custom CSS for advanced users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserPreferences user_id={self.user_id}>'
