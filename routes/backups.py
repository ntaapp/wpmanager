from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from models import Domain, WordPressSite, Backup, BackupSchedule, RemoteStorage
from app import db, scheduler
import logging
import subprocess
import os
from datetime import datetime, timedelta
import tempfile
import uuid
from utils.backup_simple import create_backup, restore_backup, setup_backup_schedule, delete_backup, get_backup_file
from utils.validator import validate_path

backups_bp = Blueprint('backups', __name__, url_prefix='/backups')
logger = logging.getLogger(__name__)

@backups_bp.route('/')
@login_required
def list_backups():
    if current_user.role == 'admin':
        backups = Backup.query.order_by(Backup.created_at.desc()).all()
        domains = Domain.query.all()
        schedules = BackupSchedule.query.all()
    else:
        backups = Backup.query.filter_by(user_id=current_user.id).order_by(Backup.created_at.desc()).all()
        domains = Domain.query.filter_by(user_id=current_user.id).all()
        schedules = BackupSchedule.query.filter_by(user_id=current_user.id).all()
    
    remote_storages = RemoteStorage.query.filter_by(user_id=current_user.id).all()
    
    return render_template('backups.html', 
                           backups=backups, 
                           domains=domains, 
                           schedules=schedules,
                           remote_storages=remote_storages)

@backups_bp.route('/create', methods=['POST'])
@login_required
def create_backup_route():
    domain_id = request.form.get('domain_id')
    backup_type = request.form.get('backup_type', 'full')
    storage_type = request.form.get('storage_type', 'local')
    remote_storage_id = request.form.get('remote_storage_id')
    remote_path = request.form.get('remote_path', '')
    
    if not domain_id:
        flash('Domain is required.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to backup this domain.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Get WordPress site information if available
    site = WordPressSite.query.filter_by(domain_id=domain.id).first()
    
    # Validate remote path if using remote storage
    if storage_type != 'local':
        if not validate_path(remote_path):
            flash('Invalid remote path.', 'danger')
            return redirect(url_for('backups.list_backups'))
        
        # Get remote storage credentials
        if remote_storage_id:
            remote_storage = RemoteStorage.query.get(remote_storage_id)
            if not remote_storage or remote_storage.user_id != current_user.id:
                flash('Invalid remote storage selection.', 'danger')
                return redirect(url_for('backups.list_backups'))
    
    try:
        # Create backup
        backup_result = create_backup(
            domain=domain,
            site=site,
            backup_type=backup_type,
            storage_type=storage_type,
            remote_storage_id=remote_storage_id,
            remote_path=remote_path,
            user_id=current_user.id
        )
        
        if backup_result['success']:
            flash(f'Backup created successfully: {backup_result["backup_name"]}', 'success')
            logger.info(f"User {current_user.username} created backup for domain: {domain.name}")
        else:
            flash(f'Backup failed: {backup_result["message"]}', 'danger')
            logger.error(f"Backup failed for domain {domain.name}: {backup_result['message']}")
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'danger')
        logger.error(f"Backup failed for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/restore/<int:backup_id>', methods=['POST'])
@login_required
def restore_backup_route(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    
    # Check if user has permission
    if backup.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to restore this backup.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    try:
        restore_result = restore_backup(backup)
        
        if restore_result['success']:
            flash(f'Backup restored successfully for {backup.domain.name}.', 'success')
            logger.info(f"User {current_user.username} restored backup for domain: {backup.domain.name}")
        else:
            flash(f'Restore failed: {restore_result["message"]}', 'danger')
            logger.error(f"Restore failed for backup {backup_id}: {restore_result['message']}")
    except Exception as e:
        flash(f'Restore failed: {str(e)}', 'danger')
        logger.error(f"Restore failed for backup {backup_id}: {str(e)}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/delete/<int:backup_id>', methods=['POST'])
@login_required
def delete_backup_route(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    
    # Check if user has permission
    if backup.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this backup.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    try:
        delete_result = delete_backup(backup)
        
        if delete_result['success']:
            flash(f'Backup deleted successfully.', 'success')
            logger.info(f"User {current_user.username} deleted backup {backup_id}")
        else:
            flash(f'Delete failed: {delete_result["message"]}', 'danger')
            logger.error(f"Delete failed for backup {backup_id}: {delete_result['message']}")
    except Exception as e:
        flash(f'Delete failed: {str(e)}', 'danger')
        logger.error(f"Delete failed for backup {backup_id}: {str(e)}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/download/<int:backup_id>')
@login_required
def download_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    
    # Check if user has permission
    if backup.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to download this backup.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Only allow local backups to be downloaded directly
    if backup.storage_type != 'local':
        flash('Only local backups can be downloaded directly.', 'warning')
        return redirect(url_for('backups.list_backups'))
    
    try:
        backup_file = get_backup_file(backup)
        if backup_file['success']:
            return send_file(
                backup_file['file_path'],
                as_attachment=True,
                download_name=os.path.basename(backup.backup_path)
            )
        else:
            flash(f'Download failed: {backup_file["message"]}', 'danger')
            logger.error(f"Download failed for backup {backup_id}: {backup_file['message']}")
    except Exception as e:
        flash(f'Download failed: {str(e)}', 'danger')
        logger.error(f"Download failed for backup {backup_id}: {str(e)}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/schedule', methods=['POST'])
@login_required
def create_schedule():
    domain_id = request.form.get('domain_id')
    frequency = request.form.get('frequency', 'daily')
    hour = request.form.get('hour', 0, type=int)
    minute = request.form.get('minute', 0, type=int)
    day_of_week = request.form.get('day_of_week', 0, type=int) if frequency == 'weekly' else None
    day_of_month = request.form.get('day_of_month', 1, type=int) if frequency == 'monthly' else None
    
    backup_type = request.form.get('backup_type', 'full')
    storage_type = request.form.get('storage_type', 'local')
    remote_storage_id = request.form.get('remote_storage_id')
    remote_path = request.form.get('remote_path', '')
    retention_count = request.form.get('retention_count', 7, type=int)
    
    if not domain_id:
        flash('Domain is required.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to schedule backups for this domain.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Validate remote path if using remote storage
    if storage_type != 'local' and not validate_path(remote_path):
        flash('Invalid remote path.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Calculate next run time
    now = datetime.utcnow()
    next_run = datetime(now.year, now.month, now.day, hour, minute)
    
    if next_run < now:
        next_run = next_run + timedelta(days=1)
    
    # Create schedule
    schedule = BackupSchedule()
    schedule.domain_id = domain_id
    schedule.user_id = current_user.id
    schedule.frequency = frequency
    schedule.day_of_week = day_of_week
    schedule.day_of_month = day_of_month
    schedule.hour = hour
    schedule.minute = minute
    schedule.backup_type = backup_type
    schedule.storage_type = storage_type
    schedule.remote_path = remote_path
    schedule.retention_count = retention_count
    schedule.next_run = next_run
    
    db.session.add(schedule)
    db.session.commit()
    
    # Set up the schedule in APScheduler
    try:
        setup_backup_schedule(schedule, scheduler)
        flash(f'Backup schedule created successfully for {domain.name}.', 'success')
        logger.info(f"User {current_user.username} created backup schedule for domain: {domain.name}")
    except Exception as e:
        flash(f'Schedule created but job not started: {str(e)}', 'warning')
        logger.error(f"Failed to set up backup schedule for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/schedule/delete/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    schedule = BackupSchedule.query.get_or_404(schedule_id)
    
    # Check if user has permission
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this schedule.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Remove from scheduler
    try:
        job_id = f"backup_{schedule.id}"
        scheduler.remove_job(job_id)
    except Exception as e:
        logger.error(f"Failed to remove job from scheduler: {str(e)}")
    
    # Delete from database
    db.session.delete(schedule)
    db.session.commit()
    
    flash('Backup schedule deleted successfully.', 'success')
    logger.info(f"User {current_user.username} deleted backup schedule {schedule_id}")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/remote-storage', methods=['POST'])
@login_required
def add_remote_storage():
    storage_type = request.form.get('storage_type')
    name = request.form.get('storage_name')
    
    if storage_type == 'sftp':
        host = request.form.get('sftp_host')
        port = request.form.get('sftp_port', 22, type=int)
        username = request.form.get('sftp_username')
        password = request.form.get('sftp_password', '')
        key_file = request.form.get('sftp_key_file', '')
        
        credentials = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'key_file': key_file
        }
    elif storage_type == 'gdrive':
        client_id = request.form.get('gdrive_client_id')
        client_secret = request.form.get('gdrive_client_secret')
        refresh_token = request.form.get('gdrive_refresh_token', '')
        
        credentials = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token
        }
    elif storage_type == 'onedrive':
        client_id = request.form.get('onedrive_client_id')
        client_secret = request.form.get('onedrive_client_secret')
        refresh_token = request.form.get('onedrive_refresh_token', '')
        
        credentials = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token
        }
    else:
        flash('Invalid storage type.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    # Create remote storage
    remote_storage = RemoteStorage()
    remote_storage.user_id = current_user.id
    remote_storage.storage_type = storage_type
    remote_storage.name = name
    remote_storage.credentials = str(credentials)
    
    db.session.add(remote_storage)
    db.session.commit()
    
    flash(f'Remote storage "{name}" added successfully.', 'success')
    logger.info(f"User {current_user.username} added remote storage: {name} ({storage_type})")
    
    return redirect(url_for('backups.list_backups'))

@backups_bp.route('/remote-storage/delete/<int:storage_id>', methods=['POST'])
@login_required
def delete_remote_storage(storage_id):
    storage = RemoteStorage.query.get_or_404(storage_id)
    
    # Check if user has permission
    if storage.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this remote storage.', 'danger')
        return redirect(url_for('backups.list_backups'))
    
    name = storage.name
    db.session.delete(storage)
    db.session.commit()
    
    flash(f'Remote storage "{name}" deleted successfully.', 'success')
    logger.info(f"User {current_user.username} deleted remote storage: {name}")
    
    return redirect(url_for('backups.list_backups'))
