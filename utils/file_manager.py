import os
import shutil
import logging
import mimetypes
from werkzeug.utils import secure_filename
from datetime import datetime

logger = logging.getLogger(__name__)

def list_directory(directory_path):
    """
    List contents of a directory
    
    Args:
        directory_path (str): Path to the directory
        
    Returns:
        dict: Dictionary with directory contents and metadata
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            
        items = []
        
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            stats = os.stat(item_path)
            
            is_dir = os.path.isdir(item_path)
            
            # Get file type/extension
            if is_dir:
                item_type = 'directory'
                mime_type = 'directory'
                size = get_directory_size(item_path)
            else:
                mime_type, _ = mimetypes.guess_type(item_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                item_type = mime_type.split('/')[0] if mime_type else 'unknown'
                size = stats.st_size
            
            # Last modified time
            mod_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            items.append({
                'name': item,
                'path': os.path.relpath(item_path, directory_path),
                'type': item_type,
                'mime_type': mime_type,
                'size': size,
                'size_formatted': format_size(size),
                'is_dir': is_dir,
                'modified': mod_time
            })
        
        # Sort items: directories first, then by name
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        # Get parent directory
        parent_dir = os.path.dirname(directory_path)
        
        return {
            'success': True,
            'directory': directory_path,
            'parent': parent_dir if parent_dir != directory_path else None,
            'items': items
        }
    
    except Exception as e:
        logger.error(f"Error listing directory {directory_path}: {str(e)}")
        return {'success': False, 'message': str(e)}

def read_file(file_path):
    """
    Read contents of a file
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        dict: Dictionary with file contents and metadata
    """
    try:
        if not os.path.exists(file_path):
            return {'success': False, 'message': 'File not found'}
        
        if os.path.isdir(file_path):
            return {'success': False, 'message': 'Path is a directory, not a file'}
        
        # Get file stats
        stats = os.stat(file_path)
        size = stats.st_size
        mod_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Check if file is binary
        is_binary = is_binary_file(file_path, mime_type)
        
        # Read file contents
        if is_binary:
            content = None  # Don't read binary files
            is_text = False
        else:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            is_text = True
        
        return {
            'success': True,
            'path': file_path,
            'name': os.path.basename(file_path),
            'content': content,
            'size': size,
            'size_formatted': format_size(size),
            'mime_type': mime_type,
            'is_text': is_text,
            'is_binary': is_binary,
            'modified': mod_time
        }
    
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return {'success': False, 'message': str(e)}

def write_file(file_path, content):
    """
    Write content to a file
    
    Args:
        file_path (str): Path to the file
        content (str): Content to write to the file
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"File {file_path} written successfully")
        return {'success': True, 'message': 'File saved successfully'}
    
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {str(e)}")
        return {'success': False, 'message': str(e)}

def create_directory(parent_dir, dir_name):
    """
    Create a new directory
    
    Args:
        parent_dir (str): Path to the parent directory
        dir_name (str): Name of the new directory
        
    Returns:
        dict: Result of the operation
    """
    new_dir = os.path.join(parent_dir, dir_name)
    try:
        os.makedirs(new_dir, exist_ok=True)
        logger.info(f"Directory {new_dir} created successfully")
        return {'success': True, 'message': 'Directory created successfully'}
    except Exception as e:
        logger.error(f"Error creating directory {new_dir}: {str(e)}")
        return {'success': False, 'message': str(e)}

def delete_file_or_dir(path):
    """
    Delete a file or directory
    
    Args:
        path (str): Path to the file or directory
        
    Returns:
        dict: Result of the operation
    """
    try:
        if not os.path.exists(path):
            return {'success': False, 'message': 'File or directory not found'}
        
        if os.path.isdir(path):
            shutil.rmtree(path)
            message = 'Directory deleted successfully'
        else:
            os.remove(path)
            message = 'File deleted successfully'
        
        logger.info(f"Deleted {path}")
        return {'success': True, 'message': message}
    
    except Exception as e:
        logger.error(f"Error deleting {path}: {str(e)}")
        return {'success': False, 'message': str(e)}

def upload_file(upload_dir, file, filename=None):
    """
    Upload a file
    
    Args:
        upload_dir (str): Directory to upload the file to
        file: File object (from Flask request.files)
        filename (str, optional): Custom filename (if None, use secure version of file.filename)
        
    Returns:
        dict: Result of the operation
    """
    try:
        if not filename:
            filename = secure_filename(file.filename)
        
        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        logger.info(f"File uploaded to {file_path}")
        return {'success': True, 'message': 'File uploaded successfully', 'path': file_path}
    
    except Exception as e:
        logger.error(f"Error uploading file to {upload_dir}: {str(e)}")
        return {'success': False, 'message': str(e)}

def get_directory_size(directory_path):
    """
    Calculate the total size of a directory
    
    Args:
        directory_path (str): Path to the directory
        
    Returns:
        int: Size in bytes
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    
    return total_size

def format_size(size_bytes):
    """
    Format size in bytes to human readable format
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def is_binary_file(file_path, mime_type=None):
    """
    Check if a file is binary
    
    Args:
        file_path (str): Path to the file
        mime_type (str, optional): Mime type of the file
        
    Returns:
        bool: Whether the file is binary
    """
    # Known text mime types
    text_mimes = [
        'text/', 'application/json', 'application/xml', 'application/javascript',
        'application/x-httpd-php', 'application/x-sh'
    ]
    
    # Check by mime type first
    if mime_type:
        for text_mime in text_mimes:
            if mime_type.startswith(text_mime):
                return False
    
    # Check by file extension
    text_extensions = ['.txt', '.html', '.css', '.js', '.json', '.xml', '.md', '.php', '.py', '.rb', '.sh', '.log', '.ini', '.conf']
    ext = os.path.splitext(file_path)[1].lower()
    if ext in text_extensions:
        return False
    
    # Try to read the file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            sample = f.read(1024)
        
        # If there are too many non-printable characters, it's binary
        non_printable = sum(1 for c in sample if not (32 <= ord(c) <= 126) and c not in '\n\r\t')
        if non_printable / len(sample) > 0.3:
            return True
        
        return False
    except:
        # If there's an error reading as text, it's probably binary
        return True