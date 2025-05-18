document.addEventListener('DOMContentLoaded', function() {
    // Backup form validation
    const createBackupForm = document.getElementById('createBackupForm');
    if (createBackupForm) {
        createBackupForm.addEventListener('submit', function(e) {
            const domainId = document.getElementById('domain_id').value;
            const backupType = document.getElementById('backup_type').value;
            const storageType = document.getElementById('storage_type').value;
            
            // Basic validation
            if (!domainId) {
                e.preventDefault();
                showAlert('Please select a domain', 'danger');
                return;
            }
            
            // Validate remote storage settings
            if (storageType !== 'local') {
                const remoteStorageId = document.getElementById('remote_storage_id').value;
                const remotePath = document.getElementById('remote_path').value;
                
                if (!remoteStorageId) {
                    e.preventDefault();
                    showAlert('Please select a remote storage', 'danger');
                    return;
                }
                
                if (!remotePath) {
                    e.preventDefault();
                    showAlert('Remote path is required', 'danger');
                    return;
                }
            }
            
            showAlert('Backup creation started. This may take some time depending on site size.', 'info');
        });
    }
    
    // Toggle remote storage fields based on storage type
    const storageTypeSelect = document.getElementById('storage_type');
    const remoteStorageGroup = document.getElementById('remote_storage_group');
    const remotePathGroup = document.getElementById('remote_path_group');
    
    if (storageTypeSelect && remoteStorageGroup && remotePathGroup) {
        storageTypeSelect.addEventListener('change', function() {
            if (this.value !== 'local') {
                remoteStorageGroup.classList.remove('d-none');
                remotePathGroup.classList.remove('d-none');
                document.getElementById('remote_storage_id').setAttribute('required', 'required');
                document.getElementById('remote_path').setAttribute('required', 'required');
            } else {
                remoteStorageGroup.classList.add('d-none');
                remotePathGroup.classList.add('d-none');
                document.getElementById('remote_storage_id').removeAttribute('required');
                document.getElementById('remote_path').removeAttribute('required');
            }
        });
        
        // Initialize on page load
        if (storageTypeSelect.value !== 'local') {
            remoteStorageGroup.classList.remove('d-none');
            remotePathGroup.classList.remove('d-none');
            document.getElementById('remote_storage_id').setAttribute('required', 'required');
            document.getElementById('remote_path').setAttribute('required', 'required');
        } else {
            remoteStorageGroup.classList.add('d-none');
            remotePathGroup.classList.add('d-none');
            document.getElementById('remote_storage_id').removeAttribute('required');
            document.getElementById('remote_path').removeAttribute('required');
        }
    }
    
    // Handle restore backup confirmation
    document.querySelectorAll('.restore-backup-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const backupName = this.getAttribute('data-backup-name');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to restore the backup "${backupName}"? This will overwrite the current site files and database.`)) {
                showAlert('Backup restoration started. This may take some time.', 'info');
                form.submit();
            }
        });
    });
    
    // Handle delete backup confirmation
    document.querySelectorAll('.delete-backup-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const backupName = this.getAttribute('data-backup-name');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to delete the backup "${backupName}"? This action cannot be undone.`)) {
                form.submit();
            }
        });
    });
    
    // Schedule form validation
    const scheduleForm = document.getElementById('scheduleForm');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function(e) {
            const domainId = document.getElementById('schedule_domain_id').value;
            const frequency = document.getElementById('frequency').value;
            const hour = document.getElementById('hour').value;
            const minute = document.getElementById('minute').value;
            const backupType = document.getElementById('schedule_backup_type').value;
            
            // Basic validation
            if (!domainId) {
                e.preventDefault();
                showAlert('Please select a domain', 'danger');
                return;
            }
            
            // Validate time
            if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
                e.preventDefault();
                showAlert('Please enter a valid time', 'danger');
                return;
            }
            
            // Validate day of week/month based on frequency
            if (frequency === 'weekly') {
                const dayOfWeek = document.getElementById('day_of_week').value;
                if (dayOfWeek < 0 || dayOfWeek > 6) {
                    e.preventDefault();
                    showAlert('Please select a valid day of week', 'danger');
                    return;
                }
            } else if (frequency === 'monthly') {
                const dayOfMonth = document.getElementById('day_of_month').value;
                if (dayOfMonth < 1 || dayOfMonth > 31) {
                    e.preventDefault();
                    showAlert('Please enter a valid day of month (1-31)', 'danger');
                    return;
                }
            }
            
            // Validate retention count
            const retentionCount = document.getElementById('retention_count').value;
            if (retentionCount < 1) {
                e.preventDefault();
                showAlert('Retention count must be at least 1', 'danger');
                return;
            }
        });
    }
    
    // Toggle day fields based on frequency
    const frequencySelect = document.getElementById('frequency');
    const dayOfWeekGroup = document.getElementById('day_of_week_group');
    const dayOfMonthGroup = document.getElementById('day_of_month_group');
    
    if (frequencySelect && dayOfWeekGroup && dayOfMonthGroup) {
        frequencySelect.addEventListener('change', function() {
            if (this.value === 'weekly') {
                dayOfWeekGroup.classList.remove('d-none');
                dayOfMonthGroup.classList.add('d-none');
                document.getElementById('day_of_week').setAttribute('required', 'required');
                document.getElementById('day_of_month').removeAttribute('required');
            } else if (this.value === 'monthly') {
                dayOfWeekGroup.classList.add('d-none');
                dayOfMonthGroup.classList.remove('d-none');
                document.getElementById('day_of_week').removeAttribute('required');
                document.getElementById('day_of_month').setAttribute('required', 'required');
            } else {
                dayOfWeekGroup.classList.add('d-none');
                dayOfMonthGroup.classList.add('d-none');
                document.getElementById('day_of_week').removeAttribute('required');
                document.getElementById('day_of_month').removeAttribute('required');
            }
        });
        
        // Initialize on page load
        if (frequencySelect.value === 'weekly') {
            dayOfWeekGroup.classList.remove('d-none');
            dayOfMonthGroup.classList.add('d-none');
            document.getElementById('day_of_week').setAttribute('required', 'required');
            document.getElementById('day_of_month').removeAttribute('required');
        } else if (frequencySelect.value === 'monthly') {
            dayOfWeekGroup.classList.add('d-none');
            dayOfMonthGroup.classList.remove('d-none');
            document.getElementById('day_of_week').removeAttribute('required');
            document.getElementById('day_of_month').setAttribute('required', 'required');
        } else {
            dayOfWeekGroup.classList.add('d-none');
            dayOfMonthGroup.classList.add('d-none');
            document.getElementById('day_of_week').removeAttribute('required');
            document.getElementById('day_of_month').removeAttribute('required');
        }
    }
    
    // Remote storage form validation
    const remoteStorageForm = document.getElementById('remoteStorageForm');
    if (remoteStorageForm) {
        remoteStorageForm.addEventListener('submit', function(e) {
            const storageType = document.getElementById('remote_storage_type').value;
            const storageName = document.getElementById('storage_name').value;
            
            if (!storageName) {
                e.preventDefault();
                showAlert('Storage name is required', 'danger');
                return;
            }
            
            // Validate SFTP fields
            if (storageType === 'sftp') {
                const host = document.getElementById('sftp_host').value;
                const port = document.getElementById('sftp_port').value;
                const username = document.getElementById('sftp_username').value;
                
                if (!host || !port || !username) {
                    e.preventDefault();
                    showAlert('SFTP host, port, and username are required', 'danger');
                    return;
                }
            }
            
            // Validate OAuth fields
            if (storageType === 'gdrive' || storageType === 'onedrive') {
                const clientId = document.getElementById(`${storageType}_client_id`).value;
                const clientSecret = document.getElementById(`${storageType}_client_secret`).value;
                
                if (!clientId || !clientSecret) {
                    e.preventDefault();
                    showAlert('Client ID and Client Secret are required', 'danger');
                    return;
                }
            }
        });
    }
    
    // Show relevant remote storage fields based on type
    const remoteStorageTypeSelect = document.getElementById('remote_storage_type');
    const sftpFields = document.getElementById('sftp_fields');
    const gdriveFields = document.getElementById('gdrive_fields');
    const onedriveFields = document.getElementById('onedrive_fields');
    
    if (remoteStorageTypeSelect && sftpFields && gdriveFields && onedriveFields) {
        remoteStorageTypeSelect.addEventListener('change', function() {
            sftpFields.classList.add('d-none');
            gdriveFields.classList.add('d-none');
            onedriveFields.classList.add('d-none');
            
            if (this.value === 'sftp') {
                sftpFields.classList.remove('d-none');
            } else if (this.value === 'gdrive') {
                gdriveFields.classList.remove('d-none');
            } else if (this.value === 'onedrive') {
                onedriveFields.classList.remove('d-none');
            }
        });
        
        // Initialize on page load
        sftpFields.classList.add('d-none');
        gdriveFields.classList.add('d-none');
        onedriveFields.classList.add('d-none');
        
        if (remoteStorageTypeSelect.value === 'sftp') {
            sftpFields.classList.remove('d-none');
        } else if (remoteStorageTypeSelect.value === 'gdrive') {
            gdriveFields.classList.remove('d-none');
        } else if (remoteStorageTypeSelect.value === 'onedrive') {
            onedriveFields.classList.remove('d-none');
        }
    }
});
