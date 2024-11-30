import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns


curr_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///household.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '1234567890'
app.config['PASSWORD_HASH'] = 'sha237_crypt'

app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['UPLOAD_PATH'] = os.path.join(curr_dir, 'static', 'pdfs')

db = SQLAlchemy(app)  # Initialize SQLAlchemy with the app

# db.init_app(app)
app.app_context().push()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_customer = db.Column(db.Boolean, default=False)
    is_professional = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    avg_rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    professional_profile = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)
    is_blocked = db.Column(db.Boolean, default=False)  # New field for block/unblock status
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='SET NULL'), nullable=True)
    

    # Relationships
    service = db.relationship('Service', back_populates='professionals')
    customer_requests = db.relationship('ServiceRequest', back_populates='customer', foreign_keys='ServiceRequest.customer_id', cascade='all, delete-orphan')
    professional_requests = db.relationship('ServiceRequest', back_populates='professional', foreign_keys='ServiceRequest.professional_id', cascade='all, delete-orphan')


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Float, nullable=False)
    estimated_duration = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(255), nullable=True)

    # Relationships
    professionals = db.relationship('User', back_populates='service', cascade='all, delete')
    requests = db.relationship('ServiceRequest', back_populates='service', cascade='all, delete')


class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    request_type = db.Column(db.String(15), nullable=False)  # public/private
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(25), nullable=True)  # pending/accepted/closed/rejected
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.now().date())
    closed_on = db.Column(db.DateTime, nullable=True)
    customer_rating = db.Column(db.Float, default=0.0)
    customer_feedback = db.Column(db.Text, nullable=True)

    # Relationships
    service = db.relationship('Service', back_populates='requests')
    customer = db.relationship('User', back_populates='customer_requests', foreign_keys=[customer_id])
    professional = db.relationship('User', back_populates='professional_requests', foreign_keys=[professional_id])


# Admin creation logic
def setup_admin_account():
    with app.app_context():
        admin_exists = User.query.filter_by(is_admin=True).first()
        if not admin_exists:
            new_admin = User(username='admin', password=generate_password_hash('admin123'), is_admin=True, is_verified=True)
            db.session.add(new_admin)
            db.session.commit()
            print('Admin account initialized successfully.')

# Initialize the database and check for admin creation
with app.app_context():
    db.create_all()
    setup_admin_account()


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = User.query.filter_by(is_admin=True).first()
        # admin is a sqlalchemy object

        if admin and check_password_hash(admin.password, password):
            session['username'] = username
            session['is_admin'] = True
            flash('Logged in successfully.', category='success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

# creating route for admin dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    services = Service.query.all()
    requests = ServiceRequest.query.all()
    unauthorized_professionals = User.query.filter_by(is_professional=True, is_verified=False).all()
    return render_template('admin_dashboard.html', services=services, requests=requests, unauthorized_professionals=unauthorized_professionals, admin_name=session['username'])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']  # Get the username from the form
        password = request.form['password']  # Get the password from the form

        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and verify the password
        if user and check_password_hash(user.password, password):
            # Check if the user is blocked
            if user.is_blocked:
                flash("Your account has been blocked. Please contact support.", "danger")
                return redirect("/login")

            # Store user session information
            session['id'] = user.id
            session['is_professional'] = user.is_professional
            session['is_customer'] = user.is_customer
            session['username'] = user.username

            # Logic for professionals
            if user.is_professional:
                user_type = 'professional'

                # Check if the professional is approved by admin
                if not user.is_verified:
                    flash("Please wait for admin approval", "danger")
                    return redirect("/login")

                # Check if the professional is linked to any service
                if user.service_id is None:
                    flash("No service linked to your account. Please register with another service.", "danger")
                    return redirect("/login")

                return redirect(f"/{user_type}_dashboard")

            # Logic for customers
            if user.is_customer:
                user_type = 'customer'
                flash("Login successful!", "success")
                return redirect(f"/{user_type}_dashboard")

        # If login fails
        flash("Login failed. Please check your username and password.", "danger")
        return redirect("/login")

    # Render the login page if method is GET
    return render_template("login.html")


# creating route for professional registration
@app.route('/professional_register', methods=['GET', 'POST'])
def professional_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        address = request.form['address']
        pincode = request.form['pincode']
        email = request.form['email']
        phone_number = request.form['phone_number']
        professional_profile = request.files['professional_profile']
        experience = request.form['experience']
        service = request.form['service']
        service_id = Service.query.filter_by(name=service).first().id

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different username.', category='danger')
            return redirect(url_for('professional_register'))
        file_name = secure_filename(professional_profile.filename) # profile .pdf file name
        if file_name != '':
            file_ext = os.path.splitext(file_name)[1]
            renamed_file_name = username + file_ext
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                abort (400)
            professional_profile.save(os.path.join(app.config['UPLOAD_PATH'], renamed_file_name))
        user = User(username=username, password=generate_password_hash(password), email=email, phone_number=phone_number, address=address, pincode=pincode, professional_profile=renamed_file_name, is_professional=True, service_id=service_id, experience=experience, is_verified=False)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please login now.', category='success')
        return redirect(url_for('login'))
    services = Service.query.all()
    return render_template('professional_register.html', services=services)

# creating route for customer registration
@app.route('/customer_register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        address = request.form['address']
        pincode = request.form['pincode']
        email = request.form['email']
        phone_number = request.form['phone_number']

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different username.', category='danger')
            return redirect(url_for('customer_register'))
        user = User(username=username, password=generate_password_hash(password), email=email, phone_number=phone_number, address=address, pincode=pincode, is_customer=True, is_verified=True)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please login now.', category='success')
        return redirect(url_for('login'))
    return render_template('customer_register.html')

# creating route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('is_admin', None)
    session.pop('is_professional', None)
    session.pop('is_customer', None)
    flash('Logged out successfully.', category='success')
    return redirect(url_for('home'))



@app.route('/admin_dashboard/create_service', methods=['GET', 'POST'])
def create_service():
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        base_price = request.form['base_price']
        estimated_duration = request.form['estimated_duration']
        location = request.form['location']
        
        new_service = Service(name=name, description=description, base_price=base_price, estimated_duration=estimated_duration, location=location)
        db.session.add(new_service)
        db.session.commit()
        flash('Service created successfully.', category='success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_service.html')

@app.route('/admin_dashboard/edit_service/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        service.name = request.form['name']
        service.description = request.form['description']
        service.base_price = request.form['base_price']
        service.estimated_duration = request.form['estimated_duration']
        db.session.commit()
        flash('Service updated successfully.', category='success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_service.html', service=service)

@app.route('/admin_dashboard/delete_service/<int:service_id>', methods=['GET', 'POST'])
def delete_service(service_id):
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    service = Service.query.get_or_404(service_id)
    verified_professionals = User.query.filter_by(is_professional=True, is_verified=True, service_id=service_id).all()
    for professional in verified_professionals:
        professional.is_verified = False
    db.session.delete(service)
    db.session.commit()
    flash('Service removed successfully.', category='success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin_dashboard/view_professional_info/<int:professional_id>', methods=['GET', 'POST'])
def view_professional_info(professional_id):
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    professional = User.query.get_or_404(professional_id)
    return render_template('view_professional_info.html', professional=professional)

@app.route('/admin_dashboard/approve_professional/<int:professional_id>', methods=['GET', 'POST'])
def approve_professional(professional_id):
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    professional = User.query.get_or_404(professional_id)
    professional.is_verified = True
    db.session.commit()
    flash('Professional approved successfully.', category='success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard/reject_professional/<int:professional_id>', methods=['GET', 'POST'])
def reject_professional(professional_id):
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    professional = User.query.get_or_404(professional_id)
    pdf_file = professional.professional_profile
    if pdf_file:
        path_file = os.path.join(app.config['UPLOAD_PATH'], pdf_file)
        if os.path.exists(path_file):
            try:
                os.remove(path_file)
                print('File has been deleted successfully')
            except Exception as e:
                print(f'Error deleting file: {e}')
        else:
            print('File not found')
    professional.is_verified = False
    db.session.delete(professional)
    db.session.commit()
    flash('Professional has been rejected successfully.', category='success')
    return redirect(url_for('admin_dashboard'))

@app.route('/professional_dashboard', methods=['GET', 'POST'])
def professional_dashboard():
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    
    professional_id = User.query.filter_by(username=session['username']).first().id
    professional = User.query.get(professional_id)
    
    if professional.is_verified == False:
        flash('Please wait for admin to approve your account.', category='danger')
        return redirect(url_for('login'))
    
    # Fetching the pending, completed, and closed requests
    pending_requests = ServiceRequest.query.filter_by(professional_id=professional_id, status='pending', request_type="private").all()
    completed_requests = ServiceRequest.query.filter_by(professional_id=professional_id, status='accepted').all()
    closed_requests = ServiceRequest.query.filter_by(professional_id=professional_id, status='closed').all()
    
    # Fetch the top 5 reviews based on customer ratings (highest first)
    top_reviews = ServiceRequest.query.filter_by(professional_id=professional_id).order_by(ServiceRequest.customer_rating.desc()).limit(5).all()
    
    return render_template(
        'professional_dashboard.html',
        professional=professional,
        pending_requests=pending_requests,
        completed_requests=completed_requests,
        closed_requests=closed_requests,
        top_reviews=top_reviews,
        professional_name=session['username']
    )


# creating route for Customer Dashboard

@app.route('/customer_dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    customer = User.query.filter_by(username = session['username']).first()
    services = Service.query.join(User).filter(User.is_verified == True).all()
    service_history = ServiceRequest.query.filter_by(customer_id = customer.id).filter(ServiceRequest.professional_id != None).all()
    return render_template('customer_dashboard.html', customer=customer, customer_name = session['username'], services=services, service_history=service_history)

# creating route to create a service request by customer in a service
@app.route('/customer_dashboard/create_request/<int:service_id>', methods=['GET', 'POST'])
def create_request(service_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    # service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        professional = request.form.get('professional')
        description = request.form.get('description')
        professional_id = User.query.filter_by(username=professional).first().id
        customer = User.query.filter_by(username = session['username']).first()
        new_request = ServiceRequest(service_id=service_id, customer_id=customer.id, 
                        professional_id=professional_id, description=description, request_type="private", status="pending")
        db.session.add(new_request)
        db.session.commit()
        flash('Service request created successfully.', category='success')
        return redirect(url_for('customer_dashboard'))
    service = Service.query.get_or_404(service_id)
    professional = User.query.filter_by(is_professional=True, is_verified=True, service_id=service_id).all()
    return render_template('create_request.html', service=service, professional=professional)

# creating a route for editing a service request
@app.route('/customer_dashboard/edit_request/<int:request_id>', methods=['GET', 'POST'])
def edit_request(request_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))

    # Fetch the service request from the database
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # Handle form submission
    if request.method == 'POST':
        description = request.form.get('description')
        service_request.description = description
        db.session.commit()
        flash('Service request updated successfully.', category='success')
        return redirect(url_for('customer_dashboard'))

    return render_template('edit_request.html', service_request=service_request)

# edit it later to prevent editing by customer

# creating a route for deleting a service request
@app.route('/customer_dashboard/delete_request/<int:request_id>', methods=['GET', 'POST'])
def delete_request(request_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    request = ServiceRequest.query.get_or_404(request_id)
    db.session.delete(request)
    db.session.commit()
    flash('Service request deleted successfully.', category='success')
    return redirect(url_for('customer_dashboard'))

# creating route for customer dashboard for search service
@app.route('/customer_dashboard/customer_search', methods=['GET', 'POST'])
def customer_search():
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    search_type = request.args.get('search_type')
    search_query = request.args.get('search_query')

    if search_query:
        if search_type == 'pincode':
            services = Service.query.join(User).filter(User.is_verified == True, User.pincode.like(f'%{search_query}%')).all()
        elif search_type == 'service_name':
            services = Service.query.filter(Service.name.like(f'%{search_query}%')).all()
        elif search_type == 'address':
            services = Service.query.join(User).filter(User.is_verified == True, User.address.like(f'%{search_query}%')).all()
    else:
        services = Service.query.join(User).filter(User.is_verified == True).all()
    return render_template('customer_search.html', services=services, customer_name=session['username'])

# ruote for view professional profile
@app.route('/customer_dashboard/view_professional/<int:professional_id>', methods=['GET', 'POST'])
def view_professional(professional_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    new_professional = User.query.get_or_404(professional_id)
    reviews = ServiceRequest.query.filter_by(professional_id=professional_id, status="closed").all()
    return render_template('professional_profile.html', new_professional=new_professional, reviews=reviews, customer_name=session['username'])

# route for accepting service request in professional dashboard
@app.route('/professional_dashboard/accept_request/<int:request_id>', methods=['GET', 'POST'])
def accept_request(request_id):
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    new_request = ServiceRequest.query.get_or_404(request_id)
    new_request.status = "accepted"
    db.session.commit()
    flash('Service request accepted successfully.', category='success')
    return redirect(url_for('professional_dashboard'))

# route for rejecting service request in professional dashboard
@app.route('/professional_dashboard/reject_request/<int:request_id>', methods=['GET', 'POST'])
def reject_request(request_id):
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    new_request = ServiceRequest.query.get_or_404(request_id)
    new_request.status = "rejected"
    db.session.commit()
    flash('Service request rejected successfully.', category='danger')
    return redirect(url_for('professional_dashboard'))

# route for closing service request in customer dashboard
@app.route('/customer_dashboard/close_request/<int:request_id>', methods=['GET', 'POST'])
def close_request(request_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    
    new_request = ServiceRequest.query.get_or_404(request_id)
    if not new_request:
        flash('Service request not found.', category='danger')
        return redirect(url_for('customer_dashboard'))
    if request.method == 'POST':
        feedback = request.form.get('feedback')
        rating = request.form.get('rating')

        new_request.status = 'closed'
        new_request.customer_feedback = feedback
        new_request.customer_rating = float(rating)
        new_request.closed_on = datetime.now().date()

        pro_feedback_update = User.query.get(new_request.professional_id)
        temp = pro_feedback_update.rating_count
        pro_feedback_update.rating_count = temp + 1
        pro_feedback_update.avg_rating = (pro_feedback_update.avg_rating*temp + float(rating)) / pro_feedback_update.rating_count
        db.session.commit()
        flash('Service request closed successfully.', category='success')
        return redirect(url_for('customer_dashboard'))

    professional = new_request.professional.username
    service = new_request.service.name
    return render_template('close_request.html', professional=professional, service=service, request_id=request_id, customer_name=session['username'])

# create route for sending open requests in a particular service by customer to all professionals in that service in customer dashboard
@app.route('/customer_dashboard/create_open_request/<int:service_id>', methods=['GET'])
def create_open_request(service_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    
    customer_id = User.query.filter_by(username=session['username']).first().id
    open_request = ServiceRequest(service_id=service_id, customer_id=customer_id, request_type="public", status="pending")
    db.session.add(open_request)
    db.session.commit()
    flash('Open service request created successfully and sent to all professionals of the service.', category='success')
    return redirect(url_for('customer_dashboard'))

# create route to show open requests sent by customer to professionals in professional dashboard
@app.route('/professional_dashboard/open_requests', methods=['GET', 'POST'])
def open_requests():
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    professional = User.query.filter_by(username=session['username']).first()
    open_requests = ServiceRequest.query.filter_by(status="pending", request_type="public", service_id=professional.service_id).filter(ServiceRequest.professional_id == None).all()
    sent_requests = ServiceRequest.query.filter_by(status="pending", request_type="public", service_id=professional.service_id, professional_id=professional.id).all()
    return render_template('open_requests_professional.html', open_requests=open_requests, sent_requests=sent_requests)

# create route for bidding requests sent by professional to customer for a given request id
@app.route('/professional_dashboard/bid_request/<int:request_id>', methods=['GET', 'POST'])
def bid_request(request_id):
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        description = request.form.get('description')
        professional_id = User.query.filter_by(username=session['username']).first().id
        service_id = User.query.filter_by(id=professional_id).first().service_id
        customer_id = ServiceRequest.query.filter_by(id=request_id).first().customer_id
        bid_request = ServiceRequest(service_id=service_id, customer_id=customer_id, professional_id=professional_id, description=description, request_type="public", status="pending")
        db.session.add(bid_request)
        db.session.commit()
        flash('Bid request created successfully and sent to customer', category='success')
        return redirect(url_for('professional_dashboard'))
    return render_template('open_requests_professional.html', request_id=request_id)

# create a route for customer to see all the bidding requests sent by professional
@app.route('/customer_dashboard/bidding_requests', methods=['GET', 'POST'])
def bidding_requests():
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    customer_id = User.query.filter_by(username=session['username']).first().id
    open_requests = ServiceRequest.query.filter_by(status="pending", request_type="public", customer_id=customer_id).filter(ServiceRequest.professional_id != None).all()
    return render_template('open_requests_customer.html', open_requests=open_requests, customer_name=session['username'])

# create a route for customer to reject a bid request
@app.route('/customer_dashboard/reject_bid_request/<int:request_id>', methods=['GET', 'POST'])
def reject_bid_request(request_id):
    if not session.get('is_customer'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))
    bid_request = ServiceRequest.query.filter_by(id=request_id).first() # filter by id and get the first object itter
    db.session.delete(bid_request)
    db.session.commit()
    flash('Bid request rejected successfully.', category='success')
    return redirect(url_for('customer_dashboard'))

# create a route for customer to accept a bid request
@app.route('/customer_dashboard/accept_bid_request/<int:request_id>', methods=['GET', 'POST'])
def accept_bid_request(request_id):
    if not session.get('is_customer'):
        flash('Please log in first.', category='danger')
        return redirect(url_for('login'))
    
    # Retrieve the specific bid request
    bid_request = ServiceRequest.query.filter_by(id=request_id).first()
    if not bid_request:
        flash('Bid request not found.', category='danger')
        return redirect(url_for('customer_dashboard'))
    
    # Set the current bid request status to accepted
    bid_request.status = "accepted"
    
    # Retrieve other pending public requests with the same service_id but exclude the accepted bid
    old_bid_requests = ServiceRequest.query.filter(
        ServiceRequest.id != bid_request.id,
        ServiceRequest.request_type == 'public',
        ServiceRequest.service_id == bid_request.service_id,
        ServiceRequest.status == 'pending'
    ).all()

    # Delete the old pending requests
    for old_request in old_bid_requests:
        db.session.delete(old_request)

    # Commit the changes to the database
    db.session.commit()

    flash('Bid request accepted successfully.', category='success')
    return redirect(url_for('customer_dashboard'))


# creating route for professional dashboard for search service

@app.route('/professional_dashboard/professional_search', methods=['GET', 'POST'])
def professional_search():
    # Check if the user is logged in as a professional
    if not session.get('is_professional'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))

    # Get the professional user and search parameters
    professional = User.query.filter_by(username=session['username']).first()
    search_type = request.args.get('search_type')  # Can be 'pincode' or 'address'
    search_query = request.args.get('search_query')

    # Define the join condition
    onclause = ServiceRequest.customer_id == User.id

    # Filter requests based on search criteria
    if search_query:
        if search_type == 'pincode':
            service_requests = ServiceRequest.query.join(User, onclause).filter(
                User.pincode.like(f"%{search_query}%"),
                ServiceRequest.request_type == 'public',
                ServiceRequest.status == 'pending',
                ServiceRequest.professional_id == None,  # Unassigned requests
                ServiceRequest.service_id == professional.service_id  # Match professional's service type
            ).all()
        elif search_type == 'address':
            service_requests = ServiceRequest.query.join(User, onclause).filter(
                User.address.like(f"%{search_query}%"),
                ServiceRequest.request_type == 'public',
                ServiceRequest.status == 'pending',
                ServiceRequest.professional_id == None,  # Unassigned requests
                ServiceRequest.service_id == professional.service_id  # Match professional's service type
            ).all()
    else:
        # If no search query, retrieve all matching requests
        service_requests = ServiceRequest.query.join(User, onclause).filter(
            ServiceRequest.request_type == 'public',
            ServiceRequest.status == 'pending',
            ServiceRequest.professional_id == None,  # Unassigned requests
            ServiceRequest.service_id == professional.service_id  # Match professional's service type
        ).all()

    # Render the template with the filtered service requests
    return render_template('professional_search.html', service_requests=service_requests, professional_name=session['username'])

@app.route('/professional_dashboard/b_request/<int:request_id>', methods=['GET', 'POST'])
def b_request(request_id):
    # Fetch the service request details using the request_id
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    if request.method == 'POST':
        # Process the form submission
        description = request.form.get('description')
        if description:
            # Add logic to save the bid here (e.g., creating a new Bid entry in the database)
            flash(f"Bid for request {request_id} submitted successfully!", "success")
            return redirect(url_for('professional_search'))
        else:
            flash("Failed to submit the bid request. Please try again.", "danger")

    # If GET request, render the bid request page with service request details
    return render_template('bid_request.html', service_request=service_request)

plt.switch_backend('Agg')

@app.route('/admin_dashboard/summary', methods=['GET', 'POST'])
def admin_summary():
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))

    customer_count = User.query.filter_by(is_customer=True).count()
    professional_count = User.query.filter_by(is_professional=True).count()

    pending_count = ServiceRequest.query.filter_by(status='pending').count()
    accepted_count = ServiceRequest.query.filter_by(status='accepted').count()
    rejected_count = ServiceRequest.query.filter_by(status='rejected').count()
    closed_count = ServiceRequest.query.filter_by(status='closed').count()

    img_1 = os.path.join(curr_dir, 'static', 'images', 'img_1.png')
    img_2 = os.path.join(curr_dir, 'static', 'images', 'img_2.png')

    # User Summary Bar Chart
    roles = ['customers', 'professionals']
    counts = [customer_count, professional_count]

    plt.clf()  # Clear the current figure
    plt.figure(figsize=(8, 6))

    if customer_count == 0 and professional_count == 0:
        # No users, create a blank image
        plt.text(0.5, 0.5, "No Data Available for Users", ha='center', va='center', fontsize=12, color='gray')
    else:
        sns.barplot(x=roles, y=counts)
        plt.title('User Summary')
        plt.xlabel('Roles')
        plt.ylabel('Count')

    plt.savefig(img_1, format='png')
    plt.close()

    # Service Request Distribution Pie Chart
    status = ['accepted', 'rejected', 'pending', 'closed']
    counts = [accepted_count, rejected_count, pending_count, closed_count]

    plt.clf()  # Clear the current figure
    plt.figure(figsize=(8, 6))

    if accepted_count == 0 and rejected_count == 0 and pending_count == 0 and closed_count == 0:
        # No requests, create a blank image
        plt.text(0.5, 0.5, "No Data Available for Service Requests", ha='center', va='center', fontsize=12, color='gray')
    else:
        plt.pie(counts, labels=status, colors=['green', 'red', 'orange', 'blue'], autopct='%1.1f%%')
        plt.title('Service Request Distribution Status')

    plt.savefig(img_2, format='png')
    plt.close()

    return render_template('admin_summary.html', customer_count=customer_count, 
                           professional_count=professional_count, pending_count=pending_count,
                           accepted_count=accepted_count, rejected_count=rejected_count,
                           closed_count=closed_count, admin_name=session['username'])

    
# create route for admin search

@app.route('/admin_dashboard/admin_search', methods=['GET', 'POST'])
def admin_search():
    # Check if the user is logged in as an admin
    if not session.get('is_admin'):
        flash('Please login first.', category='danger')
        return redirect(url_for('login'))

    search_query = request.args.get('search_query')
    search_type = request.args.get('search_type')

    users = []
    services = []  # Initialize services as an empty list to avoid UnboundLocalError
    
    if search_query:
        if search_type == 'username':
            users = User.query.filter(User.username.like(f"%{search_query}%")).all()
        elif search_type == 'address':
            users = User.query.filter(User.address.like(f"%{search_query}%")).all()
        elif search_type == 'pincode':
            users = User.query.filter(User.pincode.like(f"%{search_query}%")).all()
        elif search_type == 'service_name':
            services = Service.query.filter(Service.name.like(f"%{search_query}%")).all()
        else:
            flash('Invalid search type.', category='danger')
            return redirect(url_for('admin_search'))
    else:
        users = User.query.filter(User.is_verified == True).all()
        services = Service.query.all()  # Retrieve all services only if no specific search is performed

    return render_template(
        'admin_search.html',
        users=users,
        admin_name=session['username'],
        services=services
    )


@app.route('/professional_dashboard/professional_summary', methods=['GET', 'POST'])
def professional_summary():
    # Check if the user is logged in as a professional
    if not session.get('is_professional'):
        flash('Please login as a professional first.', category='danger')
        return redirect(url_for('login'))
    
    professional_id = session.get('id')
    
    # Retrieve service requests for the professional
    service_requests = ServiceRequest.query.filter_by(professional_id=professional_id).all()

    # Calculate statistics for the professional's requests
    total_requests = len(service_requests)
    pending_count = ServiceRequest.query.filter_by(professional_id=professional_id, status='pending').count()
    completed_count = ServiceRequest.query.filter_by(professional_id=professional_id, status='closed').count()
    accepted_count = ServiceRequest.query.filter_by(professional_id=professional_id, status='accepted').count()
    rejected_count = ServiceRequest.query.filter_by(professional_id=professional_id, status='rejected').count()
    # Calculate average rating
    professional = User.query.get(professional_id)
    avg_rating = round(professional.avg_rating, 2) if professional and professional.avg_rating else "No ratings yet"

    # Generate paths for the images to save
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    img_1 = os.path.join(curr_dir, 'static', 'images', 'professional_summary_requests.png')
    img_2 = os.path.join(curr_dir, 'static', 'images', 'professional_summary_status.png')
    img_3 = os.path.join(curr_dir, 'static', 'images', 'professional_rating_distribution.png')

    if total_requests > 0:
        # Create charts for request summary and status distribution
        request_types = ['Pending', 'Completed']
        counts = [pending_count, completed_count]
        
        plt.clf()
        plt.figure(figsize=(8, 6))
        sns.barplot(x=request_types, y=counts, palette='muted')
        plt.title('Summary of Request Status')
        plt.xlabel('Request Type')
        plt.ylabel('Count')
        plt.savefig(img_1, format='png')
        plt.close()

        status_labels = ['Accepted', 'Rejected', 'Pending', 'Closed']
        status_counts = [accepted_count, rejected_count, pending_count, completed_count]

        plt.clf()
        plt.figure(figsize=(8, 6))
        plt.pie(status_counts, labels=status_labels, colors=['green', 'red', 'orange', 'blue'], autopct='%1.1f%%')
        plt.title('Distribution of Service Request Status')
        # plt.pie(counts, labels=status, colors=['green', 'red', 'orange', 'blue'], autopct='%1.1f%%')
        # plt.title('Service Request Distribution Status')
        plt.savefig(img_2, format='png')
        plt.close()

        # Create doughnut chart for rating distribution
        rating_counts = [professional.rating_count if professional and professional.rating_count else 0]
        rating_labels = [f'Average Rating: {avg_rating} out of 5']

        plt.clf()
        plt.figure(figsize=(8, 6))

        # Calculate the percentage fill based on the average rating
        rating_percentage = professional.avg_rating if professional and professional.avg_rating else 0
        rating_percentage = min(rating_percentage, 5)  # Ensure the rating does not exceed 5

        # Prepare the chart data
        rating_counts = [rating_percentage, 5 - rating_percentage]  # Fill and empty sections of the doughnut
        rating_labels = [f'{rating_percentage} out of 5', f'']

        # Set the colors for the filled and empty sections
        colors = ['#9C27B0', '#E0E0E0']  # Purple for filled, light grey for remaining

        # Create the doughnut chart
        plt.pie(rating_counts, labels=rating_labels, colors=colors, autopct='%1.1f%%', startangle=90, 
                wedgeprops=dict(width=0.3, edgecolor='black'))

        # Title and save the chart
        plt.title('Average Rating Distribution', fontsize=16)
        plt.tight_layout()  # Adjust the layout for better clarity
        plt.savefig(img_3, format='png')
        plt.close()


        img_1_path = '/static/images/professional_summary_requests.png'
        img_2_path = '/static/images/professional_summary_status.png'
        img_3_path = '/static/images/professional_rating_distribution.png'
        no_data_message = None
    else:
        img_1_path = None
        img_2_path = None
        img_3_path = None
        no_data_message = "No Data Available for Service Requests"

    return render_template(
        'professional_summary.html',
        total_requests=total_requests,
        pending_count=pending_count,
        completed_count=completed_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        avg_rating=avg_rating,
        img_1=img_1_path,
        img_2=img_2_path,
        img_3=img_3_path,
        no_data_message=no_data_message,
        professional_name=session['username']
    )

@app.route('/block_user/<int:user_id>', methods=['POST'])
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = True
    db.session.commit()
    flash(f'User {user.username} has been blocked.', 'success')
    return redirect(url_for('admin_search'))  # Adjust redirect as needed

@app.route('/unblock_user/<int:user_id>', methods=['POST'])
def unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    flash(f'User {user.username} has been unblocked.', 'success')
    return redirect(url_for('admin_search'))  # Adjust redirect as needed


@app.route('/customer_dashboard/customer_summary', methods=['GET', 'POST'])
def customer_summary():
    # Check if the user is logged in as a customer
    if not session.get('is_customer'):
        flash('Please log in as a customer first.', category='danger')
        return redirect(url_for('login'))
    
    customer_id = session.get('id')

    # # Debugging: Ensure the correct customer_id is fetched from session
    # print(f"Customer ID from session: {customer_id}")
    
    # Retrieve specific counts of service requests based on status for the logged-in customer
    pending_count = ServiceRequest.query.filter_by(customer_id=customer_id, status='pending').count()
    accepted_count = ServiceRequest.query.filter_by(customer_id=customer_id, status='accepted').count()
    rejected_count = ServiceRequest.query.filter_by(customer_id=customer_id, status='rejected').count()
    closed_count = ServiceRequest.query.filter_by(customer_id=customer_id, status='closed').count()

    # Debugging: Ensure the counts are retrieved correctly
    print(f"Pending: {pending_count}, Accepted: {accepted_count}, Rejected: {rejected_count}, Closed: {closed_count}")
    
    # Calculate total requests for the logged-in customer
    total_requests = pending_count + accepted_count + rejected_count + closed_count

    # Set path for the image to save
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(curr_dir, 'static', 'images', 'customer_summary_requests.png')

    # Check if there are any requests to display the chart
    if total_requests > 0:
        # Chart: Bar chart for Request Status Distribution
        request_types = ['Pending', 'Accepted', 'Rejected', 'Closed']
        counts = [pending_count, accepted_count, rejected_count, closed_count]

        plt.clf()
        plt.figure(figsize=(8, 6))
        sns.barplot(x=request_types, y=counts, palette='muted')
        plt.title('Customer Service Request Distribution')
        plt.xlabel('Request Status')
        plt.ylabel('Count')
        plt.savefig(img_path, format='png')
        plt.close()

        img_url = '/static/images/customer_summary_requests.png'
        no_data_message = None
    else:
        # If there are no requests, skip chart creation and set the no data message
        img_url = None
        no_data_message = "No Data Available for Service Requests"

    # Render template with summary data
    return render_template(
        'customer_summary.html',
        total_requests=total_requests,
        pending_count=pending_count,
        accepted_count=accepted_count,
        rejected_count=rejected_count,
        closed_count=closed_count,
        img_url=img_url,
        no_data_message=no_data_message,
        customer_name=session['username']
    )







if __name__ == '__main__':
    app.run(debug=True)

