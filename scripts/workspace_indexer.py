#!/usr/bin/env python3
"""
Workspace Indexing Engine for Claude Code Project Index
Generates individual workspace indexes with cross-workspace dependency analysis.

Features:
- Individual workspace indexing with existing schema compatibility
- Cross-workspace dependency detection and analysis  
- Workspace context metadata in indexes
- Workspace-specific ignore patterns and configurations
- Import resolution and dependency tracking
"""

import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime

from workspace_config import WorkspaceConfigManager, WorkspaceConfig, WorkspaceRegistry
from index_utils import (
    PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    extract_python_signatures, extract_javascript_signatures, 
    extract_shell_signatures, extract_markdown_structure,
    infer_file_purpose, get_language_name, should_index_file
)

# Import the enhanced cross-workspace analyzer
try:
    from cross_workspace_analyzer import CrossWorkspaceAnalyzer
    ENHANCED_ANALYSIS = True
except ImportError:
    ENHANCED_ANALYSIS = False


class CrossWorkspaceDependencyAnalyzer:
    """
    Enhanced wrapper for cross-workspace dependency analysis.
    Uses the comprehensive CrossWorkspaceAnalyzer when available, falls back to basic analysis.
    """
    
    def __init__(self, registry: WorkspaceRegistry):
        self.registry = registry
        self.enhanced_analyzer = None
        self.workspace_packages = self._load_workspace_packages()
        
        # Initialize enhanced analyzer if available
        if ENHANCED_ANALYSIS:
            try:
                self.enhanced_analyzer = CrossWorkspaceAnalyzer(registry)
            except Exception as e:
                print(f"Warning: Enhanced analysis failed to initialize: {e}")
    
    def _load_workspace_packages(self) -> Dict[str, Dict]:
        """Load package.json from each workspace to understand package names."""
        packages = {}
        
        for workspace in self.registry.get_all_workspaces():
            package_json = workspace.full_path / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, 'r') as f:
                        package_data = json.load(f)
                    packages[workspace.name] = {
                        "name": package_data.get("name", workspace.name),
                        "workspace": workspace.name,
                        "path": workspace.path
                    }
                except (json.JSONDecodeError, IOError):
                    pass
        
        return packages
    
    def get_workspace_dependencies(self, workspace_name: str) -> Dict[str, List[str]]:
        """Get comprehensive dependency information for a workspace."""
        if self.enhanced_analyzer:
            # Use enhanced analysis
            try:
                full_analysis = self.enhanced_analyzer.analyze_all_workspaces()
                workspace_deps = full_analysis['dependency_graph'].get(workspace_name, {})
                
                return {
                    "imports_from": workspace_deps.get("imports_from", []),
                    "imported_by": workspace_deps.get("imported_by", []),
                    "shared_types": workspace_deps.get("shared_types", []),
                    "analysis_quality": "enhanced"
                }
            except Exception as e:
                print(f"Warning: Enhanced analysis failed for {workspace_name}: {e}")
        
        # Fallback to basic analysis
        workspace = self.registry.get_workspace(workspace_name)
        if not workspace:
            return {"imports_from": [], "imported_by": [], "shared_types": [], "analysis_quality": "basic"}
        
        basic_deps = []
        for file_path in workspace.full_path.rglob('*'):
            if file_path.is_file():
                file_deps = self.analyze_file_imports(file_path, workspace)
                basic_deps.extend(file_deps)
        
        return {
            "imports_from": list(set(basic_deps)),
            "imported_by": [],  # Basic analysis doesn't track reverse dependencies
            "shared_types": [],
            "analysis_quality": "basic"
        }
    
    def analyze_file_imports(self, file_path: Path, workspace: WorkspaceConfig) -> List[str]:
        """Analyze imports in a file to find cross-workspace dependencies."""
        if not file_path.exists() or not file_path.is_file():
            return []
        
        cross_workspace_deps = []
        file_ext = file_path.suffix.lower()
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return []
        
        if file_ext in ['.py']:
            cross_workspace_deps.extend(self._analyze_python_imports(content, workspace))
        elif file_ext in ['.js', '.ts', '.jsx', '.tsx']:
            cross_workspace_deps.extend(self._analyze_javascript_imports(content, workspace))
        elif file_ext == '.json' and file_path.name == 'package.json':
            cross_workspace_deps.extend(self._analyze_package_json_deps(content, workspace))
        
        return cross_workspace_deps
    
    def _analyze_python_imports(self, content: str, workspace: WorkspaceConfig) -> List[str]:
        """Analyze Python imports for cross-workspace dependencies."""
        deps = []
        
        # Pattern for import statements
        import_patterns = [
            r'from\s+([^\s]+)\s+import',
            r'import\s+([^\s,]+)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Check if this import might be from another workspace
                dep_workspace = self._resolve_python_import_to_workspace(match, workspace)
                if dep_workspace and dep_workspace != workspace.name:
                    deps.append(dep_workspace)
        
        return list(set(deps))
    
    def _analyze_javascript_imports(self, content: str, workspace: WorkspaceConfig) -> List[str]:
        """Analyze JavaScript/TypeScript imports for cross-workspace dependencies."""
        deps = []
        
        # Pattern for import statements
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Check if this is a workspace-relative import
                dep_workspace = self._resolve_javascript_import_to_workspace(match, workspace)
                if dep_workspace and dep_workspace != workspace.name:
                    deps.append(dep_workspace)
        
        return list(set(deps))
    
    def _analyze_package_json_deps(self, content: str, workspace: WorkspaceConfig) -> List[str]:
        """Analyze package.json dependencies for cross-workspace dependencies."""
        deps = []
        
        try:
            package_data = json.loads(content)
        except json.JSONDecodeError:
            return []
        
        # Check all dependency types
        dep_types = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']
        
        for dep_type in dep_types:
            if dep_type in package_data:
                for package_name in package_data[dep_type]:
                    # Check if this package belongs to another workspace
                    for ws_name, pkg_info in self.workspace_packages.items():
                        if pkg_info["name"] == package_name and ws_name != workspace.name:
                            deps.append(ws_name)
        
        return list(set(deps))
    
    def _resolve_python_import_to_workspace(self, import_path: str, current_workspace: WorkspaceConfig) -> Optional[str]:
        """Resolve a Python import to a workspace name."""
        # Check if import starts with a workspace name
        for workspace in self.registry.get_all_workspaces():
            if workspace.name != current_workspace.name:
                if import_path.startswith(workspace.name):
                    return workspace.name
        
        return None
    
    def _resolve_javascript_import_to_workspace(self, import_path: str, current_workspace: WorkspaceConfig) -> Optional[str]:
        """Resolve a JavaScript/TypeScript import to a workspace name."""
        # Relative imports starting with ../ might point to other workspaces
        if import_path.startswith('../'):
            # Try to resolve the path
            try:
                resolved_path = (current_workspace.full_path / import_path).resolve()
                return self.registry.get_workspace_by_path(resolved_path)
            except:
                pass
        
        # Check if import is a workspace package name
        for ws_name, pkg_info in self.workspace_packages.items():
            if import_path == pkg_info["name"] and ws_name != current_workspace.name:
                return ws_name
        
        return None


class WorkspaceIndexer:
    """Indexes individual workspaces with cross-workspace awareness."""
    
    def __init__(self, registry: WorkspaceRegistry):
        self.registry = registry
        self.root_path = registry.root_path
        self.dependency_analyzer = CrossWorkspaceDependencyAnalyzer(registry)
    
    def index_workspace(self, workspace_name: str) -> Optional[Dict]:
        """
        Index a specific workspace.
        
        Args:
            workspace_name: Name of the workspace to index
            
        Returns:
            Dictionary containing the workspace index
        """
        workspace = self.registry.get_workspace(workspace_name)
        if not workspace:
            return None
        
        if not workspace.full_path.exists():
            return None
        
        # Build the index structure (compatible with existing schema)
        index = {
            "indexed_at": datetime.now().isoformat(),
            "root": workspace.path,
            "workspace": {
                "name": workspace.name,
                "parent_root": str(self.root_path),
                "package_manager": workspace.package_manager,
                "dependencies": [],
                "dependents": []
            },
            "project_structure": {
                "type": "tree",
                "root": workspace.path,
                "tree": []
            },
            "documentation_map": {},
            "directory_purposes": {},
            "stats": {
                "total_files": 0,
                "total_directories": 0,
                "fully_parsed": {},
                "listed_only": {},
                "markdown_files": 0
            },
            "files": {},
            "dependency_graph": {}
        }
        
        # Collect files and analyze structure
        all_files = []
        all_dirs = set()
        cross_workspace_deps = set()
        
        ignore_patterns = workspace.get_ignore_patterns()
        
        try:
            for file_path in workspace.full_path.rglob('*'):
                if file_path.is_file():
                    # Check if file should be indexed
                    if should_index_file(file_path, self.root_path):
                        # Check workspace-specific ignore patterns
                        relative_path = file_path.relative_to(workspace.full_path)
                        if not self._matches_ignore_patterns(str(relative_path), ignore_patterns):
                            all_files.append(file_path)
                            
                            # Analyze for cross-workspace dependencies
                            file_deps = self.dependency_analyzer.analyze_file_imports(file_path, workspace)
                            cross_workspace_deps.update(file_deps)
                elif file_path.is_dir():
                    all_dirs.add(file_path)
        except PermissionError:
            pass
        
        # Update workspace dependencies using enhanced analysis
        enhanced_deps = self.dependency_analyzer.get_workspace_dependencies(workspace_name)
        
        # Set dependencies in registry for backward compatibility
        self.registry.set_dependencies(workspace_name, enhanced_deps["imports_from"])
        
        # Add comprehensive dependency information to workspace index
        index["workspace"]["dependencies"] = enhanced_deps["imports_from"]
        index["workspace"]["dependents"] = enhanced_deps["imported_by"]
        index["workspace"]["shared_types"] = enhanced_deps["shared_types"]
        index["workspace"]["analysis_quality"] = enhanced_deps["analysis_quality"]
        
        # Generate tree structure
        index["project_structure"]["tree"] = self._generate_workspace_tree(workspace.full_path, workspace.path)
        
        # Process files
        for file_path in all_files:
            relative_path = file_path.relative_to(self.root_path)
            file_key = str(relative_path)
            
            file_info = {
                "language": get_language_name(file_path.suffix),
                "parsed": False
            }
            
            # Add file purpose if detectable
            purpose = infer_file_purpose(file_path)
            if purpose:
                file_info["purpose"] = purpose
            
            # Parse file if it's in a parseable language
            if file_path.suffix in PARSEABLE_LANGUAGES:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    parsed_data = self._parse_file_content(content, file_path.suffix)
                    if parsed_data:
                        file_info.update(parsed_data)
                        file_info["parsed"] = True
                        
                        # Update stats
                        lang = PARSEABLE_LANGUAGES[file_path.suffix]
                        if lang not in index["stats"]["fully_parsed"]:
                            index["stats"]["fully_parsed"][lang] = 0
                        index["stats"]["fully_parsed"][lang] += 1
                    else:
                        lang = PARSEABLE_LANGUAGES[file_path.suffix]
                        if lang not in index["stats"]["listed_only"]:
                            index["stats"]["listed_only"][lang] = 0
                        index["stats"]["listed_only"][lang] += 1
                except:
                    # Failed to parse, just list it
                    lang = get_language_name(file_path.suffix)
                    if lang not in index["stats"]["listed_only"]:
                        index["stats"]["listed_only"][lang] = 0
                    index["stats"]["listed_only"][lang] += 1
            elif file_path.suffix in MARKDOWN_EXTENSIONS:
                # Process markdown files
                md_structure = extract_markdown_structure(file_path)
                if md_structure["sections"]:
                    index["documentation_map"][file_key] = md_structure
                    index["stats"]["markdown_files"] += 1
            else:
                # Just list the file
                lang = get_language_name(file_path.suffix)
                if lang not in index["stats"]["listed_only"]:
                    index["stats"]["listed_only"][lang] = 0
                index["stats"]["listed_only"][lang] += 1
            
            index["files"][file_key] = file_info
        
        # Update final stats
        index["stats"]["total_files"] = len(all_files)
        index["stats"]["total_directories"] = len(all_dirs)
        
        # Generate dependency graph for workspace
        index["dependency_graph"] = self._build_workspace_dependency_graph(index["files"])
        
        return index
    
    def _matches_ignore_patterns(self, file_path: str, patterns: Set[str]) -> bool:
        """Check if a file path matches any ignore pattern."""
        for pattern in patterns:
            if re.match(pattern.replace('*', '.*'), file_path):
                return True
        return False
    
    def _generate_workspace_tree(self, workspace_path: Path, workspace_root: str) -> List[str]:
        """Generate ASCII tree structure for workspace."""
        tree_lines = [workspace_root]
        
        def add_tree_level(path: Path, prefix: str = "", depth: int = 0, max_depth: int = 3):
            if depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except PermissionError:
                return
            
            # Filter to important items
            dirs = [item for item in items if item.is_dir() and not item.name.startswith('.')]
            important_files = [
                item for item in items 
                if item.is_file() and (
                    item.name in ['README.md', 'package.json', 'requirements.txt', 
                                 'Cargo.toml', 'go.mod', 'setup.py', 'pyproject.toml']
                )
            ]
            
            all_items = dirs + important_files
            
            for i, item in enumerate(all_items):
                is_last = i == len(all_items) - 1
                current_prefix = "└── " if is_last else "├── "
                
                name = item.name
                if item.is_dir():
                    name += "/"
                
                tree_lines.append(prefix + current_prefix + name)
                
                if item.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    add_tree_level(item, next_prefix, depth + 1)
        
        add_tree_level(workspace_path, "├── ")
        return tree_lines
    
    def _parse_file_content(self, content: str, file_extension: str) -> Optional[Dict]:
        """Parse file content based on its extension."""
        try:
            if file_extension == '.py':
                return extract_python_signatures(content)
            elif file_extension in ['.js', '.ts', '.jsx', '.tsx']:
                return extract_javascript_signatures(content)
            elif file_extension in ['.sh', '.bash']:
                return extract_shell_signatures(content)
        except Exception:
            pass
        
        return None
    
    def _build_workspace_dependency_graph(self, files: Dict) -> Dict:
        """Build dependency graph for the workspace."""
        dependency_graph = {}
        
        # Extract dependencies from parsed files
        for file_path, file_info in files.items():
            if file_info.get("parsed") and isinstance(file_info, dict):
                # Handle different file types
                if "functions" in file_info:
                    for func_name, func_info in file_info["functions"].items():
                        if isinstance(func_info, dict) and "calls" in func_info:
                            dependency_graph[f"{file_path}:{func_name}"] = func_info["calls"]
                
                if "classes" in file_info:
                    for class_name, class_info in file_info["classes"].items():
                        if isinstance(class_info, dict) and "methods" in class_info:
                            for method_name, method_info in class_info["methods"].items():
                                if isinstance(method_info, dict) and "calls" in method_info:
                                    dependency_graph[f"{file_path}:{class_name}.{method_name}"] = method_info["calls"]
        
        return dependency_graph
    
    def index_all_workspaces(self) -> Dict[str, Dict]:
        """Index all workspaces in the registry."""
        results = {}
        
        for workspace_name in self.registry.get_workspace_names():
            index = self.index_workspace(workspace_name)
            if index:
                results[workspace_name] = index
        
        return results


def index_workspace(root_path: Union[str, Path], workspace_name: str) -> Optional[Dict]:
    """
    Convenience function to index a specific workspace.
    
    Args:
        root_path: Path to the monorepo root
        workspace_name: Name of the workspace to index
        
    Returns:
        Workspace index dictionary or None if not found
    """
    config_manager = WorkspaceConfigManager(root_path)
    registry = config_manager.load_configuration()
    
    indexer = WorkspaceIndexer(registry)
    return indexer.index_workspace(workspace_name)


def index_all_workspaces(root_path: Union[str, Path]) -> Dict[str, Dict]:
    """
    Convenience function to index all workspaces.
    
    Args:
        root_path: Path to the monorepo root
        
    Returns:
        Dictionary mapping workspace names to their indexes
    """
    config_manager = WorkspaceConfigManager(root_path)
    registry = config_manager.load_configuration()
    
    indexer = WorkspaceIndexer(registry)
    return indexer.index_all_workspaces()


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    workspace_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if workspace_name:
        # Index specific workspace
        result = index_workspace(root_dir, workspace_name)
        if result:
            print(f"Index for workspace '{workspace_name}':")
            print(json.dumps(result, indent=2))
        else:
            print(f"Workspace '{workspace_name}' not found or failed to index.")
    else:
        # Index all workspaces
        results = index_all_workspaces(root_dir)
        if results:
            print("All workspace indexes:")
            for ws_name, ws_index in results.items():
                print(f"\n=== {ws_name} ===")
                print(f"Files: {ws_index['stats']['total_files']}")
                print(f"Dependencies: {ws_index['workspace']['dependencies']}")
                print(f"Dependents: {ws_index['workspace']['dependents']}")
        else:
            print("No workspaces found or failed to index.")