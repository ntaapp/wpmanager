from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin, editor, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    domains = db.relationship('Domain', backref='owner', lazy='dynamic')
    backups = db.relationship('Backup', backref='owner', lazy='dynamic')

class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_subdomain = db.Column(db.Boolean, default=False)
    parent_domain = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    wordpress_site = db.relationship('WordPressSite', backref='domain', uselist=False)
    backups = db.relationship('Backup', backref='domain', lazy='dynamic')

class WordPressSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), unique=True)
    wp_url = db.Column(db.String(100), nullable=False)
    admin_user = db.Column(db.String(64), nullable=False)
    admin_email = db.Column(db.String(120), nullable=False)
    db_name = db.Column(db.String(64), nullable=False)
    db_user = db.Column(db.String(64), nullable=False)
    db_pass = db.Column(db.String(100), nullable=False)
    document_root = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(20))
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    openlitespeed_enabled = db.Column(db.Boolean, default=False)

class Backup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    backup_name = db.Column(db.String(100), nullable=False)
    backup_path = db.Column(db.String(255), nullable=False)
    remote_path = db.Column(db.String(255))
    backup_type = db.Column(db.String(20))  # full, db, files
    storage_type = db.Column(db.String(20))  # local, gdrive, onedrive, sftp
    size = db.Column(db.Integer)  # size in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')
    notes = db.Column(db.Text)

class BackupSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    frequency = db.Column(db.String(20))  # daily, weekly, monthly
    day_of_week = db.Column(db.Integer, nullable=True)  # 0-6 (Monday is 0)
    day_of_month = db.Column(db.Integer, nullable=True)  # 1-31
    hour = db.Column(db.Integer)  # 0-23
    minute = db.Column(db.Integer)  # 0-59
    backup_type = db.Column(db.String(20))  # full, db, files
    storage_type = db.Column(db.String(20))  # local, gdrive, onedrive, sftp
    remote_path = db.Column(db.String(255), nullable=True)
    retention_count = db.Column(db.Integer, default=7)  # number of backups to keep
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    
    # Relationship with the domain
    domain = db.relationship('Domain', backref='backup_schedules')
    user = db.relationship('User', backref='backup_schedules')

class SSHKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    private_key = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='ssh_keys')

class RemoteStorage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    storage_type = db.Column(db.String(20))  # gdrive, onedrive, sftp
    name = db.Column(db.String(100), nullable=False)
    credentials = db.Column(db.Text)  # JSON for OAuth tokens or SFTP credentials
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    user = db.relationship('User', backref='remote_storages')

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
