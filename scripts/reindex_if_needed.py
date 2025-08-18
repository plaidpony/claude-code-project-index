#!/usr/bin/env python3
"""
Stop hook for PROJECT_INDEX.json workspace-aware reindexing
Phase 2: Enhanced Staleness Detection with per-workspace granularity

Features:
- Per-workspace staleness detection
- Selective reindexing of stale workspaces only  
- Workspace configuration change detection
- Workspace addition/removal handling
- Performance optimization with intelligent scheduling
- 100% backward compatibility with single-repo setups
"""

import json
import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

# Workspace management cache
_workspace_cache = {}
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes

def find_project_modules():
    """Find project modules in project or system location."""
    current_dir = Path(os.getcwd())
    
    # Search up the directory tree for project-local modules
    check_dir = current_dir
    while check_dir != check_dir.parent:
        scripts_dir = check_dir / 'scripts'
        if (scripts_dir / 'workspace_config.py').exists():
            sys.path.insert(0, str(scripts_dir))
            return True
        
        # Check if modules are directly in the directory
        if (check_dir / 'workspace_config.py').exists():
            sys.path.insert(0, str(check_dir))
            return True
        check_dir = check_dir.parent
    
    # Try the system location
    system_scripts_path = Path.home() / '.claude-code-project-index' / 'scripts'
    if (system_scripts_path / 'workspace_config.py').exists():
        sys.path.insert(0, str(system_scripts_path))
        return True
    
    return False

# Import workspace modules if available
if find_project_modules():
    try:
        from workspace_config import WorkspaceConfigManager
        from workspace_indexer import WorkspaceIndexer
        WORKSPACE_SUPPORT = True
        print("Workspace-aware reindexing enabled", file=sys.stderr)
    except ImportError as e:
        print(f"Warning: Workspace modules not found ({e}). Using single-repo mode.", file=sys.stderr)
        WORKSPACE_SUPPORT = False
else:
    WORKSPACE_SUPPORT = False
    print("Warning: Project modules not found. Using single-repo functionality.", file=sys.stderr)


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


def check_index_features(index_path: Path) -> Tuple[bool, Optional[str]]:
    """Check if index has all required features."""
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Check for required features
        if 'project_structure' not in index:
            return True, "Missing project structure tree"
        
        if index.get('tree_needs_refresh', False):
            return True, "Directory tree needs refresh"
        
        if index.get('needs_full_reindex', False):
            return True, "Full reindex requested"
        
        if index.get('needs_dependency_refresh', False):
            return True, "Dependency refresh needed"
        
        return False, None
    except:
        return True, "Cannot read index file"


def check_index_staleness(index_path: Path, threshold_hours: int = 24) -> bool:
    """Check if index is older than threshold."""
    try:
        # Check file modification time
        index_mtime = index_path.stat().st_mtime
        current_time = datetime.now().timestamp()
        age_hours = (current_time - index_mtime) / 3600
        
        return age_hours > threshold_hours
    except:
        return True  # If can't check, assume stale


def check_workspace_staleness(workspace_name: str, project_root: Path) -> Tuple[bool, Optional[str]]:
    """Check if a specific workspace is stale."""
    workspace_config = get_workspace_config_cached(project_root)
    if not workspace_config:
        return False, None
    
    workspace = workspace_config['workspaces'].get(workspace_name)
    if not workspace:
        return True, f"Workspace '{workspace_name}' no longer exists"
    
    # Get workspace index path
    workspace_index_path = project_root / workspace.path / 'PROJECT_INDEX.json'
    
    if not workspace_index_path.exists():
        return True, f"Workspace index missing"
    
    # Check workspace-specific staleness
    needs_features, feature_reason = check_index_features(workspace_index_path)
    if needs_features:
        return True, feature_reason
    
    # Check age-based staleness (per workspace)
    if check_index_staleness(workspace_index_path, threshold_hours=168):  # 1 week
        return True, "Index older than 1 week"
    
    # Check for missing documentation in workspace
    if check_missing_documentation(workspace_index_path, project_root / workspace.path):
        return True, "New documentation files detected"
    
    # Check structural changes in workspace
    if check_structural_changes(workspace_index_path, project_root / workspace.path):
        return True, "Directory structure changed significantly"
    
    # Check hook update ratio
    hook_count, total_count = count_hook_updates(workspace_index_path)
    if total_count > 20 and hook_count / total_count > 0.5:
        return True, f"Many incremental updates ({hook_count}/{total_count})"
    
    return False, None


def check_missing_documentation(index_path: Path, workspace_root: Path) -> bool:
    """Check if important documentation files are missing from index."""
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        doc_map = index.get('documentation_map', {})
        
        # Check for common documentation files
        important_docs = ['README.md', 'ARCHITECTURE.md', 'API.md', 'CONTRIBUTING.md']
        
        for doc in important_docs:
            doc_path = workspace_root / doc
            if doc_path.exists() and doc not in doc_map:
                return True
        
        return False
    except:
        return True


def check_structural_changes(index_path: Path, workspace_root: Path) -> bool:
    """Check if directory structure has significantly changed."""
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Count current directories
        dir_count = 0
        for item in workspace_root.rglob('*'):
            if item.is_dir() and not any(part.startswith('.') for part in item.parts):
                dir_count += 1
        
        # Compare with indexed count
        indexed_dirs = index.get('stats', {}).get('total_directories', 0)
        
        # If directory count changed by more than 20%, reindex
        if indexed_dirs > 0:
            change_ratio = abs(dir_count - indexed_dirs) / indexed_dirs
            return change_ratio > 0.2
        
        return False
    except:
        return False


def count_hook_updates(index_path: Path) -> Tuple[int, int]:
    """Count how many files were updated by hooks vs full index."""
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        hook_count = 0
        total_count = 0
        
        for file_path, info in index.get('files', {}).items():
            total_count += 1
            if info.get('updated_by_hook', False):
                hook_count += 1
        
        return hook_count, total_count
    except:
        return 0, 0


def check_workspace_configuration_changes(project_root: Path) -> Tuple[bool, List[str]]:
    """Check if workspace configuration has changed."""
    if not WORKSPACE_SUPPORT:
        return False, []
    
    changes = []
    
    try:
        workspace_config = get_workspace_config_cached(project_root)
        if not workspace_config:
            return False, []
        
        root_index_path = project_root / 'PROJECT_INDEX.json'
        if not root_index_path.exists():
            return False, []
        
        with open(root_index_path, 'r') as f:
            root_index = json.load(f)
        
        current_workspaces = set(workspace_config['workspaces'].keys())
        
        # Get previously known workspaces from root index
        previous_workspaces = set()
        if 'monorepo' in root_index and 'workspaces' in root_index['monorepo']:
            previous_workspaces = set(root_index['monorepo']['workspaces'].keys())
        
        # Check for added workspaces
        added_workspaces = current_workspaces - previous_workspaces
        if added_workspaces:
            changes.append(f"Added workspaces: {', '.join(added_workspaces)}")
        
        # Check for removed workspaces
        removed_workspaces = previous_workspaces - current_workspaces
        if removed_workspaces:
            changes.append(f"Removed workspaces: {', '.join(removed_workspaces)}")
        
        # Check for configuration file changes
        config_files = [
            'nx.json', 'lerna.json', 'pnpm-workspace.yaml', 
            'package.json', 'rush.json', '.project-index-config.json'
        ]
        
        for config_file in config_files:
            config_path = project_root / config_file
            if config_path.exists():
                # Check if config file is newer than root index
                if config_path.stat().st_mtime > root_index_path.stat().st_mtime:
                    changes.append(f"Configuration file {config_file} was modified")
        
        return len(changes) > 0, changes
        
    except Exception as e:
        print(f"Error checking workspace configuration changes: {e}", file=sys.stderr)
        return False, []


def run_workspace_reindex(workspace_name: str, project_root: Path) -> bool:
    """Run reindex for a specific workspace."""
    if not WORKSPACE_SUPPORT:
        return False
    
    try:
        workspace_config = get_workspace_config_cached(project_root)
        if not workspace_config:
            return False
        
        workspace = workspace_config['workspaces'].get(workspace_name)
        if not workspace:
            return False
        
        # Use the workspace indexer to reindex this workspace
        config_manager = WorkspaceConfigManager(project_root)
        registry = config_manager.load_configuration()
        indexer = WorkspaceIndexer(registry)
        
        workspace_index = indexer.index_workspace(workspace_name)
        
        if workspace_index:
            # Write the index to the workspace directory
            workspace_index_path = project_root / workspace.path / 'PROJECT_INDEX.json'
            workspace_index_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(workspace_index_path, 'w') as f:
                json.dump(workspace_index, f, indent=2)
            
            print(f"Reindexed workspace '{workspace_name}'", file=sys.stderr)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error reindexing workspace '{workspace_name}': {e}", file=sys.stderr)
        return False


def run_reindex(project_root: Path, selective_workspaces: Optional[List[str]] = None) -> bool:
    """Run reindexing with workspace awareness."""
    try:
        workspace_config = get_workspace_config_cached(project_root)
        
        if not workspace_config or not workspace_config['is_monorepo']:
            # Single-repo mode: use the original indexing approach
            return run_single_repo_reindex(project_root)
        
        # Monorepo mode: selective workspace reindexing
        if selective_workspaces:
            success_count = 0
            for workspace_name in selective_workspaces:
                if run_workspace_reindex(workspace_name, project_root):
                    success_count += 1
            
            # Update root index workspace registry
            if success_count > 0:
                update_root_index_after_workspace_reindex(project_root, selective_workspaces)
            
            return success_count > 0
        else:
            # Reindex all workspaces
            all_workspaces = list(workspace_config['workspaces'].keys())
            return run_reindex(project_root, all_workspaces)
        
    except Exception as e:
        print(f"Error running workspace-aware reindex: {e}", file=sys.stderr)
        return False


def run_single_repo_reindex(project_root: Path) -> bool:
    """Run traditional single-repo reindex."""
    try:
        # Try to find project_index.py
        project_index_path = None
        check_dir = project_root
        while check_dir != check_dir.parent:
            potential_path = check_dir / 'project_index.py'
            if potential_path.exists():
                project_index_path = str(potential_path)
                break
            
            # Check in scripts directory
            potential_path = check_dir / 'scripts' / 'project_index.py'
            if potential_path.exists():
                project_index_path = str(potential_path)
                break
            check_dir = check_dir.parent
        
        if project_index_path:
            result = subprocess.run(
                [sys.executable, project_index_path],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        
        # Try the system-installed version
        system_index_path = Path.home() / '.claude-code-project-index' / 'scripts' / 'project_index.py'
        if system_index_path.exists():
            result = subprocess.run(
                [sys.executable, str(system_index_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        
        return False
        
    except Exception as e:
        print(f"Error running single-repo reindex: {e}", file=sys.stderr)
        return False


def update_root_index_after_workspace_reindex(project_root: Path, reindexed_workspaces: List[str]) -> None:
    """Update root index after workspace reindexing."""
    root_index_path = project_root / 'PROJECT_INDEX.json'
    
    if not root_index_path.exists():
        return
    
    try:
        with open(root_index_path, 'r') as f:
            root_index = json.load(f)
        
        workspace_config = get_workspace_config_cached(project_root)
        if not workspace_config:
            return
        
        # Update monorepo section
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
            workspace_index_path = project_root / workspace.path / 'PROJECT_INDEX.json'
            
            root_index['monorepo']['workspaces'][name] = {
                'path': workspace.path,
                'index_path': str(workspace_index_path.relative_to(project_root)),
                'package_manager': workspace.package_manager,
                'last_updated': datetime.now().isoformat() if name in reindexed_workspaces else root_index.get('monorepo', {}).get('workspaces', {}).get(name, {}).get('last_updated'),
                'dependencies': workspace_config['registry'].get_dependencies(name),
                'dependents': workspace_config['registry'].get_dependents(name)
            }
        
        with open(root_index_path, 'w') as f:
            json.dump(root_index, f, indent=2)
        
        print(f"Updated root index after reindexing {len(reindexed_workspaces)} workspaces", file=sys.stderr)
        
    except Exception as e:
        print(f"Error updating root index after workspace reindex: {e}", file=sys.stderr)


def main():
    """Main hook entry point with workspace awareness."""
    # Find project root
    current_dir = Path.cwd()
    project_root = None
    
    # Search up the directory tree
    check_dir = current_dir
    while check_dir != check_dir.parent:
        # Check for PROJECT_INDEX.json
        potential_index = check_dir / 'PROJECT_INDEX.json'
        if potential_index.exists():
            project_root = check_dir
            break
        
        # Check for .git directory
        if (check_dir / '.git').is_dir():
            project_root = check_dir
            break
            
        check_dir = check_dir.parent
    
    if not project_root:
        return
    
    root_index_path = project_root / 'PROJECT_INDEX.json'
    
    try:
        workspace_config = get_workspace_config_cached(project_root)
        
        if not workspace_config or not workspace_config['is_monorepo']:
            # Single-repo mode: use traditional logic
            handle_single_repo_reindex(root_index_path, project_root)
            return
        
        # Monorepo mode: workspace-aware reindexing
        handle_workspace_aware_reindex(project_root, workspace_config)
        
    except Exception as e:
        print(f"Error in main hook: {e}", file=sys.stderr)


def handle_single_repo_reindex(root_index_path: Path, project_root: Path) -> None:
    """Handle single-repo reindexing logic."""
    if not root_index_path.exists():
        return  # No index exists - skip silently
    
    # Check if root index needs refresh
    needs_reindex = False
    reason = ""
    
    # Check for missing features
    missing_features, feature_reason = check_index_features(root_index_path)
    if missing_features:
        needs_reindex = True
        reason = feature_reason
    
    # Check staleness (once a week)
    elif check_index_staleness(root_index_path, threshold_hours=168):
        needs_reindex = True
        reason = "Index is over a week old"
    
    # Check for missing documentation
    elif check_missing_documentation(root_index_path, project_root):
        needs_reindex = True
        reason = "New documentation files detected"
    
    # Check for structural changes
    elif check_structural_changes(root_index_path, project_root):
        needs_reindex = True
        reason = "Directory structure changed significantly"
    
    # Check hook update ratio
    else:
        hook_count, total_count = count_hook_updates(root_index_path)
        if total_count > 20 and hook_count / total_count > 0.5:
            needs_reindex = True
            reason = f"Many incremental updates ({hook_count}/{total_count})"
    
    # Perform reindex if needed
    if needs_reindex:
        if run_single_repo_reindex(project_root):
            print(f"♻️  Reindexed project: {reason}")
            output = {"suppressOutput": False}
            sys.stdout.write(json.dumps(output) + '\n')
        else:
            print(f"Failed to reindex: {reason}", file=sys.stderr)


def handle_workspace_aware_reindex(project_root: Path, workspace_config: Dict) -> None:
    """Handle workspace-aware reindexing logic."""
    # Check for workspace configuration changes first
    config_changed, config_changes = check_workspace_configuration_changes(project_root)
    
    if config_changed:
        print(f"Workspace configuration changes detected: {'; '.join(config_changes)}", file=sys.stderr)
        # Full reindex when workspace configuration changes
        if run_reindex(project_root):
            print("♻️  Full reindex due to workspace configuration changes")
            output = {"suppressOutput": False}
            sys.stdout.write(json.dumps(output) + '\n')
        return
    
    # Check each workspace for staleness
    stale_workspaces = []
    staleness_reasons = {}
    
    for workspace_name in workspace_config['workspaces'].keys():
        is_stale, reason = check_workspace_staleness(workspace_name, project_root)
        if is_stale:
            stale_workspaces.append(workspace_name)
            staleness_reasons[workspace_name] = reason
    
    # Selective reindexing of stale workspaces
    if stale_workspaces:
        print(f"Stale workspaces detected: {', '.join(stale_workspaces)}", file=sys.stderr)
        
        if run_reindex(project_root, stale_workspaces):
            for workspace_name in stale_workspaces:
                reason = staleness_reasons.get(workspace_name, "unknown reason")
                print(f"♻️  Reindexed workspace '{workspace_name}': {reason}")
            
            output = {"suppressOutput": False}
            sys.stdout.write(json.dumps(output) + '\n')
        else:
            print("Failed to reindex stale workspaces", file=sys.stderr)


if __name__ == '__main__':
    main()