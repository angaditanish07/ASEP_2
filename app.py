from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user, UserMixin, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///circular_economy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'signin'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
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
    status = db.Column(db.String(20), default='available')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float)
    transaction_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    status = db.Column(db.String(20), default='pending')

class ImpactMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    co2_saved_kg = db.Column(db.Float)
    water_saved_liters = db.Column(db.Float)
    energy_saved_kwh = db.Column(db.Float)
    landfill_waste_reduced_kg = db.Column(db.Float)
    calculation_date = db.Column(db.DateTime, default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/home')
@login_required
def home():
    stats = {
        'active_listings': Material.query.filter_by(user_id=current_user.id, status='available').count(),
        'completed_transactions': Transaction.query.filter_by(buyer_id=current_user.id, status='completed').count(),
        'in_transit': Transaction.query.filter_by(buyer_id=current_user.id, status='shipped').count(),
        'co2_saved': (ImpactMetric.query.with_entities(db.func.sum(ImpactMetric.co2_saved_kg))
                      .filter_by(user_id=current_user.id).scalar() or 0) / 1000,  # Convert to tons
        'max_listings': 20,
        'max_transactions': 50,
        'max_in_transit': 10,
        'max_co2': 100
    }
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter(
        (Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.transaction_date.desc()).limit(5).all()
    
    # Format recent transactions for template
    formatted_transactions = []
    for t in recent_transactions:
        material = Material.query.get(t.material_id)
        partner = User.query.get(t.seller_id if t.buyer_id == current_user.id else t.buyer_id)
        formatted_transactions.append({
            'material_name': material.name if material else 'Unknown Material',
            'partner_name': partner.company_name if partner else 'Unknown Partner',
            'date': t.transaction_date,
            'status': t.status,
            'amount': t.total_price or 0
        })
    
    # Get impact metrics
    impact = {
        'waste_diverted': ImpactMetric.query.with_entities(db.func.sum(ImpactMetric.landfill_waste_reduced_kg))
                         .filter_by(user_id=current_user.id).scalar() or 0,
        'water_saved': ImpactMetric.query.with_entities(db.func.sum(ImpactMetric.water_saved_liters))
                       .filter_by(user_id=current_user.id).scalar() or 0,
        'energy_saved': ImpactMetric.query.with_entities(db.func.sum(ImpactMetric.energy_saved_kwh))
                        .filter_by(user_id=current_user.id).scalar() or 0,
        'trees_saved': int((ImpactMetric.query.with_entities(db.func.sum(ImpactMetric.landfill_waste_reduced_kg))
                         .filter_by(user_id=current_user.id).scalar() or 0) / 10000)  # Approx 10kg of paper per tree
    }
    
    # Generate AI recommendations
    recommendations = [
        {
            'type': 'buy',
            'material_name': 'HDPE Plastic Scraps',
            'quantity': 1200,
            'distance': 25,
            'price_per_kg': 0.35,
            'match_score': 0.87
        },
        {
            'type': 'sell',
            'material_name': 'Aluminum Waste',
            'quantity': 800,
            'distance': 15,
            'price_per_kg': 1.20,
            'match_score': 0.78
        },
        {
            'type': 'buy',
            'material_name': 'Cardboard Waste',
            'quantity': 2500,
            'distance': 42,
            'price_per_kg': 0.15,
            'match_score': 0.65
        }
    ]
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_transactions=formatted_transactions,
                         impact=impact,
                         recommendations=recommendations,
                         current_year=datetime.datetime.now().year)

# Auth Routes
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('signin'))
        
        login_user(user, remember=remember)
        return redirect(url_for('home'))
    
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form.get('company')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('role')
        location = request.form.get('location')
        
        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists')
            return redirect(url_for('signup'))
        
        # Create new user
        new_user = User(
            company_name=company_name,
            email=email,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            user_type=user_type,
            location=location,
            verified=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('signin'))
    
    return render_template('signup.html')

# Add these with your existing routes
@app.route('/marketplace')
@login_required
def marketplace():
    materials = Material.query.filter(Material.user_id != current_user.id, 
                                    Material.status == 'available').all()
    return render_template('marketplace.html', materials=materials)

@app.route('/materials')
@login_required
def materials():
    user_materials = Material.query.filter_by(user_id=current_user.id).all()
    return render_template('materials.html', materials=user_materials)

@app.route('/transactions')
@login_required
def transactions():
    user_transactions = Transaction.query.filter(
        (Transaction.buyer_id == current_user.id) | 
        (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.transaction_date.desc()).all()
    return render_template('transactions.html', transactions=user_transactions)

@app.route('/tracking')
@login_required
def tracking():
    shipments = Transaction.query.filter(
        ((Transaction.buyer_id == current_user.id) | 
         (Transaction.seller_id == current_user.id)),
        Transaction.status.in_(['shipped', 'in_transit'])
    ).all()
    return render_template('tracking.html', shipments=shipments)

@app.route('/impact')
@login_required
def impact():
    metrics = ImpactMetric.query.filter_by(user_id=current_user.id).all()
    return render_template('impact.html', metrics=metrics)

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

# Profile Route 
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)