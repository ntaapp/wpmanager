document.addEventListener('DOMContentLoaded', function() {
    // WordPress installation form validation
    const installWordPressForm = document.getElementById('installWordPressForm');
    if (installWordPressForm) {
        installWordPressForm.addEventListener('submit', function(e) {
            const domainId = document.getElementById('domain_id').value;
            const adminUser = document.getElementById('admin_user').value;
            const adminEmail = document.getElementById('admin_email').value;
            const adminPassword = document.getElementById('admin_password').value;
            const siteTitle = document.getElementById('site_title').value;
            
            // Basic validation
            if (!domainId || !adminUser || !adminEmail || !adminPassword || !siteTitle) {
                e.preventDefault();
                showAlert('All fields are required', 'danger');
                return;
            }
            
            // Password strength validation
            if (adminPassword.length < 8) {
                e.preventDefault();
                showAlert('Password must be at least 8 characters long', 'danger');
                return;
            }
            
            // Email format validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(adminEmail)) {
                e.preventDefault();
                showAlert('Please enter a valid email address', 'danger');
                return;
            }
            
            // Show installation in progress message
            if (!confirm('WordPress installation will begin. This may take a few minutes. Continue?')) {
                e.preventDefault();
                return;
            }
            
            showAlert('WordPress installation started. Please wait...', 'info');
        });
    }
    
    // Handle OpenLiteSpeed configuration
    document.querySelectorAll('.configure-ols-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Configure OpenLiteSpeed for this WordPress site?')) {
                e.preventDefault();
                return;
            }
            
            showAlert('OpenLiteSpeed configuration started. Please wait...', 'info');
        });
    });
    
    // Handle WordPress site deletion confirmation
    document.querySelectorAll('.delete-wp-btn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const domainName = this.getAttribute('data-domain-name');
            const form = this.closest('form');
            
            if (confirm(`Are you sure you want to delete the WordPress site for "${domainName}"? This will remove all files and the database. This action cannot be undone.`)) {
                form.submit();
            }
        });
    });
    
    // WordPress status checks
    document.querySelectorAll('.wp-status-badge').forEach(async function(badge) {
        const siteId = badge.getAttribute('data-site-id');
        if (!siteId) return;
        
        try {
            const response = await fetch(`/wordpress/api/status/${siteId}`);
            const data = await response.json();
            
            let statusClass = 'secondary';
            let statusText = 'Unknown';
            
            if (data.error) {
                statusClass = 'danger';
                statusText = 'Error';
            } else if (data.accessible) {
                statusClass = 'success';
                statusText = 'Online';
            } else if (data.wordpress_exists) {
                statusClass = 'warning';
                statusText = 'Installed (Offline)';
            } else {
                statusClass = 'danger';
                statusText = 'Not Installed';
            }
            
            badge.classList.remove('bg-secondary');
            badge.classList.add(`bg-${statusClass}`);
            badge.textContent = statusText;
            
            // Add tooltip with details
            const tooltipText = `
                WordPress Files: ${data.wordpress_exists ? 'Yes' : 'No'}<br>
                wp-config.php: ${data.has_wp_config ? 'Yes' : 'No'}<br>
                wp-content: ${data.has_wp_content ? 'Yes' : 'No'}<br>
                Website Accessible: ${data.accessible ? 'Yes' : 'No'}
            `;
            
            badge.setAttribute('data-bs-toggle', 'tooltip');
            badge.setAttribute('data-bs-html', 'true');
            badge.setAttribute('title', tooltipText);
            
            // Initialize tooltip
            new bootstrap.Tooltip(badge);
            
        } catch (error) {
            console.error('Error checking WordPress status:', error);
            badge.textContent = 'Status Error';
            badge.classList.remove('bg-secondary');
            badge.classList.add('bg-danger');
        }
    });
    
    // Generate random password for WordPress admin
    const generatePasswordBtn = document.getElementById('generate-password');
    const adminPasswordInput = document.getElementById('admin_password');
    
    if (generatePasswordBtn && adminPasswordInput) {
        generatePasswordBtn.addEventListener('click', function() {
            const length = 12;
            const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+";
            let password = "";
            
            for (let i = 0; i < length; i++) {
                const randomIndex = Math.floor(Math.random() * charset.length);
                password += charset[randomIndex];
            }
            
            adminPasswordInput.value = password;
            adminPasswordInput.type = 'text';
            
            setTimeout(() => {
                adminPasswordInput.type = 'password';
            }, 5000);
        });
    }
});
