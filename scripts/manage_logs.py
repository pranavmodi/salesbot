#!/usr/bin/env python3
"""
Log Management Script

Provides CLI utilities for managing application logs.
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.log_manager import log_manager

def info():
    """Display log file information."""
    print("=== SalesBot Log Information ===")
    info = log_manager.get_log_info()
    
    print(f"Log Directory: {info['log_directory']}")
    print(f"Current Log File: {info['current_log_file']}")
    print(f"Total Files: {info['total_files']}")
    print()
    
    print("Log Files:")
    for file_info in info['files']:
        current_marker = " [CURRENT]" if file_info['is_current'] else ""
        print(f"  {file_info['name']}: {file_info['size_mb']} MB (modified: {file_info['modified']}){current_marker}")

def tail(lines=100):
    """Display the last N lines from the current log file."""
    print(f"=== Last {lines} lines from current log ===")
    log_lines = log_manager.read_log_tail(lines=lines)
    
    if not log_lines:
        print("No log lines found or log file doesn't exist.")
        return
    
    for line in log_lines:
        print(line)

def search(term, case_sensitive=False):
    """Search for a term in the current log file."""
    print(f"=== Searching for '{term}' (case_sensitive={case_sensitive}) ===")
    results = log_manager.search_logs(term, case_sensitive=case_sensitive)
    
    if not results:
        print("No matches found.")
        return
    
    print(f"Found {len(results)} matches:")
    for result in results:
        print(result)

def errors(hours=24):
    """Display recent errors and warnings."""
    print(f"=== Recent errors and warnings (last {hours} hours) ===")
    errors = log_manager.get_recent_errors(hours=hours)
    
    if not errors:
        print("No errors or warnings found.")
        return
    
    print(f"Found {len(errors)} error/warning entries:")
    for error in errors:
        print(error)

def cleanup(hours=48):
    """Clean up old log files."""
    print(f"=== Cleaning up log files older than {hours} hours ===")
    removed = log_manager.cleanup_old_logs(keep_hours=hours)
    print(f"Cleanup completed. Removed {removed} old files.")

def main():
    parser = argparse.ArgumentParser(description='SalesBot Log Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    subparsers.add_parser('info', help='Display log file information')
    
    # Tail command
    tail_parser = subparsers.add_parser('tail', help='Display last N lines from log')
    tail_parser.add_argument('-n', '--lines', type=int, default=100, help='Number of lines to display (default: 100)')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for term in logs')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('-c', '--case-sensitive', action='store_true', help='Case sensitive search')
    
    # Errors command
    errors_parser = subparsers.add_parser('errors', help='Display recent errors and warnings')
    errors_parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old log files')
    cleanup_parser.add_argument('-k', '--keep-hours', type=int, default=48, help='Hours of logs to keep (default: 48)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'info':
            info()
        elif args.command == 'tail':
            tail(args.lines)
        elif args.command == 'search':
            search(args.term, args.case_sensitive)
        elif args.command == 'errors':
            errors(args.hours)
        elif args.command == 'cleanup':
            cleanup(args.keep_hours)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()