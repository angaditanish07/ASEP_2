from flask import Flask, render_template, session, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from models import db, User, Material, Product, CartItem, Review, Transaction, ImpactMetric
from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/asep_2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'tanishangadi07@gmail.com'
app.config['MAIL_PASSWORD'] = 'dnko ajgn pzrw xvav'
app.config['MAIL_DEFAULT_SENDER'] = ('EcoExchange', 'tanishangadi07@gmail.com')

db.init_app(app)

mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'signin'


if __name__ == "__main__":
    # Remove test email sending from here to avoid sending on app start
    pass

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    return render_template('index.html', products=products)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter((User.email == email) | (User.company_name == email)).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('signin'))
        
        login_user(user, remember=remember)
        return redirect(url_for('home'))
    
    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        company_name = request.form.get('company') or request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('role') or 'buyer'
        location = request.form.get('location')
        
        user = User.query.filter((User.email == email) | (User.company_name == company_name)).first()
        if user:
            flash('User already exists')
            return redirect(url_for('signup'))
        
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

@app.route('/home')
@login_required
def home():
    stats = {
        'active_listings': Material.query.filter_by(seller=current_user.company_name, available=True).count(),
        'completed_transactions': Transaction.query.filter_by(buyer_id=current_user.id, status='completed').count(),
        'in_transit': Transaction.query.filter_by(buyer_id=current_user.id, status='shipped').count(),
        'co2_saved': (db.session.query(db.func.sum(ImpactMetric.co2_saved_kg))
                      .join(Transaction, ImpactMetric.transaction_id == Transaction.id)
                      .filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))
                      .scalar() or 0) / 1000,  # Convert to tons
        'max_listings': 20,
        'max_transactions': 50,
        'max_in_transit': 10,
        'max_co2': 100
    }

    recent_transactions = Transaction.query.filter(
        (Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.transaction_date.desc()).limit(5).all()

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

    impact = {
        'waste_diverted': db.session.query(db.func.sum(ImpactMetric.landfill_waste_reduced_kg))
                         .join(Transaction, ImpactMetric.transaction_id == Transaction.id)
                         .filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))
                         .scalar() or 0,
        'water_saved': db.session.query(db.func.sum(ImpactMetric.water_saved_liters))
                       .join(Transaction, ImpactMetric.transaction_id == Transaction.id)
                       .filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))
                       .scalar() or 0,
        'energy_saved': db.session.query(db.func.sum(ImpactMetric.energy_saved_kwh))
                        .join(Transaction, ImpactMetric.transaction_id == Transaction.id)
                        .filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))
                        .scalar() or 0,
        'trees_saved': int((db.session.query(db.func.sum(ImpactMetric.landfill_waste_reduced_kg))
                         .join(Transaction, ImpactMetric.transaction_id == Transaction.id)
                         .filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))
                         .scalar() or 0) / 10000)  # Approx 10kg of paper per tree
    }

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

    # --- Chart Data for Dashboard ---
    # Transactions over time (last 6 months)
    from sqlalchemy import extract
    from collections import OrderedDict
    import calendar
    import datetime as dt
    now = dt.datetime.now()
    months = [(now - dt.timedelta(days=30*i)).strftime('%Y-%m') for i in reversed(range(6))]
    month_labels = [calendar.month_abbr[int(m.split('-')[1])] + ' ' + m.split('-')[0][2:] for m in months]
    transaction_counts = []
    for m in months:
        year, month = int(m.split('-')[0]), int(m.split('-')[1])
        count = Transaction.query.filter(
            ((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)),
            extract('year', Transaction.transaction_date) == year,
            extract('month', Transaction.transaction_date) == month
        ).count()
        transaction_counts.append(count)
    chart_transactions = {'labels': month_labels, 'data': transaction_counts}

    # Material categories pie chart
    category_counts = db.session.query(Material.category, db.func.count(Material.id)).filter_by(seller=current_user.company_name).group_by(Material.category).all()
    chart_categories = {
        'labels': [c[0] or 'Uncategorized' for c in category_counts],
        'data': [c[1] for c in category_counts]
    }

    # Goal progress (example: % of 50 completed transactions)
    goal_progress = min(100, int((stats['completed_transactions'] / 50) * 100))

    return render_template('dashboard.html',
                         stats=stats,
                         recent_transactions=formatted_transactions,
                         impact=impact,
                         recommendations=recommendations,
                         chart_transactions=chart_transactions,
                         chart_categories=chart_categories,
                         goal_progress=goal_progress,
                         current_year=datetime.now().year)

@app.route('/marketplace')
@login_required
def marketplace():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    total_materials = Material.query.filter_by(available=True).count()
    materials = Material.query.filter_by(available=True).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total_materials + per_page - 1) // per_page
    return render_template('marketplace.html', materials=materials, page=page, total_pages=total_pages)

@app.route('/tracking')
@login_required
def tracking():
    shipments = Transaction.query.filter(
        ((Transaction.buyer_id == current_user.id) | 
         (Transaction.seller_id == current_user.id)),
        Transaction.status.in_(['shipped', 'in_transit'])
    ).all()
    return render_template('material_tracking.html', shipments=shipments)

@app.route('/materials')
@login_required
def materials():
    user_materials = Material.query.filter_by(seller=current_user.company_name).all()
    return render_template('my_materials.html', materials=user_materials)

@app.route('/material/<int:material_id>')
@login_required
def material_detail(material_id):
    material = Material.query.get_or_404(material_id)
    similar_materials = Material.query.filter(Material.name == material.name, Material.id != material.id).all()
    return render_template('material_detail.html', material=material, similar_materials=similar_materials)

@app.route('/transactions')
@login_required
def transactions():
    user_transactions = Transaction.query.filter(
        (Transaction.buyer_id == current_user.id) | 
        (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.transaction_date.desc()).all()
    return render_template('transactions.html', transactions=user_transactions)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/material/add', methods=['GET', 'POST'])
@login_required
def add_material():
    if request.method == 'POST':
        try:
            quantity_value = request.form.get('quantity')
            quantity_unit = request.form.get('unit')
            combined_quantity = f"{quantity_value} {quantity_unit}"
            
            new_material = Material(
                name=request.form.get('name'),
                category=request.form.get('category'),
                quantity=combined_quantity,
                location=request.form.get('location'),
                price_per_unit=float(request.form.get('price')),
                available=True,
                seller=current_user.company_name
            )
            
            db.session.add(new_material)
            db.session.commit()
            
            flash('Material successfully listed!', 'success')
            return redirect(url_for('marketplace'))
            
        except ValueError as e:
            flash('Invalid number input: ' + str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash('Error adding material: ' + str(e), 'danger')
            return redirect(request.url)
    
    return render_template('add_material.html')

@app.route('/material/<int:material_id>/request', methods=['POST'])
@login_required
def request_material(material_id):
    material = Material.query.get(material_id)
    if not material:
        abort(404)
    if not material.available:
        flash('This material is not currently available', 'warning')
        return redirect(url_for('marketplace'))

    seller_user = User.query.filter_by(company_name=material.seller).first()
    if seller_user and seller_user.email:
        try:
            app.logger.info("Material request route triggered")
            quantity_requested = request.form.get('quantity')
            message_body = request.form.get('message') or ''
            delivery_date = request.form.get('delivery_date') or 'Not specified'

            # Use constant test email for all requests
            test_email = "tanish.angadi241@vit.edu"

            msg = Message(
                subject=f"New Material Request: {material.name}",
                recipients=[test_email]
            )
            msg.body = f"""
Hello Seller,

You have received a new request for your material listing with the following details:

Material Name: {material.name}
Quantity Needed: {quantity_requested}
Required By: {delivery_date}
Requested By: {current_user.company_name} (Email: {current_user.email})

Message from Buyer:
{message_body}

Please contact the buyer to proceed with the transaction.

Best regards,
EcoExchange Team
"""
            try:
                mail.send(msg)
                app.logger.info("Email sent to test email successfully")
                flash('Your request has been sent to the test email.', 'success')
            except Exception as send_error:
                app.logger.error(f"Failed to send email: {str(send_error)}")
                flash(f'Failed to send email: {str(send_error)}', 'danger')
        except Exception as e:
            app.logger.error(f"Failed to send email to the test email: {str(e)}")
            flash(f'Failed to send email to the test email: {str(e)}', 'danger')
    else:
        flash('Seller email not found. Request not sent via email.', 'warning')

    return redirect(url_for('marketplace'))

@app.route('/transaction/<int:transaction_id>/dispatch', methods=['POST'])
@login_required
def dispatch_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return {"error": "Transaction not found"}, 404
    if transaction.seller_id != current_user.id:
        return {"error": "Unauthorized"}, 403
    try:
        transaction.status = 'shipped'
        from datetime import datetime
        transaction.transaction_date = datetime.utcnow()
        db.session.commit()
        return {"message": "Transaction marked as dispatched"}, 200
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}, 500

@app.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.user_type not in ['seller', 'admin']:
        flash('You need to be a seller to add products', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        stock = int(request.form.get('stock'))
        
        if 'image' not in request.files:
            flash('No image uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '' or not allowed_file(file.filename):
            flash('Invalid image file', 'danger')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        product = Product(
            name=name,
            description=description,
            price=price,
            category=category,
            image=filepath,
            stock=stock,
            seller_id=current_user.id
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_product.html')

@app.route('/add-review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    product = Product.query.get(product_id)
    if not product:
        abort(404)
    
    content = request.form.get('content')
    rating = int(request.form.get('rating'))
    
    review = Review(
        content=content,
        rating=rating,
        user_id=current_user.id,
        product_id=product_id
    )
    
    db.session.add(review)
    db.session.commit()
    
    flash('Review added!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get(product_id)
    if not product:
        abort(404)
    reviews = Review.query.filter_by(product_id=product_id).all()
    return render_template('product_detail.html', product=product, reviews=reviews)

@app.route('/impact')
@login_required
def impact():
    try:
        # Get impact metrics through transaction relationships
        monthly_impact = db.session.query(
            db.func.date_format(ImpactMetric.calculation_date, '%Y-%m').label('month'),
            db.func.sum(ImpactMetric.co2_saved_kg).label('co2_saved'),
            db.func.sum(ImpactMetric.landfill_waste_reduced_kg).label('waste_reduced'),
            db.func.sum(ImpactMetric.water_saved_liters).label('water_saved'),
            db.func.sum(ImpactMetric.energy_saved_kwh).label('energy_saved')
        ).join(
            Transaction, Transaction.id == ImpactMetric.transaction_id
        ).filter(
            (Transaction.buyer_id == current_user.id) | 
            (Transaction.seller_id == current_user.id)
        ).group_by('month').order_by('month').all()

        # Convert to chart data
        months = [imp.month for imp in monthly_impact] if monthly_impact else []
        chart_data = {
            'co2': [imp.co2_saved/1000 for imp in monthly_impact] if monthly_impact else [0],
            'waste': [imp.waste_reduced for imp in monthly_impact] if monthly_impact else [0],
            'water': [imp.water_saved for imp in monthly_impact] if monthly_impact else [0],
            'energy': [imp.energy_saved for imp in monthly_impact] if monthly_impact else [0]
        }

        # Get top materials by impact
        top_materials = db.session.query(
            Material.name,
            db.func.sum(ImpactMetric.co2_saved_kg).label('total_co2')
        ).join(
            Transaction, Transaction.id == ImpactMetric.transaction_id
        ).join(
            Material, Material.id == Transaction.material_id
        ).filter(
            (Transaction.buyer_id == current_user.id) | 
            (Transaction.seller_id == current_user.id)
        ).group_by(
            Material.name
        ).order_by(
            db.desc('total_co2')
        ).limit(5).all()

        return render_template('impact.html', 
                            months=months,
                            chart_data=chart_data,
                            top_materials=top_materials)

    except Exception as e:
        app.logger.error(f"Error in impact route: {str(e)}")
        # Return empty data structure if there's an error
        return render_template('impact.html', 
                            months=[],
                            chart_data={'co2': [0], 'waste': [0], 'water': [0], 'energy': [0]},
                            top_materials=[])
    
@app.route('/reports')
@login_required
def reports():
    report_types = [
        {'id': 'co2', 'name': 'CO₂ Savings Report', 'icon': 'leaf'},
        {'id': 'waste', 'name': 'Waste Diversion Report', 'icon': 'recycle'},
        {'id': 'water', 'name': 'Water Savings Report', 'icon': 'tint'},
        {'id': 'energy', 'name': 'Energy Savings Report', 'icon': 'bolt'},
        {'id': 'full', 'name': 'Comprehensive Impact Report', 'icon': 'chart-bar'}
    ]
    
    time_periods = [
        {'id': '7d', 'name': 'Last 7 Days'},
        {'id': '30d', 'name': 'Last 30 Days'},
        {'id': '90d', 'name': 'Last Quarter'},
        {'id': '1y', 'name': 'Last Year'},
        {'id': 'all', 'name': 'All Time'}
    ]
    
    return render_template('reports.html',
                         report_types=report_types,
                         time_periods=time_periods)

@app.route('/generate-report', methods=['POST'])
@login_required
def generate_report():
    report_type = request.form.get('report_type')
    time_period = request.form.get('time_period')
    
    end_date = datetime.utcnow()
    if time_period == '7d':
        start_date = end_date - timedelta(days=7)
    elif time_period == '30d':
        start_date = end_date - timedelta(days=30)
    elif time_period == '90d':
        start_date = end_date - timedelta(days=90)
    elif time_period == '1y':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = datetime.min  # All time
    
    report_data = {}
    if report_type in ['co2', 'full']:
        co2_data = db.session.query(
            db.func.sum(ImpactMetric.co2_saved_kg)
        ).join(
            Transaction, Transaction.id == ImpactMetric.transaction_id
        ).filter(
            ((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)),
            ImpactMetric.created_at.between(start_date, end_date)
        ).scalar() or 0
        report_data['co2_saved_tons'] = co2_data / 1000
    
    if report_type in ['waste', 'full']:
        waste_data = db.session.query(
            db.func.sum(ImpactMetric.landfill_waste_reduced_kg)
        ).join(
            Transaction, Transaction.id == ImpactMetric.transaction_id
        ).filter(
            ((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)),
            ImpactMetric.created_at.between(start_date, end_date)
        ).scalar() or 0
        report_data['waste_diverted_kg'] = waste_data

    return render_template('report_template.html',
                         report_type=report_type,
                         time_period=time_period,
                         data=report_data,
                         current_time=datetime.now())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
