import os
import logging
import json
import tempfile
import shutil
from datetime import datetime
import uuid
from models import Domain, WordPressSite, Backup, BackupSchedule, RemoteStorage
from app import db

logger = logging.getLogger(__name__)

def create_backup(domain, site, backup_type, storage_type, remote_storage_id=None, remote_path='', user_id=None):
    """
    Create a backup for the specified domain/WordPress site
    
    This is a simplified version for the Replit environment
    """
    try:
        # Create backup directories if they don't exist
        from config import LOCAL_BACKUP_PATH, TEMP_BACKUP_PATH
        os.makedirs(LOCAL_BACKUP_PATH, exist_ok=True)
        os.makedirs(TEMP_BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        backup_name = f"{domain.name}_{backup_type}_{timestamp}"
        backup_file = f"{backup_name}.zip"
        local_backup_path = os.path.join(LOCAL_BACKUP_PATH, backup_file)
        
        # Get the document root
        document_root = site.document_root if site else os.path.join("./domains", domain.name)
        
        # Create a simple backup (zip file)
        if not os.path.exists(document_root):
            # Create an empty directory if it doesn't exist
            os.makedirs(document_root, exist_ok=True)
            
        # Create a simple backup (zip file)
        import zipfile
        
        with zipfile.ZipFile(local_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the directory and add all files
            if os.path.exists(document_root):
                for root, dirs, files in os.walk(document_root):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(document_root))
                        zipf.write(file_path, arcname)
        
        # Get backup size
        backup_size = os.path.getsize(local_backup_path)
        
        # Create backup record in database
        backup = Backup()
        backup.domain_id = domain.id
        backup.user_id = user_id if user_id else domain.user_id
        backup.backup_name = backup_name
        backup.backup_path = local_backup_path
        backup.backup_type = backup_type
        backup.storage_type = 'local'  # Always use local in the simplified version
        backup.size = backup_size
        backup.status = 'completed'
        
        db.session.add(backup)
        db.session.commit()
        
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
    
    This is a simplified version for the Replit environment
    """
    try:
        from config import TEMP_BACKUP_PATH
        
        domain = Domain.query.get(backup.domain_id)
        if not domain:
            return {'success': False, 'message': 'Domain not found'}
        
        # Get the WordPress site if available
        site = WordPressSite.query.filter_by(domain_id=domain.id).first()
        document_root = site.document_root if site else os.path.join("./domains", domain.name)
        
        # Check if the backup file exists
        if not os.path.exists(backup.backup_path):
            return {'success': False, 'message': 'Backup file not found'}
        
        # Create temporary directory for restoration
        temp_dir = os.path.join(TEMP_BACKUP_PATH, str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract the backup
        import zipfile
        with zipfile.ZipFile(backup.backup_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # First, back up the current document root (just in case)
        if os.path.exists(document_root):
            backup_dir = f"{document_root}.bak.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            shutil.move(document_root, backup_dir)
        
        # Create new document root directory
        os.makedirs(document_root, exist_ok=True)
        
        # Copy files from extracted backup
        for item in os.listdir(temp_dir):
            source = os.path.join(temp_dir, item)
            dest = os.path.join(document_root, item)
            if os.path.isdir(source):
                shutil.copytree(source, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(source, dest)
        
        # Clean up
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
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
    
    This is a simplified version for the Replit environment
    """
    try:
        # Delete local backup file if it exists
        if backup.backup_path and os.path.exists(backup.backup_path):
            os.remove(backup.backup_path)
        
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
    
    This is a simplified version for the Replit environment
    """
    try:
        if not os.path.exists(backup.backup_path):
            return {'success': False, 'message': 'Backup file not found'}
        
        return {'success': True, 'file_path': backup.backup_path}
    
    except Exception as e:
        logger.error(f"Error getting backup file: {str(e)}")
        return {'success': False, 'message': str(e)}

def setup_backup_jobs(scheduler):
    """
    Set up backup schedules in the scheduler
    
    This is a simplified version for the Replit environment
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
    
    This is a simplified version for the Replit environment
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
                    storage_type='local',  # Always use local in the simplified version
                    user_id=schedule_obj.user_id
                )
                
                if backup_result['success']:
                    # Update schedule last run time
                    schedule_obj.last_run = datetime.utcnow()
                    
                    # Calculate next run time based on frequency
                    from datetime import timedelta
                    if schedule_obj.frequency == 'daily':
                        schedule_obj.next_run = datetime.now() + timedelta(days=1)
                    elif schedule_obj.frequency == 'weekly':
                        schedule_obj.next_run = datetime.now() + timedelta(weeks=1)
                    elif schedule_obj.frequency == 'monthly':
                        # Approximate month as 30 days
                        schedule_obj.next_run = datetime.now() + timedelta(days=30)
                    
                    db.session.commit()
                    
                    # Handle backup retention
                    if schedule_obj.retention_count > 0:
                        # Get all backups for this domain/user/type
                        old_backups = Backup.query.filter_by(
                            domain_id=domain.id,
                            user_id=schedule_obj.user_id,
                            backup_type=schedule_obj.backup_type,
                            storage_type='local'
                        ).order_by(Backup.created_at.desc()).all()
                        
                        # Delete backups beyond the retention count
                        if len(old_backups) > schedule_obj.retention_count:
                            for old_backup in old_backups[schedule_obj.retention_count:]:
                                delete_backup(old_backup)
                
                else:
                    logger.error(f"Scheduled backup failed: {backup_result['message']}")
            
            except Exception as e:
                logger.error(f"Error in scheduled backup: {str(e)}")
    
    # Schedule the job based on frequency
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