import os
import logging
import platform
import psutil
import socket
import json
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

def get_system_stats():
    """
    Get system resource statistics
    
    Returns:
        dict: System stats (CPU, memory, disk, uptime, etc.)
    """
    try:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=0.5)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        memory_total = memory.total
        memory_used = memory.used
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        disk_total = disk.total
        disk_used = disk.used
        
        # Load average
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
        else:
            # Windows doesn't have getloadavg
            load_avg = [0, 0, 0]
        
        # Get uptime
        boot_time = psutil.boot_time()
        uptime_seconds = int(datetime.now().timestamp() - boot_time)
        
        # Format uptime
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_formatted = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # System info
        os_info = f"{platform.system()} {platform.release()}"
        kernel_version = platform.version()
        cpu_info = platform.processor() or "Unknown CPU"
        cpu_cores = psutil.cpu_count(logical=True)
        hostname = socket.gethostname()
        
        # Format sizes
        memory_total_formatted = format_size(memory_total)
        memory_used_formatted = format_size(memory_used)
        disk_total_formatted = format_size(disk_total)
        disk_used_formatted = format_size(disk_used)
        
        # Check service status (simulated in Replit environment)
        web_server_status = True  # Simulated as running
        database_status = True  # Simulated as running
        web_server_name = 'lsws'  # OpenLiteSpeed 
        
        return {
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'memory_total': memory_total,
            'memory_used': memory_used,
            'memory_total_formatted': memory_total_formatted,
            'memory_used_formatted': memory_used_formatted,
            'disk_usage': disk_usage,
            'disk_total': disk_total,
            'disk_used': disk_used,
            'disk_total_formatted': disk_total_formatted,
            'disk_used_formatted': disk_used_formatted,
            'load_average': load_avg,
            'uptime_seconds': uptime_seconds,
            'uptime_formatted': uptime_formatted,
            'os_info': os_info,
            'kernel_version': kernel_version,
            'cpu_info': cpu_info,
            'cpu_cores': cpu_cores,
            'hostname': hostname,
            'web_server_status': web_server_status,
            'database_status': database_status,
            'web_server_name': web_server_name
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        # Return minimal stats to prevent UI errors
        return {
            'cpu_usage': 0,
            'memory_usage': 0,
            'memory_total': 0,
            'memory_used': 0,
            'memory_total_formatted': '0B',
            'memory_used_formatted': '0B',
            'disk_usage': 0,
            'disk_total': 0,
            'disk_used': 0,
            'disk_total_formatted': '0B',
            'disk_used_formatted': '0B',
            'load_average': [0, 0, 0],
            'uptime_seconds': 0,
            'uptime_formatted': '0d 0h 0m 0s',
            'os_info': 'Unknown',
            'kernel_version': 'Unknown',
            'cpu_info': 'Unknown',
            'cpu_cores': 0,
            'hostname': 'Unknown',
            'web_server_status': False,
            'database_status': False,
            'web_server_name': 'unknown'
        }

def get_disk_usage(path='/'):
    """
    Get disk usage for a specific path
    
    Args:
        path (str): Path to check
        
    Returns:
        dict: Disk usage stats
    """
    try:
        disk = psutil.disk_usage(path)
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent,
            'total_formatted': format_size(disk.total),
            'used_formatted': format_size(disk.used),
            'free_formatted': format_size(disk.free)
        }
    except Exception as e:
        logger.error(f"Error getting disk usage for {path}: {str(e)}")
        return None

def get_network_stats():
    """
    Get network statistics
    
    Returns:
        dict: Network stats
    """
    try:
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'bytes_sent_formatted': format_size(net_io.bytes_sent),
            'bytes_recv_formatted': format_size(net_io.bytes_recv)
        }
    except Exception as e:
        logger.error(f"Error getting network stats: {str(e)}")
        return None

def get_service_status(service_name):
    """
    Get status of a system service (simulated in Replit environment)
    
    Args:
        service_name (str): Name of the service
        
    Returns:
        dict: Service status
    """
    # In Replit environment, we'll simulate service status
    try:
        # Simulate all services as running
        status = 'running'
        running = True
        
        return {
            'name': service_name,
            'status': status,
            'running': running
        }
    except Exception as e:
        logger.error(f"Error getting service status for {service_name}: {str(e)}")
        return {
            'name': service_name,
            'status': 'unknown',
            'running': False
        }

def restart_service(service_name):
    """
    Restart a system service (simulated in Replit environment)
    
    Args:
        service_name (str): Name of the service
        
    Returns:
        dict: Result of the operation
    """
    # In Replit environment, we'll simulate service restart
    try:
        # Simulate successful restart
        logger.info(f"Service restart simulation for: {service_name}")
        
        return {
            'success': True,
            'message': f'Service {service_name} restarted successfully (simulated)'
        }
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {str(e)}")
        return {'success': False, 'message': str(e)}

def get_netdata_url():
    """
    Get Netdata URL
    
    Returns:
        str: Netdata URL
    """
    # In a real environment, this would be configured to point to Netdata
    # In Replit, we'll just return a mock URL
    from config import NETDATA_URL
    return NETDATA_URL

def get_glances_url():
    """
    Get Glances URL
    
    Returns:
        str: Glances URL
    """
    # In a real environment, this would be configured to point to Glances
    # In Replit, we'll just return a mock URL
    from config import GLANCES_URL
    return GLANCES_URL

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