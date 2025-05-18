from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from models import Domain, WordPressSite
from app import db
import logging
import subprocess
import os
import pymysql
from pymysql.cursors import DictCursor
import string
import random
from utils.database import create_database, delete_database, export_database, import_database
from config import DB_USER, DB_PASSWORD

database_bp = Blueprint('database', __name__, url_prefix='/database')
logger = logging.getLogger(__name__)

@database_bp.route('/')
@login_required
def manage_databases():
    # Get WordPress sites with their domain info
    if current_user.role == 'admin':
        sites = WordPressSite.query.all()
    else:
        user_domains = Domain.query.filter_by(user_id=current_user.id).all()
        domain_ids = [domain.id for domain in user_domains]
        sites = WordPressSite.query.filter(WordPressSite.domain_id.in_(domain_ids)).all()
    
    return render_template('database.html', sites=sites)

@database_bp.route('/create', methods=['POST'])
@login_required
def create_db():
    db_name = request.form.get('db_name')
    db_user = request.form.get('db_user')
    db_password = request.form.get('db_password', ''.join(random.choices(string.ascii_letters + string.digits, k=16)))
    
    if not all([db_name, db_user]):
        flash('Database name and user are required.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Only admin can create arbitrary databases
    if current_user.role != 'admin':
        flash('You do not have permission to create databases.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    try:
        result = create_database(db_name, db_user, db_password)
        
        if result['success']:
            flash(f'Database {db_name} created successfully.', 'success')
            logger.info(f"User {current_user.username} created database: {db_name}")
        else:
            flash(f'Database creation failed: {result["message"]}', 'danger')
            logger.error(f"Database creation failed for {db_name}: {result['message']}")
    except Exception as e:
        flash(f'Database creation failed: {str(e)}', 'danger')
        logger.error(f"Database creation failed for {db_name}: {str(e)}")
    
    return redirect(url_for('database.manage_databases'))

@database_bp.route('/delete', methods=['POST'])
@login_required
def delete_db():
    db_name = request.form.get('db_name')
    
    if not db_name:
        flash('Database name is required.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Check if this is a WordPress database
    site = WordPressSite.query.filter_by(db_name=db_name).first()
    
    if site:
        domain = Domain.query.get(site.domain_id)
        # Check if user has permission to delete this WordPress database
        if domain.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have permission to delete this database.', 'danger')
            return redirect(url_for('database.manage_databases'))
        
        flash('Cannot delete database associated with a WordPress site. Delete the site first.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Only admin can delete arbitrary databases
    if current_user.role != 'admin':
        flash('You do not have permission to delete databases.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    try:
        result = delete_database(db_name)
        
        if result['success']:
            flash(f'Database {db_name} deleted successfully.', 'success')
            logger.info(f"User {current_user.username} deleted database: {db_name}")
        else:
            flash(f'Database deletion failed: {result["message"]}', 'danger')
            logger.error(f"Database deletion failed for {db_name}: {result['message']}")
    except Exception as e:
        flash(f'Database deletion failed: {str(e)}', 'danger')
        logger.error(f"Database deletion failed for {db_name}: {str(e)}")
    
    return redirect(url_for('database.manage_databases'))

@database_bp.route('/export', methods=['POST'])
@login_required
def export_db():
    db_name = request.form.get('db_name')
    
    if not db_name:
        flash('Database name is required.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Check if this is a WordPress database
    site = WordPressSite.query.filter_by(db_name=db_name).first()
    
    if site:
        domain = Domain.query.get(site.domain_id)
        # Check if user has permission to export this WordPress database
        if domain.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have permission to export this database.', 'danger')
            return redirect(url_for('database.manage_databases'))
    elif current_user.role != 'admin':
        # Only admin can export arbitrary databases
        flash('You do not have permission to export this database.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    try:
        result = export_database(db_name)
        
        if result['success']:
            return redirect(url_for('database.download_export', filename=result['filename']))
        else:
            flash(f'Database export failed: {result["message"]}', 'danger')
            logger.error(f"Database export failed for {db_name}: {result['message']}")
    except Exception as e:
        flash(f'Database export failed: {str(e)}', 'danger')
        logger.error(f"Database export failed for {db_name}: {str(e)}")
    
    return redirect(url_for('database.manage_databases'))

@database_bp.route('/download/<filename>')
@login_required
def download_export(filename):
    # Security check to prevent directory traversal
    if '/' in filename or '\\' in filename:
        flash('Invalid filename.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    export_path = os.path.join('/tmp', filename)
    
    if not os.path.exists(export_path):
        flash('Export file not found.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    from flask import send_file
    return send_file(
        export_path,
        as_attachment=True,
        download_name=filename
    )

@database_bp.route('/import', methods=['POST'])
@login_required
def import_db():
    db_name = request.form.get('db_name')
    sql_file = request.files.get('sql_file')
    
    if not db_name or not sql_file:
        flash('Database name and SQL file are required.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Check if this is a WordPress database
    site = WordPressSite.query.filter_by(db_name=db_name).first()
    
    if site:
        domain = Domain.query.get(site.domain_id)
        # Check if user has permission to import to this WordPress database
        if domain.user_id != current_user.id and current_user.role != 'admin':
            flash('You do not have permission to import to this database.', 'danger')
            return redirect(url_for('database.manage_databases'))
    elif current_user.role != 'admin':
        # Only admin can import to arbitrary databases
        flash('You do not have permission to import to this database.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Save the uploaded file temporarily
    temp_path = os.path.join('/tmp', f"import_{db_name}_{random.randrange(10000)}.sql")
    sql_file.save(temp_path)
    
    try:
        result = import_database(db_name, temp_path)
        
        if result['success']:
            flash(f'Database {db_name} imported successfully.', 'success')
            logger.info(f"User {current_user.username} imported database: {db_name}")
        else:
            flash(f'Database import failed: {result["message"]}', 'danger')
            logger.error(f"Database import failed for {db_name}: {result['message']}")
    except Exception as e:
        flash(f'Database import failed: {str(e)}', 'danger')
        logger.error(f"Database import failed for {db_name}: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return redirect(url_for('database.manage_databases'))

@database_bp.route('/adminer')
@login_required
def adminer():
    # Only allow admin users to access Adminer
    if current_user.role != 'admin':
        flash('You do not have permission to access Adminer.', 'danger')
        return redirect(url_for('database.manage_databases'))
    
    # Serve Adminer from static directory
    return send_from_directory('static/adminer', 'adminer.php')

@database_bp.route('/api/list')
@login_required
def api_list_databases():
    try:
        db_user = os.environ.get('DB_USER', DB_USER)
        db_password = os.environ.get('DB_PASSWORD', DB_PASSWORD)
        conn = pymysql.connect(
            host='localhost',
            user=db_user,
            password=db_password,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            all_dbs = cursor.fetchall()
            # Filter system databases
            system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
            databases = [db['Database'] for db in all_dbs if db['Database'] not in system_dbs]
            # Get WordPress databases
            if current_user.role == 'admin':
                wp_sites = WordPressSite.query.all()
            else:
                user_domains = Domain.query.filter_by(user_id=current_user.id).all()
                domain_ids = [domain.id for domain in user_domains]
                wp_sites = WordPressSite.query.filter(WordPressSite.domain_id.in_(domain_ids)).all()
            wp_dbs = [site.db_name for site in wp_sites]
            result = {
                'databases': databases,
                'wordpress_dbs': wp_dbs
            }
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing databases: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
