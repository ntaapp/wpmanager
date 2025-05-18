from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from models import User
from app import db
import logging
from datetime import datetime

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('domains.list_domains'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('domains.list_domains'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password', '')  # Default to empty string if None
        remember = 'remember' in request.form

        logger.debug(f"Login attempt: username={username}, password length={len(password)}")

        user = User.query.filter_by(username=username).first()
        
        if not user:
            logger.warning(f"Login failed: No user found with username: {username}")
            flash('Login failed. Please check your username and password.', 'danger')
            return render_template('login.html')
            
        logger.debug(f"User found: id={user.id}, username={user.username}, password_hash={user.password_hash[:20]}...")
        
        # Try to verify password
        is_password_correct = check_password_hash(user.password_hash, password)
        logger.debug(f"Password verification result: {is_password_correct}")

        if is_password_correct:
            # Password is correct, try to log in
            try:
                login_user(user, remember=remember)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"User {username} logged in successfully")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('domains.list_domains'))
            except Exception as e:
                logger.error(f"Error during login_user: {str(e)}")
                flash('An error occurred during login. Please try again.', 'danger')
        else:
            flash('Login failed. Please check your username and password.', 'danger')
            logger.warning(f"Failed login attempt: Password verification failed for username: {username}")

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info(f"User {username} logged out")
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if email and email != current_user.email:
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Email address is already in use.', 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.email = email
            flash('Email updated successfully.', 'success')
        
        if current_password and new_password and confirm_password:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.profile'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))
            
            current_user.password_hash = generate_password_hash(new_password)
            flash('Password updated successfully.', 'success')
        
        db.session.commit()
        return redirect(url_for('auth.profile'))
    
    return render_template('profile.html', user=current_user)

@auth_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@auth_bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    # Validate input
    if not username or not email or not password or not role:
        flash('All fields are required.', 'danger')
        return redirect(url_for('auth.users'))
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('auth.users'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('auth.users'))
    
    # Create new user
    new_user = User()
    new_user.username = username
    new_user.email = email
    new_user.password_hash = generate_password_hash(password)
    new_user.role = role
    
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'User {username} created successfully.', 'success')
    logger.info(f"Admin {current_user.username} created new user: {username}")
    return redirect(url_for('auth.users'))

@auth_bp.route('/users/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    user = User.query.get_or_404(user_id)
    
    email = request.form.get('email')
    role = request.form.get('role')
    password = request.form.get('password')
    
    if email and email != user.email:
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash('Email address is already in use.', 'danger')
            return redirect(url_for('auth.users'))
        
        user.email = email
    
    if role:
        user.role = role
    
    if password:
        user.password_hash = generate_password_hash(password)
    
    db.session.commit()
    
    flash(f'User {user.username} updated successfully.', 'success')
    logger.info(f"Admin {current_user.username} updated user: {user.username}")
    return redirect(url_for('auth.users'))

@auth_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('auth.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully.', 'success')
    logger.info(f"Admin {current_user.username} deleted user: {username}")
    return redirect(url_for('auth.users'))
