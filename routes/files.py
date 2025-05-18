from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from models import Domain, WordPressSite
from app import db
import logging
import os
import shutil
import tempfile
import mimetypes
from werkzeug.utils import secure_filename
from utils.file_manager import list_directory, read_file, write_file, create_directory, delete_file_or_dir

files_bp = Blueprint('files', __name__, url_prefix='/files')
logger = logging.getLogger(__name__)

# Get the base directory for file storage
BASE_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'WordPressManager', 'domains')

@files_bp.route('/')
@login_required
def file_manager():
    if current_user.role == 'admin':
        domains = Domain.query.all()
    else:
        domains = Domain.query.filter_by(user_id=current_user.id).all()
    
    return render_template('files.html', domains=domains)

@files_bp.route('/browse/<int:domain_id>')
@login_required
def browse(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to browse files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    path = request.args.get('path', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    full_path = os.path.join(document_root, path)
    
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
    
    try:
        directory_listing = list_directory(full_path)
        return render_template(
            'files.html', 
            domain=domain, 
            current_path=path, 
            directory_listing=directory_listing.get('items', [])
        )
    except Exception as e:
        flash(f'Error listing directory: {str(e)}', 'danger')
        logger.error(f"Error listing directory for domain {domain.name}: {str(e)}")
        return redirect(url_for('files.file_manager'))

@files_bp.route('/view/<int:domain_id>')
@login_required
def view_file(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to view files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    file_path = request.args.get('path', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in file_path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    full_path = os.path.join(document_root, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        flash('File does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))
    
    try:
        file_content = read_file(full_path)
        return render_template(
            'files.html', 
            domain=domain, 
            current_path=os.path.dirname(file_path),
            file_path=file_path,
            file_content=file_content,
            view_mode=True
        )
    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'danger')
        logger.error(f"Error reading file for domain {domain.name}: {str(e)}")
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))

@files_bp.route('/edit/<int:domain_id>', methods=['GET', 'POST'])
@login_required
def edit_file(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to edit files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    file_path = request.args.get('path', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in file_path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    full_path = os.path.join(document_root, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        flash('File does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))
    
    if request.method == 'POST':
        new_content = request.form.get('content', '')
        
        try:
            write_file(full_path, new_content)
            flash('File saved successfully.', 'success')
            logger.info(f"User {current_user.username} edited file {file_path} for domain {domain.name}")
            return redirect(url_for('files.view_file', domain_id=domain_id, path=file_path))
        except Exception as e:
            flash(f'Error saving file: {str(e)}', 'danger')
            logger.error(f"Error saving file for domain {domain.name}: {str(e)}")
    
    try:
        file_content = read_file(full_path)
        return render_template(
            'files.html', 
            domain=domain, 
            current_path=os.path.dirname(file_path),
            file_path=file_path,
            file_content=file_content,
            edit_mode=True
        )
    except Exception as e:
        flash(f'Error reading file: {str(e)}', 'danger')
        logger.error(f"Error reading file for domain {domain.name}: {str(e)}")
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))

@files_bp.route('/download/<int:domain_id>')
@login_required
def download_file(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to download files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    file_path = request.args.get('path', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in file_path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    full_path = os.path.join(document_root, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        flash('File does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))
    
    try:
        return send_file(
            full_path,
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        logger.error(f"Error downloading file for domain {domain.name}: {str(e)}")
        return redirect(url_for('files.browse', domain_id=domain_id, path=os.path.dirname(file_path)))

@files_bp.route('/upload/<int:domain_id>', methods=['POST'])
@login_required
def upload_file(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to upload files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(request.referrer)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(request.referrer)
    
    path = request.form.get('path', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    upload_dir = os.path.join(document_root, path)
    
    if not os.path.exists(upload_dir) or not os.path.isdir(upload_dir):
        flash('Upload directory does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    
    try:
        file.save(file_path)
        # Set proper permissions
        os.chmod(file_path, 0o644)
        os.chown(file_path, 33, 33)  # www-data user and group
        
        flash(f'File {filename} uploaded successfully.', 'success')
        logger.info(f"User {current_user.username} uploaded file {filename} to {path} for domain {domain.name}")
    except Exception as e:
        flash(f'Error uploading file: {str(e)}', 'danger')
        logger.error(f"Error uploading file for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('files.browse', domain_id=domain_id, path=path))

@files_bp.route('/mkdir/<int:domain_id>', methods=['POST'])
@login_required
def mkdir(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to create directories for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    path = request.form.get('path', '')
    dir_name = request.form.get('dir_name', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in path:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    parent_dir = os.path.join(document_root, path)
    
    if not os.path.exists(parent_dir) or not os.path.isdir(parent_dir):
        flash('Parent directory does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    try:
        result = create_directory(parent_dir, dir_name)
        
        if result['success']:
            flash(f'Directory {dir_name} created successfully.', 'success')
            logger.info(f"User {current_user.username} created directory {dir_name} in {path} for domain {domain.name}")
        else:
            flash(f'Error creating directory: {result["message"]}', 'danger')
            logger.error(f"Error creating directory for domain {domain.name}: {result['message']}")
    except Exception as e:
        flash(f'Error creating directory: {str(e)}', 'danger')
        logger.error(f"Error creating directory for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('files.browse', domain_id=domain_id, path=path))

@files_bp.route('/delete/<int:domain_id>', methods=['POST'])
@login_required
def delete_item(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    
    # Check if user has permission
    if domain.user_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete files for this domain.', 'danger')
        return redirect(url_for('files.file_manager'))
    
    path = request.form.get('path', '')
    item_name = request.form.get('item_name', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    
    # Ensure path doesn't go outside document root
    if '..' in path or '..' in item_name:
        flash('Invalid path.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id))
    
    parent_dir = os.path.join(document_root, path)
    item_path = os.path.join(parent_dir, item_name)
    
    if not os.path.exists(item_path):
        flash('Item does not exist.', 'danger')
        return redirect(url_for('files.browse', domain_id=domain_id, path=path))
    
    try:
        result = delete_file_or_dir(item_path)
        
        if result['success']:
            flash(f'{item_name} deleted successfully.', 'success')
            logger.info(f"User {current_user.username} deleted {item_name} in {path} for domain {domain.name}")
        else:
            flash(f'Error deleting {item_name}: {result["message"]}', 'danger')
            logger.error(f"Error deleting item for domain {domain.name}: {result['message']}")
    except Exception as e:
        flash(f'Error deleting {item_name}: {str(e)}', 'danger')
        logger.error(f"Error deleting item for domain {domain.name}: {str(e)}")
    
    return redirect(url_for('files.browse', domain_id=domain_id, path=path))

@files_bp.route('/rename/<int:domain_id>', methods=['POST'])
@login_required
def rename_item(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    if domain.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    path = request.form.get('path', '')
    old_name = request.form.get('old_name', '')
    new_name = request.form.get('new_name', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    parent_dir = os.path.join(document_root, path)
    old_path = os.path.join(parent_dir, old_name)
    new_path = os.path.join(parent_dir, new_name)
    if not os.path.exists(old_path):
        return jsonify({'success': False, 'message': 'Item does not exist'}), 404
    try:
        os.rename(old_path, new_path)
        return jsonify({'success': True, 'message': 'Renamed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@files_bp.route('/zip/<int:domain_id>', methods=['POST'])
@login_required
def zip_item(domain_id):
    import zipfile
    domain = Domain.query.get_or_404(domain_id)
    if domain.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    path = request.form.get('path', '')
    item_name = request.form.get('item_name', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    parent_dir = os.path.join(document_root, path)
    item_path = os.path.join(parent_dir, item_name)
    zip_path = os.path.join(parent_dir, f'{item_name}.zip')
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, parent_dir)
                        zipf.write(abs_path, rel_path)
            else:
                zipf.write(item_path, item_name)
        return jsonify({'success': True, 'message': 'Zipped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@files_bp.route('/unzip/<int:domain_id>', methods=['POST'])
@login_required
def unzip_item(domain_id):
    import zipfile
    domain = Domain.query.get_or_404(domain_id)
    if domain.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    path = request.form.get('path', '')
    item_name = request.form.get('item_name', '')
    document_root = os.path.join(BASE_DIR, domain.name)
    parent_dir = os.path.join(document_root, path)
    zip_path = os.path.join(parent_dir, item_name)
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(parent_dir)
        return jsonify({'success': True, 'message': 'Unzipped successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
