from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'producer', 'recycler', 'upcycler'
    location = db.Column(db.String(100))
    verified = db.Column(db.Boolean, default=False)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price_per_unit = db.Column(db.Float)
    unit = db.Column(db.String(20), default='kg')
    location = db.Column(db.String(100))
    posted_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='available')  # 'available', 'reserved', 'sold'

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float)
    transaction_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='pending')  # 'pending', 'shipped', 'completed'

class ImpactMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    co2_saved_kg = db.Column(db.Float)
    water_saved_liters = db.Column(db.Float)
    energy_saved_kwh = db.Column(db.Float)
    landfill_waste_reduced_kg = db.Column(db.Float)
    calculation_date = db.Column(db.DateTime, default=db.func.current_timestamp())