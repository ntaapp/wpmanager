#!/bin/bash
set -e

# Auto-install script for WPManager (Python/Flask)
echo 'Installing WPManager...'

# Generate random passwords
ROOT_PASSWORD=$(openssl rand -base64 12)
DB_PASSWORD=$(openssl rand -base64 12)
JWT_SECRET=$(openssl rand -base64 32)
OLS_PASSWORD=$(openssl rand -base64 12)

# Default admin user
ADMIN_USER=admin
ADMIN_PASS=admin123
ADMIN_EMAIL=admin@localhost.com

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv mariadb-server wget curl unzip git openssl certbot rclone

# Install OpenLiteSpeed
if ! command -v /usr/local/lsws/bin/lswsctrl &> /dev/null; then
    wget https://raw.githubusercontent.com/litespeedtech/ols1clk/master/ols1clk.sh
    bash ols1clk.sh --wordpressplus no --adminpassword "$OLS_PASSWORD"
fi

# Install Netdata (monitoring)
if ! command -v netdata &> /dev/null; then
    bash <(curl -Ss https://my-netdata.io/kickstart.sh) --dont-wait
fi

# Download Adminer
mkdir -p static/adminer
wget -O static/adminer/adminer.php https://github.com/vrana/adminer/releases/download/v4.8.1/adminer-4.8.1.php

# Secure MariaDB installation
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$ROOT_PASSWORD';"
mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.user WHERE User='';"
mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
mysql -u root -p"$ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS test;"
mysql -u root -p"$ROOT_PASSWORD" -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
mysql -u root -p"$ROOT_PASSWORD" -e "FLUSH PRIVILEGES;"

# Create database and user for WPManager
mysql -u root -p"$ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS wpmanager;
CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON wpmanager.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
EOF

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install poetry
poetry install

deactivate

# Create .env file
cat > .env <<EOF
PGUSER=admin
PGPASSWORD=$DB_PASSWORD
PGHOST=localhost
PGPORT=3306
PGDATABASE=wpmanager
SESSION_SECRET=$JWT_SECRET
DEFAULT_ADMIN_USER=$ADMIN_USER
DEFAULT_ADMIN_PASSWORD=$ADMIN_PASS
DEFAULT_ADMIN_EMAIL=$ADMIN_EMAIL
EOF

# Set up backup directory
mkdir -p backups
chown -R www-data:www-data backups

# Save credentials to a secure file
cat > credentials.txt <<EOF
=== WPManager Installation Credentials ===
Please save these credentials securely. They will not be shown again.

Server Information:
------------------
Server IP: $SERVER_IP
Flask App Port: 5000

Database Credentials:
-------------------
Root Password: $ROOT_PASSWORD
WPManager DB User: admin
WPManager DB Password: $DB_PASSWORD

OpenLiteSpeed:
-------------
Admin Panel: https://$SERVER_IP:7080
Admin Username: admin
Admin Password: $OLS_PASSWORD

JWT Secret:
----------
$JWT_SECRET

App Admin User:
--------------
Username: $ADMIN_USER
Password: $ADMIN_PASS
Email: $ADMIN_EMAIL

EOF
chmod 600 credentials.txt

# Display installation completion message
echo '=================================================='
echo 'WPManager installation completed successfully!'
echo '=================================================='
echo ''
echo 'IMPORTANT: Your credentials have been saved to:'
echo "$(pwd)/credentials.txt"
echo ''
echo 'Please save these credentials securely.'
echo 'They will not be shown again.'
echo ''
echo 'You can access the application at:'
echo "Flask App: http://$SERVER_IP:5000"
echo ''
echo 'OpenLiteSpeed Admin Panel:'
echo "https://$SERVER_IP:7080"
echo ''
echo '==================================================' 