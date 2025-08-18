#!/usr/bin/env python3
"""
Detect files that changed outside of Claude's control
Used by Stop hook to trigger incremental updates
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


def get_file_mtime(file_path):
    """Get file modification time as timestamp."""
    try:
        return os.path.getmtime(file_path)
    except:
        return 0


def detect_external_changes(index_path, project_root):
    """
    Detect files that were modified externally since last index.
    Returns list of changed file paths.
    """
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Get index timestamp
        index_time = os.path.getmtime(index_path)
        changed_files = []
        
        # Check indexed files for changes
        for rel_path, file_info in index.get('files', {}).items():
            file_path = os.path.join(project_root, rel_path)
            
            # Skip if file no longer exists
            if not os.path.exists(file_path):
                changed_files.append(rel_path)
                continue
            
            # Check if file was modified after index
            file_mtime = get_file_mtime(file_path)
            if file_mtime > index_time:
                # Skip if it was updated by hook (has updated_at timestamp)
                if 'updated_at' in file_info:
                    try:
                        # Parse ISO format timestamp
                        updated_at = datetime.fromisoformat(file_info['updated_at']).timestamp()
                        # If hook update is recent, skip
                        if abs(file_mtime - updated_at) < 2:  # 2 second tolerance
                            continue
                    except:
                        pass
                
                changed_files.append(rel_path)
        
        # Also scan for new files not in index
        root_path = Path(project_root)
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.rb', '.php'}
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in code_extensions:
                rel_path = str(file_path.relative_to(root_path))
                
                # Skip ignored directories
                if any(part in {'.git', 'node_modules', '__pycache__', '.venv', 'venv'} 
                       for part in file_path.parts):
                    continue
                
                # If not in index and created after index, it's new
                if rel_path not in index.get('files', {}) and get_file_mtime(file_path) > index_time:
                    changed_files.append(rel_path)
        
        return changed_files
        
    except Exception as e:
        # If anything fails, return empty list
        return []


def check_git_changes(project_root):
    """
    Optional: Check git for uncommitted changes as additional signal.
    Returns True if working directory has changes.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


if __name__ == '__main__':
    # Test mode
    import sys
    if len(sys.argv) > 2:
        index_path = sys.argv[1]
        project_root = sys.argv[2]
        
        changes = detect_external_changes(index_path, project_root)
        if changes:
            print(f"Found {len(changes)} external changes:")
            for path in changes[:10]:  # Show first 10
                print(f"  - {path}")
        else:
            print("No external changes detected")