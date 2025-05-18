import os

# Database configuration
DB_USER = os.environ.get('PGUSER', 'admin')
DB_PASSWORD = os.environ.get('PGPASSWORD', 'admin123')
DB_HOST = os.environ.get('PGHOST', 'localhost')
DB_PORT = os.environ.get('PGPORT', '3306')
DB_NAME = os.environ.get('PGDATABASE', 'wpmanager')
DATABASE_URL = os.environ.get('DATABASE_URL', f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# WordPress configuration
WP_DEFAULT_VERSION = 'latest'
DOCUMENT_ROOT = './domains'

# Backup configuration
BACKUP_DIR = './backups'
LOCAL_BACKUP_PATH = os.path.join(BACKUP_DIR, 'local')
TEMP_BACKUP_PATH = os.path.join(BACKUP_DIR, 'temp')

# Adminer configuration
ADMINER_PATH = '/usr/share/adminer'
ADMINER_URL = '/adminer'

# OpenLiteSpeed configuration
OLS_CONFIG_PATH = '/usr/local/lsws/conf'
OLS_VHOST_PATH = '/usr/local/lsws/conf/vhosts'

# Monitoring configuration
MONITORING_TYPE = 'netdata'  # netdata or glances
NETDATA_URL = 'http://localhost:19999'
GLANCES_URL = 'http://localhost:61208'

# File browser configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# SFTP configuration
SFTP_TIMEOUT = 30  # seconds

# OAuth configuration
GDRIVE_CLIENT_ID = os.environ.get('GDRIVE_CLIENT_ID', '')
GDRIVE_CLIENT_SECRET = os.environ.get('GDRIVE_CLIENT_SECRET', '')
ONEDRIVE_CLIENT_ID = os.environ.get('ONEDRIVE_CLIENT_ID', '')
ONEDRIVE_CLIENT_SECRET = os.environ.get('ONEDRIVE_CLIENT_SECRET', '')

# Application settings
SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')

# User settings
DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
DEFAULT_ADMIN_EMAIL = 'admin@localhost'
