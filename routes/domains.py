from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Domain, WordPressSite
from app import db
import logging
from utils.validator import validate_domain_name
import subprocess

domains_bp = Blueprint('domains', __name__, url_prefix='/domains')
logger = logging.getLogger(__name__)

@domains_bp.route('/')
@login_required
def list_domains():
    domains = Domain.query.all() if current_user.role == 'admin' else Domain.query.filter_by(user_id=current_user.id).all()
    return render_template('domains.html', domains=domains)

@domains_bp.route('/add', methods=['POST'])
@login_required
def add_domain():
    domain_name = request.form.get('domain_name', '').strip().lower()
    is_subdomain = 'is_subdomain' in request.form
    parent_domain = request.form.get('parent_domain', '').strip() if is_subdomain else None
    
    # Validate domain name
    validation_result = validate_domain_name(domain_name, is_subdomain, parent_domain)
    if not validation_result['valid']:
        flash(validation_result['message'], 'danger')
        return redirect(url_for('domains.list_domains'))
    
    # Check if domain already exists
    existing_domain = Domain.query.filter_by(name=domain_name).first()
    if existing_domain:
        flash(f'Domain {domain_name} already exists.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    # Create new domain
    new_domain = Domain()
    new_domain.name = domain_name
    new_domain.is_subdomain = is_subdomain
    new_domain.parent_domain = parent_domain
    new_domain.user_id = current_user.id
    
    db.session.add(new_domain)
    db.session.commit()
    
    try:
        # Create directory structure in the Replit environment
        import os
        document_root = f"./domains/{domain_name}"
        os.makedirs(document_root, exist_ok=True)
        
        flash(f'Domain {domain_name} added successfully.', 'success')
        logger.info(f"User {current_user.username} added domain: {domain_name}")
    except Exception as e:
        flash(f'Domain added but directory creation failed: {e}', 'warning')
        logger.error(f"Directory creation failed for domain {domain_name}: {e}")
    
    return redirect(url_for('domains.list_domains'))

@domains_bp.route('/edit/<int:domain_id>', methods=['POST'])
@login_required
def edit_domain(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission to edit this domain
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to edit this domain.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    domain_name = request.form.get('domain_name', '').strip().lower()
    
    # Validate domain name
    validation_result = validate_domain_name(domain_name, domain.is_subdomain, domain.parent_domain)
    if not validation_result['valid']:
        flash(validation_result['message'], 'danger')
        return redirect(url_for('domains.list_domains'))
    
    # Check if new domain name already exists (excluding the current domain)
    existing_domain = Domain.query.filter(Domain.name == domain_name, Domain.id != domain_id).first()
    if existing_domain:
        flash(f'Domain {domain_name} already exists.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    # Rename domain directories if needed
    if domain_name != domain.name:
        try:
            import os
            old_path = f"./domains/{domain.name}"
            new_path = f"./domains/{domain_name}"
            
            # Check if the old directory exists before attempting to rename
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
            else:
                # If the directory doesn't exist, create the new one
                os.makedirs(new_path, exist_ok=True)
            
            # Update domain name
            domain.name = domain_name
            db.session.commit()
            
            flash(f'Domain updated successfully.', 'success')
            logger.info(f"User {current_user.username} updated domain: {domain_name}")
        except Exception as e:
            flash(f'Failed to rename domain directory: {e}', 'danger')
            logger.error(f"Directory rename failed for domain {domain.name} to {domain_name}: {e}")
            return redirect(url_for('domains.list_domains'))
    
    return redirect(url_for('domains.list_domains'))

@domains_bp.route('/delete/<int:domain_id>', methods=['POST'])
@login_required
def delete_domain(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission to delete this domain
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this domain.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    # Check if domain has WordPress site
    if domain.wordpress_site:
        flash('Cannot delete domain with an active WordPress site. Delete the WordPress site first.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    domain_name = domain.name
    
    # Delete domain directories
    try:
        import os
        import shutil
        document_root = f"./domains/{domain_name}"
        
        # Check if directory exists before attempting to remove it
        if os.path.exists(document_root):
            shutil.rmtree(document_root)
        
        # Delete domain from database
        db.session.delete(domain)
        db.session.commit()
        
        flash(f'Domain {domain_name} deleted successfully.', 'success')
        logger.info(f"User {current_user.username} deleted domain: {domain_name}")
    except Exception as e:
        flash(f'Failed to delete domain directory: {e}', 'danger')
        logger.error(f"Directory deletion failed for domain {domain_name}: {e}")
        
        # Still delete from database
        db.session.delete(domain)
        db.session.commit()
        
        flash(f'Domain {domain_name} deleted from database but directory removal failed.', 'warning')
    
    return redirect(url_for('domains.list_domains'))

@domains_bp.route('/api/list')
@login_required
def api_list_domains():
    if current_user.role == 'admin':
        domains = Domain.query.all()
    else:
        domains = Domain.query.filter_by(user_id=current_user.id).all()
    
    return jsonify([{
        'id': domain.id,
        'name': domain.name,
        'is_subdomain': domain.is_subdomain,
        'parent_domain': domain.parent_domain,
        'has_wordpress': bool(domain.wordpress_site)
    } for domain in domains])

@domains_bp.route('/api/check/<name>')
@login_required
def api_check_domain(name):
    existing = Domain.query.filter_by(name=name).first()
    return jsonify({
        'available': not existing,
        'valid': validate_domain_name(name, False, None)['valid']
    })
