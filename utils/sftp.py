import os
import logging
import paramiko
from models import SSHKey

logger = logging.getLogger(__name__)

def get_ssh_connection(hostname, port, username, password=None, key_id=None):
    """
    Create an SSH connection using either password or SSH key
    
    Args:
        hostname (str): The hostname or IP address
        port (int): The SSH port
        username (str): The SSH username
        password (str, optional): The SSH password
        key_id (int, optional): The ID of the SSH key in the database
        
    Returns:
        paramiko.SSHClient: The SSH client connection
    """
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Use SSH key if provided
        if key_id:
            from app import db
            ssh_key = SSHKey.query.get(key_id)
            if not ssh_key:
                raise ValueError("SSH key not found")
            
            # Write private key to temporary file
            key_path = "/tmp/temp_ssh_key"
            with open(key_path, 'w') as f:
                f.write(ssh_key.private_key)
            os.chmod(key_path, 0o600)  # Set appropriate permissions
            
            # Connect using key
            try:
                key = paramiko.RSAKey.from_private_key_file(key_path)
                client.connect(hostname, port=port, username=username, pkey=key)
            finally:
                # Clean up temporary key file
                os.remove(key_path)
        else:
            # Connect using password
            client.connect(hostname, port=port, username=username, password=password)
        
        return client
    except Exception as e:
        logger.error(f"Failed to establish SSH connection: {e}")
        raise

def sftp_upload(local_path, remote_path, host, port, username, password=None, key_file=None):
    """
    Upload a file to a remote SFTP server
    
    Args:
        local_path (str): Path to the local file
        remote_path (str): Path on the remote server
        host (str): The hostname or IP address
        port (int): The SSH port
        username (str): The SSH username
        password (str, optional): The SSH password
        key_file (str, optional): Path to the SSH key file
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        client = get_ssh_connection(hostname, port, username, password, key_id)
        sftp = client.open_sftp()
        
        # Create remote directory if it doesn't exist
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.chdir(remote_dir)
        except IOError:
            # Directory doesn't exist, create it
            dirs = remote_dir.split('/')
            current_dir = ''
            for d in dirs:
                if not d:
                    continue
                current_dir += '/' + d
                try:
                    sftp.chdir(current_dir)
                except IOError:
                    sftp.mkdir(current_dir)
                    sftp.chdir(current_dir)
        
        # Upload file
        sftp.put(local_file, remote_path)
        sftp.close()
        client.close()
        
        logger.info(f"Successfully uploaded {local_file} to {remote_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload file to SFTP: {e}")
        return False

def sftp_download(remote_file, local_path, hostname, port, username, password=None, key_id=None):
    """
    Download a file from a remote SFTP server
    
    Args:
        remote_file (str): Path on the remote server
        local_path (str): Path to save the local file
        hostname (str): The hostname or IP address
        port (int): The SSH port
        username (str): The SSH username
        password (str, optional): The SSH password
        key_id (int, optional): The ID of the SSH key in the database
        
    Returns:
        bool: Whether the download was successful
    """
    try:
        client = get_ssh_connection(hostname, port, username, password, key_id)
        sftp = client.open_sftp()
        
        # Create local directory if it doesn't exist
        local_dir = os.path.dirname(local_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        
        # Download file
        sftp.get(remote_file, local_path)
        sftp.close()
        client.close()
        
        logger.info(f"Successfully downloaded {remote_file} to {local_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download file from SFTP: {e}")
        return False

def sftp_list_files(remote_path, hostname, port, username, password=None, key_id=None):
    """
    List files in a remote directory via SFTP
    
    Args:
        remote_path (str): Path on the remote server
        hostname (str): The hostname or IP address
        port (int): The SSH port
        username (str): The SSH username
        password (str, optional): The SSH password
        key_id (int, optional): The ID of the SSH key in the database
        
    Returns:
        list: List of files in the directory
    """
    try:
        client = get_ssh_connection(hostname, port, username, password, key_id)
        sftp = client.open_sftp()
        
        # List files
        files = sftp.listdir(remote_path)
        sftp.close()
        client.close()
        
        return files
    except Exception as e:
        logger.error(f"Failed to list files via SFTP: {e}")
        return []