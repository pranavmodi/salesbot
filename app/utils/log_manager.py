#!/usr/bin/env python3
"""
Log Manager Utility

Provides utilities for managing and viewing application logs.
"""

import os
import glob
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class LogManager:
    """Manages application log files and provides viewing utilities."""
    
    def __init__(self, log_dir: str = None):
        if log_dir is None:
            # Default to logs directory in project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.log_dir = os.path.join(project_root, 'logs')
        else:
            self.log_dir = log_dir
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
    
    def get_log_files(self) -> List[str]:
        """Get all log files in the log directory."""
        pattern = os.path.join(self.log_dir, '*.log*')
        files = glob.glob(pattern)
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def get_current_log_file(self) -> str:
        """Get the path to the current active log file."""
        return os.path.join(self.log_dir, 'salesbot_activity.log')
    
    def get_log_info(self) -> Dict:
        """Get information about log files."""
        files = self.get_log_files()
        current_log = self.get_current_log_file()
        
        info = {
            'log_directory': self.log_dir,
            'current_log_file': current_log,
            'total_files': len(files),
            'files': []
        }
        
        for file_path in files:
            try:
                stat = os.stat(file_path)
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                info['files'].append({
                    'path': file_path,
                    'name': os.path.basename(file_path),
                    'size_bytes': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_current': file_path == current_log
                })
            except OSError as e:
                logger.warning(f"Could not get stats for log file {file_path}: {e}")
        
        return info
    
    def read_log_tail(self, lines: int = 100, file_path: str = None) -> List[str]:
        """Read the last N lines from a log file."""
        if file_path is None:
            file_path = self.get_current_log_file()
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read all lines and return the last N
                all_lines = f.readlines()
                return [line.rstrip() for line in all_lines[-lines:]]
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
            return [f"Error reading log file: {e}"]
    
    def read_log_range(self, start_time: datetime, end_time: datetime, 
                       file_path: str = None) -> List[str]:
        """Read log lines within a specific time range."""
        if file_path is None:
            file_path = self.get_current_log_file()
        
        if not os.path.exists(file_path):
            return []
        
        matching_lines = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Extract timestamp from line (format: YYYY-MM-DD HH:MM:SS)
                    if len(line) >= 19:
                        timestamp_str = line[:19]
                        try:
                            line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            if start_time <= line_time <= end_time:
                                matching_lines.append(line.rstrip())
                        except ValueError:
                            # Skip lines that don't start with timestamp
                            continue
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
            return [f"Error reading log file: {e}"]
        
        return matching_lines
    
    def search_logs(self, search_term: str, case_sensitive: bool = False,
                    file_path: str = None) -> List[str]:
        """Search for specific terms in log files."""
        if file_path is None:
            file_path = self.get_current_log_file()
        
        if not os.path.exists(file_path):
            return []
        
        matching_lines = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line_content = line.rstrip()
                    search_in = line_content if case_sensitive else line_content.lower()
                    search_for = search_term if case_sensitive else search_term.lower()
                    
                    if search_for in search_in:
                        matching_lines.append(f"{line_num}: {line_content}")
        except Exception as e:
            logger.error(f"Error searching log file {file_path}: {e}")
            return [f"Error searching log file: {e}"]
        
        return matching_lines
    
    def get_recent_errors(self, hours: int = 24, file_path: str = None) -> List[str]:
        """Get recent error and warning log entries."""
        if file_path is None:
            file_path = self.get_current_log_file()
        
        if not os.path.exists(file_path):
            return []
        
        since_time = datetime.now() - timedelta(hours=hours)
        recent_errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_content = line.rstrip()
                    if len(line_content) >= 19:
                        timestamp_str = line_content[:19]
                        try:
                            line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            if line_time >= since_time:
                                # Check if line contains error or warning
                                if any(level in line_content for level in ['ERROR', 'WARNING', 'CRITICAL']):
                                    recent_errors.append(line_content)
                        except ValueError:
                            continue
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {e}")
            return [f"Error reading log file: {e}"]
        
        return recent_errors
    
    def cleanup_old_logs(self, keep_hours: int = 48):
        """Clean up log files older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=keep_hours)
        files_removed = 0
        
        for file_path in self.get_log_files():
            try:
                # Skip the current active log file
                if file_path == self.get_current_log_file():
                    continue
                
                stat = os.stat(file_path)
                file_time = datetime.fromtimestamp(stat.st_mtime)
                
                if file_time < cutoff_time:
                    os.remove(file_path)
                    files_removed += 1
                    logger.info(f"Removed old log file: {file_path}")
            except OSError as e:
                logger.warning(f"Could not remove log file {file_path}: {e}")
        
        logger.info(f"Log cleanup completed. Removed {files_removed} old files.")
        return files_removed

# Global instance
log_manager = LogManager()