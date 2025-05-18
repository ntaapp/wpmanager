from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import logging
import requests
import subprocess
import json
import os
from utils.monitoring import get_system_stats, get_netdata_url, get_glances_url

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/monitoring')
logger = logging.getLogger(__name__)

@monitoring_bp.route('/')
@login_required
def system_monitor():
    # Only admins can access monitoring
    if current_user.role != 'admin':
        flash('You do not have permission to access monitoring.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    stats = get_system_stats()
    netdata_url = get_netdata_url()
    glances_url = get_glances_url()
    
    return render_template('monitoring.html', 
                           stats=stats, 
                           netdata_url=netdata_url,
                           glances_url=glances_url)

@monitoring_bp.route('/api/stats')
@login_required
def api_stats():
    # Only admins can access monitoring API
    if current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    
    stats = get_system_stats()
    return jsonify(stats)

@monitoring_bp.route('/netdata')
@login_required
def netdata_redirect():
    # Only admins can access netdata
    if current_user.role != 'admin':
        flash('You do not have permission to access Netdata.', 'danger')
        return redirect(url_for('monitoring.system_monitor'))
    
    netdata_url = get_netdata_url()
    return redirect(netdata_url)

@monitoring_bp.route('/glances')
@login_required
def glances_redirect():
    # Only admins can access glances
    if current_user.role != 'admin':
        flash('You do not have permission to access Glances.', 'danger')
        return redirect(url_for('monitoring.system_monitor'))
    
    glances_url = get_glances_url()
    return redirect(glances_url)

@monitoring_bp.route('/server-status')
@login_required
def server_status():
    # Only admins can access server status
    if current_user.role != 'admin':
        flash('You do not have permission to access server status.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    try:
        # Check web server status
        web_server_status = False
        try:
            web_server_proc = subprocess.run(
                ['systemctl', 'is-active', 'apache2'], 
                capture_output=True, 
                text=True
            )
            web_server_status = web_server_proc.stdout.strip() == 'active'
        except:
            # Try OpenLiteSpeed if Apache is not found
            try:
                web_server_proc = subprocess.run(
                    ['systemctl', 'is-active', 'lsws'], 
                    capture_output=True, 
                    text=True
                )
                web_server_status = web_server_proc.stdout.strip() == 'active'
            except:
                web_server_status = False
        
        # Check database status
        db_status = False
        try:
            db_proc = subprocess.run(
                ['systemctl', 'is-active', 'mariadb'], 
                capture_output=True, 
                text=True
            )
            db_status = db_proc.stdout.strip() == 'active'
        except:
            db_status = False
        
        # Check monitoring tools status
        netdata_status = False
        try:
            netdata_proc = subprocess.run(
                ['systemctl', 'is-active', 'netdata'], 
                capture_output=True, 
                text=True
            )
            netdata_status = netdata_proc.stdout.strip() == 'active'
        except:
            netdata_status = False
        
        glances_status = False
        try:
            # Check if glances is running
            glances_proc = subprocess.run(
                ['pgrep', '-f', 'glances'], 
                capture_output=True, 
                text=True
            )
            glances_status = bool(glances_proc.stdout.strip())
        except:
            glances_status = False
        
        # Check disk space
        disk_info = subprocess.run(
            ['df', '-h', '/'], 
            capture_output=True, 
            text=True
        )
        disk_lines = disk_info.stdout.strip().split('\n')
        disk_usage = disk_lines[1].split() if len(disk_lines) > 1 else []
        disk_percent = disk_usage[4] if len(disk_usage) > 4 else 'N/A'
        
        status = {
            'web_server': web_server_status,
            'database': db_status,
            'netdata': netdata_status,
            'glances': glances_status,
            'disk_usage': disk_percent
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error checking server status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@monitoring_bp.route('/restart-service', methods=['POST'])
@login_required
def restart_service():
    # Only admins can restart services
    if current_user.role != 'admin':
        flash('You do not have permission to restart services.', 'danger')
        return redirect(url_for('domains.list_domains'))
    
    service = request.form.get('service')
    
    if not service:
        flash('Service name is required.', 'danger')
        return redirect(url_for('monitoring.system_monitor'))
    
    allowed_services = ['apache2', 'lsws', 'mariadb', 'netdata']
    
    if service not in allowed_services:
        flash('Invalid service name.', 'danger')
        return redirect(url_for('monitoring.system_monitor'))
    
    try:
        subprocess.run(['systemctl', 'restart', service], check=True)
        flash(f'Service {service} restarted successfully.', 'success')
        logger.info(f"User {current_user.username} restarted service: {service}")
    except subprocess.CalledProcessError as e:
        flash(f'Failed to restart service {service}: {e}', 'danger')
        logger.error(f"Failed to restart service {service}: {e}")
    
    return redirect(url_for('monitoring.system_monitor'))
