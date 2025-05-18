import re
import socket
import logging

logger = logging.getLogger(__name__)

def validate_domain_name(domain, is_subdomain=False, parent_domain=None):
    """
    Validate a domain name format and return whether it's valid
    
    Args:
        domain: The domain name to validate
        is_subdomain: Whether this is a subdomain
        parent_domain: The parent domain if this is a subdomain
        
    Returns:
        dict: {'valid': bool, 'message': str or None}
    """
    # Check for empty domain
    if not domain:
        return {'valid': False, 'message': "Domain name cannot be empty"}
    
    # Check domain length
    if len(domain) > 253:
        return {'valid': False, 'message': "Domain name is too long (max 253 characters)"}
    
    # Basic pattern validation
    pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63}(?<!-))*(\.[A-Za-z]{2,})$"
    if not re.match(pattern, domain):
        return {'valid': False, 'message': "Invalid domain name format"}
    
    # Check if domain has valid TLD
    if "." not in domain:
        return {'valid': False, 'message': "Domain must include a valid TLD (e.g. .com, .org)"}
    
    # Subdomain validation
    if is_subdomain and not parent_domain:
        return {'valid': False, 'message': "Parent domain is required for subdomains"}
    
    # All checks passed
    return {'valid': True, 'message': None}

def is_subdomain(domain):
    """
    Check if a domain is a subdomain and return the parent domain
    
    Returns:
        tuple: (is_subdomain, parent_domain)
    """
    parts = domain.split('.')
    
    # If we have at least 3 parts, it might be a subdomain
    if len(parts) >= 3:
        # Get the parent domain (last two parts joined with a dot)
        parent_domain = '.'.join(parts[-2:])
        
        # If TLD is something like .co.uk, we need three parts
        common_double_tlds = ['co.uk', 'com.au', 'org.uk', 'net.au']
        last_three = '.'.join(parts[-3:])
        
        for tld in common_double_tlds:
            if last_three.endswith(tld):
                parent_domain = '.'.join(parts[-3:])
                break
        
        return True, parent_domain
    
    return False, None

def domain_exists(domain):
    """
    Check if a domain exists by attempting a DNS lookup
    
    Returns:
        bool: Whether the domain exists
    """
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

def validate_database_name(name):
    """
    Validate a database name
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not name:
        return False, "Database name cannot be empty"
    
    if len(name) > 64:
        return False, "Database name is too long (max 64 characters)"
    
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        return False, "Database name can only contain letters, numbers, and underscores"
    
    return True, None

def validate_username(username):
    """
    Validate a username
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username is too short (min 3 characters)"
    
    if len(username) > 32:
        return False, "Username is too long (max 32 characters)"
    
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, None

def validate_password(password):
    """
    Validate a password strength
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 8:
        return False, "Password is too short (min 8 characters)"
    
    if len(password) > 64:
        return False, "Password is too long (max 64 characters)"
    
    # Check for at least one uppercase, one lowercase, one digit
    if not (re.search(r"[A-Z]", password) and re.search(r"[a-z]", password) and re.search(r"[0-9]", password)):
        return False, "Password must contain at least one uppercase letter, one lowercase letter, and one digit"
    
    return True, None

def validate_email(email):
    """
    Validate an email address format
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    # Basic email pattern validation
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email address format"
    
    return True, None

def validate_path(path, allowed_paths=None):
    """
    Validate a file path to prevent path traversal attacks
    
    Args:
        path (str): The path to validate
        allowed_paths (list): List of allowed paths
    
    Returns:
        dict: {'valid': bool, 'message': str or None}
    """
    if not path:
        return {'valid': False, 'message': "Path cannot be empty"}
    
    # Normalize path to prevent directory traversal
    import os
    path = os.path.normpath(path)
    
    # Check for attempts to escape with '..'
    if '..' in path:
        return {'valid': False, 'message': "Path contains invalid characters"}
    
    # Check if path is within allowed paths
    if allowed_paths:
        in_allowed_path = False
        for allowed_path in allowed_paths:
            if path.startswith(allowed_path):
                in_allowed_path = True
                break
        
        if not in_allowed_path:
            return {'valid': False, 'message': "Path is outside of allowed directories"}
    
    return {'valid': True, 'message': None}