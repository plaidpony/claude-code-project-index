"""
Hierarchical Index Manager for Claude Code Project Index

This module implements the hierarchical indexing architecture to solve infinite loop 
compression issues in large monorepos. It generates a lightweight root index that 
contains only workspace registry and cross-workspace dependencies, staying under 200KB 
and generating in under 30 seconds regardless of monorepo size.

Key Features:
- Lightweight root index generation (<200KB, <30s)
- Automatic monorepo vs single-repo detection
- Backward compatibility with single-repo projects
- Infinite loop prevention through architectural separation
- Cross-workspace dependency tracking without recursion
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple

import sys
from pathlib import Path

# Add scripts directory to path if needed
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from workspace_config import WorkspaceConfigManager, WorkspaceRegistry
    from monorepo_detector import detect_monorepo
    from smart_compressor import SmartCompressor
    from cross_workspace_analyzer import CrossWorkspaceAnalyzer, build_cross_workspace_dependencies
    from lazy_index_loader import LazyIndexLoader, get_global_loader
except ImportError as e:
    print(f"⚠️  Import error in hierarchical_indexer: {e}")
    print("   Some features may not be available")
    WorkspaceConfigManager = None
    WorkspaceRegistry = None
    detect_monorepo = None
    SmartCompressor = None
    CrossWorkspaceAnalyzer = None
    build_cross_workspace_dependencies = None
    LazyIndexLoader = None
    get_global_loader = None


class HierarchicalIndexManager:
    """
    Main indexer for the hierarchical architecture.
    
    Generates lightweight root indexes and coordinates workspace indexing
    to prevent infinite loops and enable scalable monorepo support.
    """
    
    def __init__(self, root_path: Union[str, Path]):
        self.root_path = Path(root_path).resolve()
        self.workspace_manager = WorkspaceConfigManager(self.root_path) if WorkspaceConfigManager else None
        self.compressor = SmartCompressor() if SmartCompressor else None
        self.lazy_loader = get_global_loader(self.root_path) if get_global_loader else None
        self.generation_start_time = None
        
    def detect_project_type(self) -> Tuple[bool, str]:
        """
        Detect if this is a monorepo or single-repo project.
        
        Returns:
            Tuple of (is_monorepo, detection_method)
        """
        if not detect_monorepo:
            return False, "single_repo"
            
        detection_result = detect_monorepo(self.root_path)
        
        if detection_result.get('monorepo', False):
            tool = detection_result.get('tool', 'unknown')
            return True, f"monorepo_{tool}"
        
        # Check for manual monorepo configuration
        manual_config = self.root_path / ".project-index-config.json"
        if manual_config.exists():
            try:
                with open(manual_config) as f:
                    config = json.load(f)
                    if config.get('monorepo', {}).get('enabled', False):
                        return True, "manual_config"
            except (json.JSONDecodeError, KeyError):
                pass
        
        return False, "single_repo"
    
    def generate_root_index(self, force_monorepo: bool = False) -> Dict:
        """
        Generate the lightweight root index.
        
        Args:
            force_monorepo: Force monorepo indexing even if not detected
            
        Returns:
            Root index dictionary
            
        Raises:
            Exception: If generation fails or exceeds time/size limits
        """
        self.generation_start_time = time.time()
        
        # Detect project type
        is_monorepo, detection_method = self.detect_project_type()
        if force_monorepo:
            is_monorepo = True
            detection_method = "forced"
        
        # Generate appropriate index
        if is_monorepo:
            return self._generate_monorepo_root_index(detection_method)
        else:
            return self._generate_single_repo_index()
    
    def _generate_monorepo_root_index(self, detection_method: str) -> Dict:
        """Generate lightweight root index for monorepo."""
        try:
            if not self.workspace_manager:
                raise Exception("Workspace manager not available")
                
            # Load workspace configuration
            registry = self.workspace_manager.load_configuration()
            
            if not registry:
                raise Exception("Failed to load workspace configuration")
            
            # Build workspace registry for root index
            workspace_registry = {}
            total_files = 0
            indexed_workspaces = 0
            failed_workspaces = 0
            
            for workspace in registry.get_all_workspaces():
                # Handle both absolute and relative paths
                if isinstance(workspace.path, str):
                    workspace_path = Path(workspace.path)
                else:
                    workspace_path = workspace.path
                
                # Make absolute path if it's relative
                if not workspace_path.is_absolute():
                    workspace_path = self.root_path / workspace_path
                
                workspace_index_path = workspace_path / "PROJECT_INDEX.json"
                workspace_status = "indexed" if workspace_index_path.exists() else "pending"
                
                if workspace_status == "indexed":
                    indexed_workspaces += 1
                    # Get file count from workspace index if available
                    try:
                        with open(workspace_index_path) as f:
                            ws_index = json.load(f)
                            total_files += ws_index.get('stats', {}).get('total_files', 0)
                    except (json.JSONDecodeError, FileNotFoundError):
                        workspace_status = "failed"
                        failed_workspaces += 1
                        indexed_workspaces -= 1
                
                workspace_registry[workspace.name] = {
                    "path": str(workspace_path.relative_to(self.root_path)),
                    "index_path": str(workspace_index_path.relative_to(self.root_path)),
                    "package_manager": getattr(workspace, 'package_manager', 'unknown'),
                    "last_updated": datetime.now().isoformat(),
                    "status": workspace_status
                }
            
            # Build cross-workspace dependencies using enhanced analyzer for root index
            if build_cross_workspace_dependencies:
                cross_workspace_deps = build_cross_workspace_dependencies(
                    registry, 
                    hierarchical_manager=self, 
                    for_root_index=True, 
                    lazy_loader=self.lazy_loader,
                    compressor=self.compressor
                )
            else:
                # Fallback to basic implementation if analyzer unavailable
                cross_workspace_deps = self._build_cross_workspace_dependencies_fallback(registry)
            
            # Create root index structure
            root_index = {
                "indexed_at": datetime.now().isoformat(),
                "root": ".",
                "index_type": "hierarchical_root",
                "monorepo": {
                    "enabled": True,
                    "tool": detection_method,
                    "last_updated": datetime.now().isoformat(),
                    "total_workspaces": len(workspace_registry),
                    "workspace_registry": workspace_registry
                },
                "cross_workspace_dependencies": cross_workspace_deps.get("cross_workspace_dependencies", {}),
                "circular_dependencies": cross_workspace_deps.get("circular_dependencies", []),
                "dependency_summary": cross_workspace_deps.get("dependency_summary", {}),
                "global_stats": {
                    "total_workspaces": len(workspace_registry),
                    "total_files": total_files,
                    "indexed_workspaces": indexed_workspaces,
                    "failed_workspaces": failed_workspaces
                },
                "project_structure": self._generate_workspace_overview_tree(registry)
            }
            
            # Compress to ensure size limits
            if self.compressor:
                compressed_index = self.compressor.compress_root_index(root_index)
            else:
                # Fallback: basic compression by removing optional fields
                compressed_index = root_index.copy()
                compressed_index.pop('project_structure', None)
            
            # Validate constraints
            self._validate_generation_constraints(compressed_index)
            
            return compressed_index
            
        except Exception as e:
            raise Exception(f"Failed to generate monorepo root index: {str(e)}")
    
    def _generate_single_repo_index(self) -> Dict:
        """Generate basic single-repo index structure."""
        # Create a simple single-repo index structure
        # This avoids circular import issues with project_index
        index = {
            "indexed_at": datetime.now().isoformat(),
            "root": str(self.root_path),
            "index_type": "single_repo",
            "monorepo": {"enabled": False},
            "project_structure": {"type": "single_repo", "tree": []},
            "stats": {
                "total_files": 0,
                "total_directories": 0,
                "markdown_files": 0
            },
            "files": {},
            "directory_purposes": {},
            "documentation_map": {}
        }
        
        # Basic file collection for single repo (simplified)
        files_found = 0
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file() and files_found < 1000:  # Limit for basic indexing
                relative_path = str(file_path.relative_to(self.root_path))
                index["files"][relative_path] = {
                    "language": file_path.suffix.lower(),
                    "parsed": False
                }
                files_found += 1
        
        index["stats"]["total_files"] = files_found
        return index
    
    def _build_cross_workspace_dependencies_fallback(self, registry: WorkspaceRegistry) -> Dict[str, Dict]:
        """
        Build simplified cross-workspace dependency mapping.
        
        This extracts only the high-level workspace-to-workspace dependencies
        without file-level details to prevent infinite loops.
        """
        dependencies = {}
        
        for workspace in registry.get_all_workspaces():
            workspace_deps = []
            
            # Check package.json for workspace dependencies
            if isinstance(workspace.path, str):
                workspace_path = Path(workspace.path)
            else:
                workspace_path = workspace.path
                
            # Make absolute path if it's relative
            if not workspace_path.is_absolute():
                workspace_path = self.root_path / workspace_path
                
            package_json = workspace_path / "package.json"
            if package_json.exists():
                try:
                    with open(package_json) as f:
                        package_data = json.load(f)
                    
                    # Look for workspace protocol dependencies
                    all_deps = {}
                    all_deps.update(package_data.get('dependencies', {}))
                    all_deps.update(package_data.get('devDependencies', {}))
                    
                    for dep_name, version in all_deps.items():
                        if version.startswith('workspace:') or version.startswith('file:'):
                            # Find workspace by package name
                            for other_workspace in registry.get_all_workspaces():
                                if other_workspace.name != workspace.name:
                                    if isinstance(other_workspace.path, str):
                                        other_workspace_path = Path(other_workspace.path)
                                    else:
                                        other_workspace_path = other_workspace.path
                                        
                                    # Make absolute path if it's relative
                                    if not other_workspace_path.is_absolute():
                                        other_workspace_path = self.root_path / other_workspace_path
                                        
                                    other_package_json = other_workspace_path / "package.json"
                                    if other_package_json.exists():
                                        try:
                                            with open(other_package_json) as f:
                                                other_package = json.load(f)
                                            if other_package.get('name') == dep_name:
                                                workspace_deps.append(other_workspace.name)
                                        except (json.JSONDecodeError, KeyError):
                                            continue
                                    
                except (json.JSONDecodeError, KeyError):
                    continue
            
            if workspace_deps:
                dependencies[workspace.name] = {"depends_on": list(set(workspace_deps)), "dependents": [], "import_count": 0}
        
        return {"cross_workspace_dependencies": dependencies, "dependency_summary": {"analysis_time_seconds": 0}}
    
    def _generate_workspace_overview_tree(self, registry: WorkspaceRegistry) -> Dict:
        """Generate high-level workspace tree for overview."""
        tree_lines = []
        workspace_names = sorted([ws.name for ws in registry.get_all_workspaces()])
        
        for i, workspace_name in enumerate(workspace_names):
            is_last = i == len(workspace_names) - 1
            prefix = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{workspace_name}/")
        
        return {
            "type": "workspace_overview",
            "tree": tree_lines
        }
    
    def _validate_generation_constraints(self, index: Dict):
        """Validate that the generated index meets performance constraints."""
        # Check generation time
        if self.generation_start_time:
            generation_time = time.time() - self.generation_start_time
            if generation_time > 30:
                raise Exception(f"Root index generation took {generation_time:.1f}s, exceeds 30s limit")
        
        # Check index size
        index_json = json.dumps(index, separators=(',', ':'))
        index_size_kb = len(index_json.encode('utf-8')) / 1024
        
        if index_size_kb > 200:
            raise Exception(f"Root index size is {index_size_kb:.1f}KB, exceeds 200KB limit")
    
    def save_root_index(self, index: Dict, output_path: Optional[Path] = None) -> Path:
        """Save the root index to disk."""
        if output_path is None:
            output_path = self.root_path / "PROJECT_INDEX.json"
        
        with open(output_path, 'w') as f:
            json.dump(index, f, indent=2, separators=(',', ': '))
        
        return output_path
    
    def get_workspace_registry(self) -> WorkspaceRegistry:
        """Get the workspace registry for this project."""
        return self.workspace_manager.load_configuration()


def generate_hierarchical_index(root_path: Union[str, Path], 
                               force_monorepo: bool = False) -> Dict:
    """
    Main entry point for hierarchical index generation.
    
    Args:
        root_path: Path to project root
        force_monorepo: Force monorepo mode even if not detected
        
    Returns:
        Generated index dictionary
    """
    manager = HierarchicalIndexManager(root_path)
    return manager.generate_root_index(force_monorepo=force_monorepo)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate hierarchical project index")
    parser.add_argument("root_path", default=".", nargs="?", 
                       help="Path to project root (default: current directory)")
    parser.add_argument("--force-monorepo", action="store_true",
                       help="Force monorepo indexing even if not detected")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    try:
        manager = HierarchicalIndexManager(args.root_path)
        index = manager.generate_root_index(force_monorepo=args.force_monorepo)
        
        output_path = Path(args.output) if args.output else None
        saved_path = manager.save_root_index(index, output_path)
        
        print(f"✅ Generated hierarchical index: {saved_path}")
        print(f"📊 Index type: {index.get('index_type', 'unknown')}")
        
        if index.get('monorepo', {}).get('enabled'):
            stats = index.get('global_stats', {})
            print(f"📦 Workspaces: {stats.get('total_workspaces', 0)}")
            print(f"📄 Total files: {stats.get('total_files', 0)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)