from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), default='buyer')
    location = db.Column(db.String(100))
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Material(db.Model):
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    quantity = db.Column(db.String(50))
    location = db.Column(db.String(100))
    price_per_unit = db.Column(db.Float)
    available = db.Column(db.Boolean, default=True)
    seller = db.Column(db.String(100), db.ForeignKey('users.company_name'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    transactions = db.relationship('Transaction', backref='material', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    category = db.Column(db.String(50))
    image = db.Column(db.String(200))
    stock = db.Column(db.Integer)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    rating = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'))
    quantity = db.Column(db.Float)
    total_price = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - Remove the impact_metrics relationship from here
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='purchases')
    seller = db.relationship('User', foreign_keys=[seller_id], backref='sales')
    # Remove: impact_metrics = db.relationship('ImpactMetric', backref='transaction', lazy=True)

class ImpactMetric(db.Model):
    __tablename__ = 'impact_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    
    # Map model attributes to actual database columns
    co2_saved_kg = db.Column(db.Float, default=0.0)
    water_saved_liters = db.Column(db.Float, default=0.0)
    energy_saved_kwh = db.Column(db.Float, default=0.0)
    landfill_waste_reduced_kg = db.Column(db.Float, default=0.0)
    
    # Additional fields
    calculation_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trees_saved = db.Column(db.Float, default=0.0)
    
    # Relationship
    transaction = db.relationship('Transaction', backref='impact_metrics')

    def calculate_trees_saved(self):
        if self.landfill_waste_reduced_kg:
            self.trees_saved = self.landfill_waste_reduced_kg / 10
        return self.trees_saved