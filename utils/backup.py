import os
import subprocess
import logging
import json
import tempfile
import shutil
from datetime import datetime
import uuid
from models import Domain, WordPressSite, Backup, BackupSchedule, RemoteStorage
from app import db
import paramiko
import requests
from utils.sftp import sftp_upload, sftp_download
from config import LOCAL_BACKUP_PATH, TEMP_BACKUP_PATH

logger = logging.getLogger(__name__)

def create_backup(domain, site, backup_type, storage_type, remote_storage_id=None, remote_path='', user_id=None):
    """
    Create a backup for the specified domain/WordPress site
    """
    try:
        # Create backup directories if they don't exist
        os.makedirs(LOCAL_BACKUP_PATH, exist_ok=True)
        os.makedirs(TEMP_BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        backup_name = f"{domain.name}_{backup_type}_{timestamp}"
        backup_file = f"{backup_name}.tar.gz"
        local_backup_path = os.path.join(LOCAL_BACKUP_PATH, backup_file)
        
        # Get the document root
        document_root = site.document_root if site else f"/var/www/html/{domain.name}"
        
        # Create backup based on type
        if backup_type == 'full':
            # Backup files and database if WordPress site
            if site:
                # Create temporary SQL dump
                sql_dump_path = os.path.join(TEMP_BACKUP_PATH, f"{domain.name}_{timestamp}.sql")
                dump_command = f"mysqldump {site.db_name} > {sql_dump_path}"
                subprocess.run(dump_command, shell=True, check=True)
                
                # Create tar archive with files and database
                tar_command = f"tar -czf {local_backup_path} -C {os.path.dirname(document_root)} {os.path.basename(document_root)} -C {os.path.dirname(sql_dump_path)} {os.path.basename(sql_dump_path)}"
                subprocess.run(tar_command, shell=True, check=True)
                
                # Remove temporary SQL dump
                os.remove(sql_dump_path)
            else:
                # Just backup files
                tar_command = f"tar -czf {local_backup_path} -C {os.path.dirname(document_root)} {os.path.basename(document_root)}"
                subprocess.run(tar_command, shell=True, check=True)
        
        elif backup_type == 'db':
            # Only backup database (requires WordPress)
            if not site:
                return {'success': False, 'message': 'Database backup requires a WordPress site'}
            
            sql_dump_path = os.path.join(TEMP_BACKUP_PATH, f"{domain.name}_{timestamp}.sql")
            dump_command = f"mysqldump {site.db_name} > {sql_dump_path}"
            subprocess.run(dump_command, shell=True, check=True)
            
            # Create tar archive with database dump
            tar_command = f"tar -czf {local_backup_path} -C {os.path.dirname(sql_dump_path)} {os.path.basename(sql_dump_path)}"
            subprocess.run(tar_command, shell=True, check=True)
            
            # Remove temporary SQL dump
            os.remove(sql_dump_path)
        
        elif backup_type == 'files':
            # Only backup files
            tar_command = f"tar -czf {local_backup_path} -C {os.path.dirname(document_root)} {os.path.basename(document_root)}"
            subprocess.run(tar_command, shell=True, check=True)
        
        # Get backup size
        backup_size = os.path.getsize(local_backup_path)
        
        # Upload to remote storage if specified
        remote_path_final = ''
        if storage_type != 'local':
            remote_storage = RemoteStorage.query.get(remote_storage_id) if remote_storage_id else None
            
            if not remote_storage:
                return {'success': False, 'message': 'Remote storage not found'}
            
            if storage_type == 'sftp':
                # Upload via SFTP
                credentials = json.loads(remote_storage.credentials.replace("'", "\""))
                remote_path_final = os.path.join(remote_path, backup_file).replace('\\', '/')
                
                upload_result = sftp_upload(
                    host=credentials['host'],
                    port=int(credentials['port']),
                    username=credentials['username'],
                    password=credentials['password'],
                    key_file=credentials['key_file'],
                    local_path=local_backup_path,
                    remote_path=remote_path_final
                )
                
                if not upload_result['success']:
                    return {'success': False, 'message': f"SFTP upload failed: {upload_result['message']}"}
            
            elif storage_type == 'gdrive' or storage_type == 'onedrive':
                # This would use OAuth to upload to Google Drive or OneDrive
                # For simplicity, we'll just log a message
                logger.warning(f"Upload to {storage_type} is not implemented in this development version")
                remote_path_final = os.path.join(remote_path, backup_file).replace('\\', '/')
        
        # Create backup record in database
        backup = Backup(
            domain_id=domain.id,
            user_id=user_id,
            backup_name=backup_name,
            backup_path=local_backup_path if storage_type == 'local' else '',
            remote_path=remote_path_final if storage_type != 'local' else '',
            backup_type=backup_type,
            storage_type=storage_type,
            size=backup_size,
            status='completed'
        )
        
        db.session.add(backup)
        db.session.commit()
        
        # Delete local backup if it was uploaded to remote storage
        if storage_type != 'local' and os.path.exists(local_backup_path):
            os.remove(local_backup_path)
        
        return {
            'success': True, 
            'message': 'Backup created successfully',
            'backup_name': backup_name,
            'backup_id': backup.id
        }
    
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return {'success': False, 'message': str(e)}

def restore_backup(backup):
    """
    Restore a backup
    """
    try:
        domain = Domain.query.get(backup.domain_id)
        if not domain:
            return {'success': False, 'message': 'Domain not found'}
        
        # Get the WordPress site if available
        site = WordPressSite.query.filter_by(domain_id=domain.id).first()
        document_root = site.document_root if site else f"/var/www/html/{domain.name}"
        
        # Create temporary directory for restoration
        temp_dir = os.path.join(TEMP_BACKUP_PATH, str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)
        
        backup_file = ''
        
        # Get the backup file from local or remote storage
        if backup.storage_type == 'local':
            backup_file = backup.backup_path
        else:
            # Download from remote storage
            if backup.storage_type == 'sftp':
                # Get the remote storage credentials
                remote_storage = RemoteStorage.query.filter_by(user_id=backup.user_id, storage_type='sftp').first()
                if not remote_storage:
                    return {'success': False, 'message': 'SFTP credentials not found'}
                
                credentials = json.loads(remote_storage.credentials.replace("'", "\""))
                temp_file = os.path.join(temp_dir, os.path.basename(backup.remote_path))
                
                download_result = sftp_download(
                    host=credentials['host'],
                    port=int(credentials['port']),
                    username=credentials['username'],
                    password=credentials['password'],
                    key_file=credentials['key_file'],
                    remote_path=backup.remote_path,
                    local_path=temp_file
                )
                
                if not download_result['success']:
                    shutil.rmtree(temp_dir)
                    return {'success': False, 'message': f"SFTP download failed: {download_result['message']}"}
                
                backup_file = temp_file
            
            elif backup.storage_type == 'gdrive' or backup.storage_type == 'onedrive':
                # This would use OAuth to download from Google Drive or OneDrive
                # For simplicity, we'll just log a message
                logger.warning(f"Download from {backup.storage_type} is not implemented in this development version")
                shutil.rmtree(temp_dir)
                return {'success': False, 'message': f"Download from {backup.storage_type} not implemented"}
        
        if not os.path.exists(backup_file):
            shutil.rmtree(temp_dir)
            return {'success': False, 'message': 'Backup file not found'}
        
        # Extract the backup to the temporary directory
        extract_command = f"tar -xzf {backup_file} -C {temp_dir}"
        subprocess.run(extract_command, shell=True, check=True)
        
        # Find extracted files
        extracted_files = os.listdir(temp_dir)
        document_root_dir = None
        sql_file = None
        
        for f in extracted_files:
            if f.endswith('.sql'):
                sql_file = os.path.join(temp_dir, f)
            elif os.path.isdir(os.path.join(temp_dir, f)) and f == os.path.basename(document_root):
                document_root_dir = os.path.join(temp_dir, f)
        
        # Restore database if SQL file exists and site exists
        if sql_file and site:
            restore_db_command = f"mysql {site.db_name} < {sql_file}"
            subprocess.run(restore_db_command, shell=True, check=True)
        
        # Restore files if document root directory exists
        if document_root_dir:
            # First, back up the current document root (just in case)
            backup_dir = f"{document_root}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            shutil.move(document_root, backup_dir)
            
            # Create new document root directory
            os.makedirs(document_root, exist_ok=True)
            
            # Copy files from extracted backup
            copy_command = f"cp -a {document_root_dir}/. {document_root}/"
            subprocess.run(copy_command, shell=True, check=True)
            
            # Set proper permissions
            subprocess.run(['chown', '-R', 'www-data:www-data', document_root])
            subprocess.run(['chmod', '-R', '755', document_root])
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return {'success': True, 'message': 'Backup restored successfully'}
    
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        # Clean up
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return {'success': False, 'message': str(e)}

def delete_backup(backup):
    """
    Delete a backup
    """
    try:
        # Delete local backup file if it exists
        if backup.storage_type == 'local' and backup.backup_path and os.path.exists(backup.backup_path):
            os.remove(backup.backup_path)
        
        # For remote storage, we might want to delete from remote as well
        # but for simplicity we'll just delete from the database
        
        # Delete from database
        db.session.delete(backup)
        db.session.commit()
        
        return {'success': True, 'message': 'Backup deleted successfully'}
    
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        return {'success': False, 'message': str(e)}

def get_backup_file(backup):
    """
    Get a backup file for download
    """
    try:
        if backup.storage_type == 'local':
            if not os.path.exists(backup.backup_path):
                return {'success': False, 'message': 'Backup file not found'}
            
            return {'success': True, 'file_path': backup.backup_path}
        else:
            # For remote storage, we need to download it first
            temp_dir = os.path.join(TEMP_BACKUP_PATH, str(uuid.uuid4()))
            os.makedirs(temp_dir, exist_ok=True)
            
            if backup.storage_type == 'sftp':
                # Get the remote storage credentials
                remote_storage = RemoteStorage.query.filter_by(user_id=backup.user_id, storage_type='sftp').first()
                if not remote_storage:
                    return {'success': False, 'message': 'SFTP credentials not found'}
                
                credentials = json.loads(remote_storage.credentials.replace("'", "\""))
                temp_file = os.path.join(temp_dir, os.path.basename(backup.remote_path))
                
                download_result = sftp_download(
                    host=credentials['host'],
                    port=int(credentials['port']),
                    username=credentials['username'],
                    password=credentials['password'],
                    key_file=credentials['key_file'],
                    remote_path=backup.remote_path,
                    local_path=temp_file
                )
                
                if not download_result['success']:
                    shutil.rmtree(temp_dir)
                    return {'success': False, 'message': f"SFTP download failed: {download_result['message']}"}
                
                return {'success': True, 'file_path': temp_file, 'temp_dir': temp_dir}
            
            elif backup.storage_type == 'gdrive' or backup.storage_type == 'onedrive':
                # This would use OAuth to download from Google Drive or OneDrive
                # For simplicity, we'll just log a message
                logger.warning(f"Download from {backup.storage_type} is not implemented in this development version")
                shutil.rmtree(temp_dir)
                return {'success': False, 'message': f"Download from {backup.storage_type} not implemented"}
    
    except Exception as e:
        logger.error(f"Error getting backup file: {str(e)}")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return {'success': False, 'message': str(e)}

def setup_backup_jobs(scheduler):
    """
    Set up backup schedules in the scheduler
    """
    try:
        from app import app
        
        with app.app_context():
            schedules = BackupSchedule.query.filter_by(enabled=True).all()
            
            for schedule in schedules:
                setup_backup_schedule(schedule, scheduler)
        
        logger.info(f"Set up {len(schedules)} backup schedules")
    except Exception as e:
        logger.error(f"Error setting up backup jobs: {str(e)}")

def setup_backup_schedule(schedule, scheduler):
    """
    Set up a single backup schedule
    """
    from app import app
    
    job_id = f"backup_{schedule.id}"
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    # Function to run the backup
    def run_backup():
        with app.app_context():
            try:
                # Get fresh data from database
                schedule_obj = BackupSchedule.query.get(schedule.id)
                if not schedule_obj or not schedule_obj.enabled:
                    return
                
                domain = Domain.query.get(schedule_obj.domain_id)
                if not domain:
                    logger.error(f"Domain not found for backup schedule {schedule_obj.id}")
                    return
                
                site = WordPressSite.query.filter_by(domain_id=domain.id).first()
                
                # Create the backup
                backup_result = create_backup(
                    domain=domain,
                    site=site,
                    backup_type=schedule_obj.backup_type,
                    storage_type=schedule_obj.storage_type,
                    remote_storage_id=None,  # Would need to be stored in the schedule
                    remote_path=schedule_obj.remote_path,
                    user_id=schedule_obj.user_id
                )
                
                if backup_result['success']:
                    logger.info(f"Scheduled backup created successfully: {backup_result['backup_name']}")
                    
                    # Update last run time
                    schedule_obj.last_run = datetime.utcnow()
                    db.session.commit()
                    
                    # Clean up old backups based on retention count
                    if schedule_obj.retention_count > 0:
                        old_backups = Backup.query.filter_by(
                            domain_id=domain.id,
                            backup_type=schedule_obj.backup_type,
                            storage_type=schedule_obj.storage_type
                        ).order_by(Backup.created_at.desc()).offset(schedule_obj.retention_count).all()
                        
                        for old_backup in old_backups:
                            delete_backup(old_backup)
                else:
                    logger.error(f"Scheduled backup failed: {backup_result['message']}")
            except Exception as e:
                logger.error(f"Error in scheduled backup: {str(e)}")
    
    # Set up the job based on frequency
    if schedule.frequency == 'daily':
        scheduler.add_job(
            run_backup,
            'cron',
            hour=schedule.hour,
            minute=schedule.minute,
            id=job_id,
            replace_existing=True
        )
    elif schedule.frequency == 'weekly':
        scheduler.add_job(
            run_backup,
            'cron',
            day_of_week=schedule.day_of_week,
            hour=schedule.hour,
            minute=schedule.minute,
            id=job_id,
            replace_existing=True
        )
    elif schedule.frequency == 'monthly':
        scheduler.add_job(
            run_backup,
            'cron',
            day=schedule.day_of_month,
            hour=schedule.hour,
            minute=schedule.minute,
            id=job_id,
            replace_existing=True
        )
    
    return True
