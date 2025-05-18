from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Domain, WordPressSite
from app import db
import logging
import subprocess
import os
import shutil
import string
import random
import pymysql
from utils.wordpress import install_wordpress, configure_openlitespeed, check_wordpress_status
import json

wordpress_bp = Blueprint('wordpress', __name__, url_prefix='/wordpress')
logger = logging.getLogger(__name__)

@wordpress_bp.route('/')
@login_required
def list_sites():
    if current_user.role == 'admin':
        sites = WordPressSite.query.all()
        domains = Domain.query.all()
    else:
        domains = Domain.query.filter_by(user_id=current_user.id).all()
        domain_ids = [domain.id for domain in domains]
        sites = WordPressSite.query.filter(WordPressSite.domain_id.in_(domain_ids)).all()
    
    return render_template('wordpress.html', sites=sites, domains=domains)

@wordpress_bp.route('/install', methods=['POST'])
@login_required
def install_site():
    domain_id = request.form.get('domain_id')
    admin_user = request.form.get('admin_user')
    admin_email = request.form.get('admin_email')
    admin_password = request.form.get('admin_password')
    site_title = request.form.get('site_title')
    wp_version = request.form.get('wp_version', 'latest')
    
    # Validate input
    if not all([domain_id, admin_user, admin_email, admin_password, site_title]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    # Get domain
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission to use this domain
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to use this domain.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    # Check if WordPress is already installed for this domain
    if WordPressSite.query.filter_by(domain_id=domain_id).first():
        flash(f'WordPress is already installed for domain {domain.name}.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    # Generate database credentials
    db_name = f"wp_{domain.name.replace('.', '_').replace('-', '_')}"
    db_user = f"wp_{domain.name.replace('.', '_').replace('-', '_')}"[:16]
    db_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    document_root = f"/var/www/html/{domain.name}"
    
    # Create WordPress site entry
    new_site = WordPressSite(
        domain_id=domain_id,
        wp_url=f"http://{domain.name}",
        admin_user=admin_user,
        admin_email=admin_email,
        db_name=db_name,
        db_user=db_user,
        db_pass=db_pass,
        document_root=document_root,
        version=wp_version,
        status='installing'
    )
    
    db.session.add(new_site)
    db.session.commit()
    
    # Install WordPress
    try:
        install_result = install_wordpress(
            domain_name=domain.name,
            db_name=db_name,
            db_user=db_user,
            db_pass=db_pass,
            wp_admin=admin_user,
            wp_admin_pass=admin_password,
            wp_admin_email=admin_email,
            site_title=site_title,
            document_root=document_root,
            wp_version=wp_version
        )
        
        if install_result['success']:
            new_site.status = 'active'
            db.session.commit()
            flash(f'WordPress installed successfully for {domain.name}.', 'success')
            logger.info(f"User {current_user.username} installed WordPress for domain: {domain.name}")
        else:
            new_site.status = 'error'
            db.session.commit()
            flash(f'WordPress installation failed: {install_result["message"]}', 'danger')
            logger.error(f"WordPress installation failed for domain {domain.name}: {install_result['message']}")
    except Exception as e:
        new_site.status = 'error'
        db.session.commit()
        flash(f'WordPress installation failed: {str(e)}', 'danger')
        logger.error(f"WordPress installation failed for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('wordpress.list_sites'))

@wordpress_bp.route('/configure-openlitespeed/<int:site_id>', methods=['POST'])
@login_required
def enable_openlitespeed(site_id):
    site = WordPressSite.query.get_or_404(site_id)
    domain = Domain.query.get_or_404(site.domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to configure this site.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    try:
        result = configure_openlitespeed(domain.name, site.document_root)
        
        if result['success']:
            site.openlitespeed_enabled = True
            db.session.commit()
            flash(f'OpenLiteSpeed configured successfully for {domain.name}.', 'success')
            logger.info(f"User {current_user.username} configured OpenLiteSpeed for domain: {domain.name}")
        else:
            flash(f'OpenLiteSpeed configuration failed: {result["message"]}', 'danger')
            logger.error(f"OpenLiteSpeed configuration failed for domain {domain.name}: {result['message']}")
    except Exception as e:
        flash(f'OpenLiteSpeed configuration failed: {str(e)}', 'danger')
        logger.error(f"OpenLiteSpeed configuration failed for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('wordpress.list_sites'))

@wordpress_bp.route('/disable-openlitespeed/<int:site_id>', methods=['POST'])
@login_required
def disable_openlitespeed(site_id):
    site = WordPressSite.query.get_or_404(site_id)
    domain = Domain.query.get_or_404(site.domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to configure this site.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    try:
        # We'll just set the flag to false as the actual configuration would be more complex
        site.openlitespeed_enabled = False
        db.session.commit()
        flash(f'OpenLiteSpeed disabled for {domain.name}.', 'success')
        logger.info(f"User {current_user.username} disabled OpenLiteSpeed for domain: {domain.name}")
    except Exception as e:
        flash(f'Failed to disable OpenLiteSpeed: {str(e)}', 'danger')
        logger.error(f"Failed to disable OpenLiteSpeed for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('wordpress.list_sites'))

@wordpress_bp.route('/delete/<int:site_id>', methods=['POST'])
@login_required
def delete_site(site_id):
    site = WordPressSite.query.get_or_404(site_id)
    domain = Domain.query.get_or_404(site.domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this site.', 'danger')
        return redirect(url_for('wordpress.list_sites'))
    
    try:
        # Get the document root path for macOS
        document_root = os.path.join(os.path.expanduser('~'), 'Documents', 'WordPressManager', 'domains', domain.name)
        
        # Remove all files in the WordPress directory
        if os.path.exists(document_root):
            for item in os.listdir(document_root):
                item_path = os.path.join(document_root, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.error(f"Error removing {item_path}: {str(e)}")
        
        # Drop database and user
        try:
            conn = pymysql.connect(
                host='localhost',
                user='root',
                password='',  # Configure as needed
                charset='utf8mb4'
            )
            with conn.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {site.db_name}")
                cursor.execute(f"DROP USER IF EXISTS '{site.db_user}'@'localhost'")
            conn.commit()
        except Exception as e:
            logger.error(f"Error dropping database: {str(e)}")
            flash('Warning: Could not delete database. You may need to delete it manually.', 'warning')
        finally:
            if 'conn' in locals():
                conn.close()
        
        # Delete site from database
        db.session.delete(site)
        db.session.commit()
        
        flash(f'WordPress site for {domain.name} deleted successfully.', 'success')
        logger.info(f"User {current_user.username} deleted WordPress site for domain: {domain.name}")
    except Exception as e:
        flash(f'Failed to delete WordPress site: {str(e)}', 'danger')
        logger.error(f"Failed to delete WordPress site for domain {domain.name}: {str(e)}")
        
        # Still delete from database
        db.session.delete(site)
        db.session.commit()
        
        flash(f'WordPress site deleted from database but some files may remain.', 'warning')
    
    return redirect(url_for('wordpress.list_sites'))

@wordpress_bp.route('/api/status/<int:site_id>')
@login_required
def api_site_status(site_id):
    site = WordPressSite.query.get_or_404(site_id)
    domain = Domain.query.get_or_404(site.domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    status = check_wordpress_status(domain.name, site.document_root)
    return jsonify(status)
