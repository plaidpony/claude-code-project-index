#!/usr/bin/env python3
"""
PostToolUse hook for PROJECT_INDEX.json incremental updates
Phase 2: Workspace-Aware Update Hook with intelligent routing

Features:
- Workspace detection and file-to-workspace routing
- Selective workspace index updates
- Cross-workspace dependency cascade updates
- Performance optimization with intelligent caching
- 100% backward compatibility with single-repo setups
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Set
import time

# Workspace management cache for performance
_workspace_cache = {}
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes

# Try to find and import utilities from the project or system location
def find_project_modules():
    """Find project modules (index_utils, workspace_config, etc.) in project or system location."""
    current_dir = Path(os.getcwd())
    
    # First, search up the directory tree for project-local modules
    check_dir = current_dir
    while check_dir != check_dir.parent:
        scripts_dir = check_dir / 'scripts'
        if (scripts_dir / 'index_utils.py').exists():
            sys.path.insert(0, str(scripts_dir))
            return True
        
        # Check if index_utils.py is directly in the directory
        utils_path = check_dir / 'index_utils.py'
        if utils_path.exists():
            sys.path.insert(0, str(check_dir))
            return True
        check_dir = check_dir.parent
    
    # If not found in project tree, try the system location
    system_scripts_path = Path.home() / '.claude-code-project-index' / 'scripts'
    if (system_scripts_path / 'index_utils.py').exists():
        sys.path.insert(0, str(system_scripts_path))
        return True
    
    return False

# Import utilities if found, otherwise define minimal versions
if find_project_modules():
    try:
        from index_utils import (
            PARSEABLE_LANGUAGES, MARKDOWN_EXTENSIONS,
            extract_python_signatures, extract_javascript_signatures,
            extract_shell_signatures, extract_markdown_structure, infer_file_purpose
        )
        from workspace_config import WorkspaceConfigManager
        from workspace_indexer import WorkspaceIndexer
        WORKSPACE_SUPPORT = True
        print("Workspace support enabled", file=sys.stderr)
    except ImportError as e:
        print(f"Warning: Workspace modules not found ({e}). Using single-repo mode.", file=sys.stderr)
        WORKSPACE_SUPPORT = False
        # Fallback definitions
        PARSEABLE_LANGUAGES = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript'
        }
        MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.rst'}
else:
    WORKSPACE_SUPPORT = False
    # Minimal definitions if utils not found
    PARSEABLE_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript', 
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript'
    }
    MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.rst'}
    
    print("Warning: Project modules not found. Using minimal single-repo functionality.", file=sys.stderr)


def get_workspace_config_cached(project_root: Path) -> Optional[Dict]:
    """Get workspace configuration with caching."""
    global _workspace_cache, _cache_timestamp
    
    if not WORKSPACE_SUPPORT:
        return None
    
    current_time = time.time()
    cache_key = str(project_root.resolve())
    
    # Check cache validity
    if (cache_key in _workspace_cache and 
        current_time - _cache_timestamp < CACHE_TTL):
        return _workspace_cache[cache_key]
    
    try:
        # Load workspace configuration
        config_manager = WorkspaceConfigManager(project_root)
        registry = config_manager.load_configuration()
        
        config_data = {
            'is_monorepo': len(registry.workspaces) > 1,
            'registry': registry,
            'workspaces': {name: ws for name, ws in registry.workspaces.items()}
        }
        
        # Update cache
        _workspace_cache[cache_key] = config_data
        _cache_timestamp = current_time
        
        return config_data
        
    except Exception as e:
        print(f"Error loading workspace config: {e}", file=sys.stderr)
        return None


def get_workspace_for_file(file_path: Path, project_root: Path) -> Optional[str]:
    """Determine which workspace a file belongs to."""
    workspace_config = get_workspace_config_cached(project_root)
    
    if not workspace_config or not workspace_config['is_monorepo']:
        return None
    
    try:
        workspace = workspace_config['registry'].get_workspace_by_path(file_path)
        return workspace.name if workspace else None
    except Exception as e:
        print(f"Error determining workspace for {file_path}: {e}", file=sys.stderr)
        return None


def get_workspace_index_path(workspace_name: str, project_root: Path) -> Optional[Path]:
    """Get the path to a workspace's index file."""
    workspace_config = get_workspace_config_cached(project_root)
    
    if not workspace_config:
        return None
    
    workspace = workspace_config['workspaces'].get(workspace_name)
    if not workspace:
        return None
    
    return project_root / workspace.path / 'PROJECT_INDEX.json'


def get_dependent_workspaces(workspace_name: str, project_root: Path) -> List[str]:
    """Get list of workspaces that depend on the given workspace."""
    workspace_config = get_workspace_config_cached(project_root)
    
    if not workspace_config:
        return []
    
    try:
        return workspace_config['registry'].get_dependents(workspace_name)
    except Exception:
        return []


def update_workspace_index(workspace_name: str, file_path: Path, project_root: Path) -> bool:
    """Update a specific workspace index."""
    workspace_index_path = get_workspace_index_path(workspace_name, project_root)
    
    if not workspace_index_path:
        print(f"Warning: Could not find workspace index path for {workspace_name}", file=sys.stderr)
        return False
    
    try:
        # Update the workspace index
        success = update_file_in_index(str(workspace_index_path), str(file_path), str(project_root))
        
        if success:
            print(f"Updated workspace '{workspace_name}' index for {file_path.name}", file=sys.stderr)
        
        return success
        
    except Exception as e:
        print(f"Error updating workspace index for {workspace_name}: {e}", file=sys.stderr)
        return False


def handle_cross_workspace_dependencies(workspace_name: str, project_root: Path) -> None:
    """Handle cascade updates for dependent workspaces."""
    dependent_workspaces = get_dependent_workspaces(workspace_name, project_root)
    
    if not dependent_workspaces:
        return
    
    print(f"Cascading updates to dependent workspaces: {', '.join(dependent_workspaces)}", file=sys.stderr)
    
    for dependent_ws in dependent_workspaces:
        try:
            # Trigger reindex of dependent workspace
            workspace_index_path = get_workspace_index_path(dependent_ws, project_root)
            if workspace_index_path and workspace_index_path.exists():
                # Mark the dependent workspace for reindex by updating its metadata
                with open(workspace_index_path, 'r') as f:
                    index = json.load(f)
                
                index['needs_dependency_refresh'] = True
                index['dependency_refresh_reason'] = f"Dependency {workspace_name} updated"
                index['last_dependency_update'] = datetime.now().isoformat()
                
                with open(workspace_index_path, 'w') as f:
                    json.dump(index, f, indent=2)
                    
                print(f"Marked workspace '{dependent_ws}' for dependency refresh", file=sys.stderr)
                
        except Exception as e:
            print(f"Error handling dependency cascade for {dependent_ws}: {e}", file=sys.stderr)


def update_root_index_workspace_registry(project_root: Path) -> None:
    """Update the root index workspace registry when workspace relationships change."""
    root_index_path = project_root / 'PROJECT_INDEX.json'
    
    if not root_index_path.exists():
        return
    
    try:
        with open(root_index_path, 'r') as f:
            root_index = json.load(f)
        
        workspace_config = get_workspace_config_cached(project_root)
        if not workspace_config or not workspace_config['is_monorepo']:
            return
        
        # Update monorepo section in root index
        if 'monorepo' not in root_index:
            root_index['monorepo'] = {}
        
        root_index['monorepo'].update({
            'enabled': True,
            'tool': workspace_config['registry'].detection_result.tool,
            'last_updated': datetime.now().isoformat(),
            'workspaces': {}
        })
        
        # Update workspace registry
        for name, workspace in workspace_config['workspaces'].items():
            workspace_index_path = get_workspace_index_path(name, project_root)
            
            root_index['monorepo']['workspaces'][name] = {
                'path': workspace.path,
                'index_path': str(workspace_index_path.relative_to(project_root)) if workspace_index_path else None,
                'package_manager': workspace.package_manager,
                'last_updated': datetime.now().isoformat(),
                'dependencies': workspace_config['registry'].get_dependencies(name),
                'dependents': workspace_config['registry'].get_dependents(name)
            }
        
        with open(root_index_path, 'w') as f:
            json.dump(root_index, f, indent=2)
        
        print("Updated root index workspace registry", file=sys.stderr)
        
    except Exception as e:
        print(f"Error updating root index workspace registry: {e}", file=sys.stderr)


def update_file_in_index(index_path: str, file_path: str, project_root: str) -> bool:
    """Update a single file's entry in the enhanced index."""
    try:
        # Read existing index
        if not os.path.exists(index_path):
            return False
            
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Check if index has required structure
        if 'project_structure' not in index:
            index['needs_full_reindex'] = True
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return False
        
        # Get relative path from project root
        rel_path = os.path.relpath(file_path, project_root)
        
        # Handle markdown files
        if Path(file_path).suffix in MARKDOWN_EXTENSIONS and 'extract_markdown_structure' in globals():
            try:
                doc_structure = extract_markdown_structure(Path(file_path))
                if doc_structure['sections'] or doc_structure['architecture_hints']:
                    if 'documentation_map' not in index:
                        index['documentation_map'] = {}
                    index['documentation_map'][rel_path] = doc_structure
                    
                    if 'stats' in index:
                        index['stats']['markdown_files'] = index['stats'].get('markdown_files', 0) + 1
            except:
                pass
            
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return True
        
        # Check if file is parseable
        file_ext = Path(file_path).suffix
        if file_ext not in PARSEABLE_LANGUAGES:
            if 'files' not in index:
                index['files'] = {}
            if rel_path in index['files']:
                index['files'][rel_path]['updated'] = True
                index['files'][rel_path]['updated_at'] = datetime.now().isoformat()
            else:
                index['files'][rel_path] = {
                    'language': file_ext[1:] if file_ext else 'unknown',
                    'parsed': False,
                    'updated_at': datetime.now().isoformat()
                }
            
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
            return True
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return False
        
        # Extract signatures if we have the functions
        if 'extract_python_signatures' in globals() and 'extract_javascript_signatures' in globals():
            if file_ext == '.py':
                extracted = extract_python_signatures(content)
            elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
                extracted = extract_javascript_signatures(content)
            elif file_ext in {'.sh', '.bash'} and 'extract_shell_signatures' in globals():
                extracted = extract_shell_signatures(content)
            else:
                extracted = {'functions': {}, 'classes': {}}
        else:
            # Minimal update without extraction
            extracted = {'functions': {}, 'classes': {}}
        
        # Update index entry
        if 'files' not in index:
            index['files'] = {}
            
        file_info = {
            'language': PARSEABLE_LANGUAGES[file_ext],
            'parsed': bool(extracted['functions'] or extracted['classes']),
            'functions': extracted['functions'],
            'classes': extracted['classes'],
            'updated_by_hook': True,
            'updated_at': datetime.now().isoformat()
        }
        
        # Add file purpose if we can infer it
        if 'infer_file_purpose' in globals():
            file_purpose = infer_file_purpose(Path(file_path))
            if file_purpose:
                file_info['purpose'] = file_purpose
            
        index['files'][rel_path] = file_info
        
        # Write updated index
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
            
        return True
        
    except Exception as e:
        print(f"Error updating index: {e}", file=sys.stderr)
        return False


def handle_file_update(file_path: Path, project_root: Path) -> None:
    """Handle a file update with workspace awareness."""
    start_time = time.time()
    
    try:
        # Get workspace configuration
        workspace_config = get_workspace_config_cached(project_root)
        
        if not workspace_config or not workspace_config['is_monorepo']:
            # Single-repo mode: update root index only
            root_index_path = project_root / 'PROJECT_INDEX.json'
            if root_index_path.exists():
                success = update_file_in_index(str(root_index_path), str(file_path), str(project_root))
                if success:
                    print(f"Updated {file_path.name} in PROJECT_INDEX.json", file=sys.stderr)
            return
        
        # Monorepo mode: determine workspace and route update
        workspace_name = get_workspace_for_file(file_path, project_root)
        
        if not workspace_name:
            # File doesn't belong to any workspace, update root index
            root_index_path = project_root / 'PROJECT_INDEX.json'
            if root_index_path.exists():
                success = update_file_in_index(str(root_index_path), str(file_path), str(project_root))
                if success:
                    print(f"Updated {file_path.name} in root PROJECT_INDEX.json", file=sys.stderr)
            return
        
        # Update the workspace index
        success = update_workspace_index(workspace_name, file_path, project_root)
        
        if success:
            # Handle cross-workspace dependencies
            handle_cross_workspace_dependencies(workspace_name, project_root)
            
            # Update root index workspace registry
            update_root_index_workspace_registry(project_root)
        
        elapsed_time = time.time() - start_time
        if elapsed_time > 2.0:
            print(f"Warning: Update took {elapsed_time:.2f}s (target <2s)", file=sys.stderr)
        
    except Exception as e:
        print(f"Error handling file update: {e}", file=sys.stderr)


def main():
    """Process PostToolUse hook input and update index with workspace awareness."""
    try:
        # Read hook input
        input_data = json.load(sys.stdin)
        
        # Check if this is a file modification tool
        tool_name = input_data.get('tool_name', '')
        if tool_name not in ['Write', 'Edit', 'MultiEdit']:
            return
            
        # Get file path(s)
        tool_input = input_data.get('tool_input', {})
        
        # Find project root by looking for PROJECT_INDEX.json
        current_dir = os.getcwd()
        project_root = None
        
        # Search up the directory tree for PROJECT_INDEX.json
        check_dir = Path(current_dir)
        while check_dir != check_dir.parent:
            potential_index = check_dir / 'PROJECT_INDEX.json'
            if potential_index.exists():
                project_root = check_dir
                break
            check_dir = check_dir.parent
        
        if not project_root:
            return
        
        # Handle based on tool type
        if tool_name in ['Write', 'Edit']:
            file_path = tool_input.get('file_path')
            if file_path:
                handle_file_update(Path(file_path), project_root)
        elif tool_name == 'MultiEdit':
            file_path = tool_input.get('file_path')
            if file_path:
                handle_file_update(Path(file_path), project_root)
                
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()