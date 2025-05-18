document.addEventListener('DOMContentLoaded', function() {
    // Database creation form validation
    const createDatabaseForm = document.getElementById('createDatabaseForm');
    if (createDatabaseForm) {
        createDatabaseForm.addEventListener('submit', function(e) {
            const dbName = document.getElementById('db_name').value;
            const dbUser = document.getElementById('db_user').value;
            
            // Basic validation
            if (!dbName || !dbUser) {
                e.preventDefault();
                showAlert('Database name and user are required', 'danger');
                return;
            }
            
            // Validate database name (alphanumeric and underscore only)
            const nameRegex = /^[a-zA-Z0-9_]+$/;
            if (!nameRegex.test(dbName)) {
                e.preventDefault();
                showAlert('Database name can only contain letters, numbers, and underscores', 'danger');
                return;
            }
            
            // Validate database user (alphanumeric and underscore only)
            if (!nameRegex.test(dbUser)) {
                e.preventDefault();
                showAlert('Database user can only contain letters, numbers, and underscores', 'danger');
                return;
            }
        });
    }
    
    // Handle database deletion confirmation
    document.querySelectorAll('.delete-db-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const dbName = this.getAttribute('data-db-name');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to delete the database "${dbName}"? This action cannot be undone.`)) {
                form.submit();
            }
        });
    });
    
    // Generate random password for database
    const generateDbPasswordBtn = document.getElementById('generate-db-password');
    const dbPasswordInput = document.getElementById('db_password');
    
    if (generateDbPasswordBtn && dbPasswordInput) {
        generateDbPasswordBtn.addEventListener('click', function() {
            const length = 16;
            const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_-";
            let password = "";
            
            for (let i = 0; i < length; i++) {
                const randomIndex = Math.floor(Math.random() * charset.length);
                password += charset[randomIndex];
            }
            
            dbPasswordInput.value = password;
            dbPasswordInput.type = 'text';
            
            setTimeout(() => {
                dbPasswordInput.type = 'password';
            }, 5000);
        });
    }
    
    // File upload validation for SQL import
    const importDbForm = document.getElementById('importDbForm');
    if (importDbForm) {
        importDbForm.addEventListener('submit', function(e) {
            const dbName = document.getElementById('import_db_name').value;
            const sqlFile = document.getElementById('sql_file').files[0];
            
            if (!dbName) {
                e.preventDefault();
                showAlert('Please select a database', 'danger');
                return;
            }
            
            if (!sqlFile) {
                e.preventDefault();
                showAlert('Please select a SQL file to upload', 'danger');
                return;
            }
            
            // Check file extension
            const fileExt = sqlFile.name.split('.').pop().toLowerCase();
            if (fileExt !== 'sql') {
                e.preventDefault();
                showAlert('Only .sql files are allowed', 'danger');
                return;
            }
            
            // Check file size (max 100MB)
            const maxSize = 100 * 1024 * 1024; // 100MB in bytes
            if (sqlFile.size > maxSize) {
                e.preventDefault();
                showAlert('SQL file size must be less than 100MB', 'danger');
                return;
            }
            
            showAlert('Database import started. This may take some time for large databases.', 'info');
        });
    }
    
    // Load database list for selects
    const loadDatabases = async function() {
        try {
            const response = await fetch('/database/api/list');
            const data = await response.json();
            
            if (data.error) {
                console.error('Error loading databases:', data.error);
                return;
            }
            
            // Populate database selects
            document.querySelectorAll('.database-select').forEach(select => {
                // Clear existing options except the default one
                while (select.options.length > 1) {
                    select.remove(1);
                }
                
                // Add database options
                data.databases.forEach(dbName => {
                    const option = document.createElement('option');
                    option.value = dbName;
                    option.textContent = dbName;
                    
                    // Mark WordPress databases
                    if (data.wordpress_dbs.includes(dbName)) {
                        option.textContent += ' (WordPress)';
                    }
                    
                    select.appendChild(option);
                });
            });
            
        } catch (error) {
            console.error('Error loading databases:', error);
        }
    };
    
    // Load databases if there are any database selects on the page
    if (document.querySelector('.database-select')) {
        loadDatabases();
    }
    
    // Handle SQL file selection display
    const sqlFileInput = document.getElementById('sql_file');
    const sqlFileLabel = document.querySelector('label[for="sql_file"]');
    
    if (sqlFileInput && sqlFileLabel) {
        sqlFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                const fileSize = formatBytes(this.files[0].size);
                sqlFileLabel.textContent = `${fileName} (${fileSize})`;
            } else {
                sqlFileLabel.textContent = 'Choose SQL file';
            }
        });
    }
});
