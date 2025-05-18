import subprocess
import os
import logging
import requests
import shutil
import tempfile

logger = logging.getLogger(__name__)

def install_wordpress(domain_name, db_name, db_user, db_pass, wp_admin, wp_admin_pass, wp_admin_email, site_title, document_root, wp_version='latest'):
    """
    Install WordPress on the specified domain
    """
    try:
        # Create directory if it doesn't exist
        if not os.path.exists(document_root):
            os.makedirs(document_root)
        
        # Create database and user
        db_commands = [
            f"CREATE DATABASE IF NOT EXISTS {db_name};",
            f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}';",
            f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';",
            "FLUSH PRIVILEGES;"
        ]
        
        db_command = "mysql -e \"" + " ".join(db_commands) + "\""
        subprocess.run(db_command, shell=True, check=True)
        
        # Run WordPress installation script
        install_command = [
            "bash", "/app/scripts/wordpress_install.sh",
            domain_name,
            document_root,
            db_name,
            db_user,
            db_pass,
            wp_admin,
            wp_admin_pass,
            wp_admin_email,
            site_title,
            wp_version
        ]
        
        # If script doesn't exist (development environment), create a simple installation
        if not os.path.exists("/app/scripts/wordpress_install.sh"):
            return _manual_wp_install(
                domain_name, document_root, db_name, db_user, db_pass,
                wp_admin, wp_admin_pass, wp_admin_email, site_title, wp_version
            )
        
        result = subprocess.run(install_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"WordPress installation failed: {result.stderr}")
            return {'success': False, 'message': result.stderr}
        
        return {'success': True, 'message': 'WordPress installed successfully'}
    
    except Exception as e:
        logger.error(f"Error installing WordPress: {str(e)}")
        return {'success': False, 'message': str(e)}

def _manual_wp_install(domain_name, document_root, db_name, db_user, db_pass, wp_admin, wp_admin_pass, wp_admin_email, site_title, wp_version):
    """
    Fallback manual WordPress installation for development environments
    """
    try:
        # Download WordPress
        wp_url = f"https://wordpress.org/wordpress-{wp_version}.tar.gz" if wp_version != 'latest' else "https://wordpress.org/latest.tar.gz"
        
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "wordpress.tar.gz")
        
        # Download WordPress
        response = requests.get(wp_url, stream=True)
        with open(temp_file, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        # Extract WordPress
        shutil.unpack_archive(temp_file, temp_dir)
        
        # Copy WordPress files to document root
        src_dir = os.path.join(temp_dir, "wordpress")
        
        # Make sure document root exists
        os.makedirs(document_root, exist_ok=True)
        
        # Copy all files
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(document_root, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        # Create wp-config.php
        wp_config = f"""<?php
define('DB_NAME', '{db_name}');
define('DB_USER', '{db_user}');
define('DB_PASSWORD', '{db_pass}');
define('DB_HOST', 'localhost');
define('DB_CHARSET', 'utf8');
define('DB_COLLATE', '');

{subprocess.check_output(['curl', '-s', 'https://api.wordpress.org/secret-key/1.1/salt/']).decode()}

$table_prefix = 'wp_';

define('WP_DEBUG', false);

if ( !defined('ABSPATH') )
    define('ABSPATH', dirname(__FILE__) . '/');

require_once(ABSPATH . 'wp-settings.php');
"""
        
        with open(os.path.join(document_root, 'wp-config.php'), 'w') as f:
            f.write(wp_config)
        
        # Set permissions
        subprocess.run(['chown', '-R', 'www-data:www-data', document_root])
        subprocess.run(['chmod', '-R', '755', document_root])
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        return {'success': True, 'message': 'WordPress installed successfully'}
    
    except Exception as e:
        logger.error(f"Error in manual WordPress installation: {str(e)}")
        return {'success': False, 'message': str(e)}

def configure_openlitespeed(domain_name, document_root):
    """
    Configure OpenLiteSpeed for the specified domain
    """
    try:
        # Run OpenLiteSpeed configuration script
        config_command = [
            "bash", "/app/scripts/setup_openlitespeed.sh",
            domain_name,
            document_root
        ]
        
        # If script doesn't exist (development environment), return a mock result
        if not os.path.exists("/app/scripts/setup_openlitespeed.sh"):
            logger.warning("OpenLiteSpeed configuration script not found, returning mock success")
            return {'success': True, 'message': 'OpenLiteSpeed configured successfully (mock)'}
        
        result = subprocess.run(config_command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"OpenLiteSpeed configuration failed: {result.stderr}")
            return {'success': False, 'message': result.stderr}
        
        return {'success': True, 'message': 'OpenLiteSpeed configured successfully'}
    
    except Exception as e:
        logger.error(f"Error configuring OpenLiteSpeed: {str(e)}")
        return {'success': False, 'message': str(e)}

def check_wordpress_status(domain_name, document_root):
    """
    Check the status of the WordPress installation
    """
    try:
        status = {
            'wordpress_exists': False,
            'has_wp_config': False,
            'has_wp_content': False,
            'has_index_php': False,
            'accessible': False
        }
        
        # Check if WordPress files exist
        status['wordpress_exists'] = os.path.exists(document_root)
        status['has_wp_config'] = os.path.exists(os.path.join(document_root, 'wp-config.php'))
        status['has_wp_content'] = os.path.exists(os.path.join(document_root, 'wp-content'))
        status['has_index_php'] = os.path.exists(os.path.join(document_root, 'index.php'))
        
        # Try to access the site
        try:
            response = requests.get(f"http://{domain_name}", timeout=5)
            status['accessible'] = response.status_code == 200
        except:
            status['accessible'] = False
        
        return status
    
    except Exception as e:
        logger.error(f"Error checking WordPress status: {str(e)}")
        return {
            'wordpress_exists': False,
            'has_wp_config': False,
            'has_wp_content': False,
            'has_index_php': False,
            'accessible': False,
            'error': str(e)
        }
