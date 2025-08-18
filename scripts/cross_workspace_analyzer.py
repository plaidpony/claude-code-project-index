#!/usr/bin/env python3
"""
Cross-Workspace Dependency Analysis Engine for Claude Code Project Index
Phase 3: Comprehensive dependency analysis with circular dependency detection.

Features:
- Static analysis of TypeScript, JavaScript, and Python imports
- Package.json and tsconfig.json project reference parsing
- Symlink resolution for workspace tools
- Circular dependency detection using DFS algorithm
- Shared types and interfaces tracking
- Performance optimization for large monorepos (50+ workspaces)
- Bidirectional relationship tracking for refactoring impact analysis
"""

import json
import re
import ast
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, deque
from dataclasses import dataclass

from workspace_config import WorkspaceRegistry, WorkspaceConfig


@dataclass
class ImportInfo:
    """Information about a cross-workspace import."""
    source_workspace: str
    target_workspace: str
    source_file: str
    import_statement: str
    import_type: str  # 'direct', 'relative', 'package', 'project_reference'
    shared_types: List[str] = None
    
    def __post_init__(self):
        if self.shared_types is None:
            self.shared_types = []


@dataclass
class CircularDependency:
    """Information about a circular dependency."""
    cycle: List[str]  # List of workspace names in the cycle
    imports: List[ImportInfo]  # Import statements that create the cycle
    severity: str = "high"  # high, medium, low


class CrossWorkspaceAnalyzer:
    """
    Advanced cross-workspace dependency analyzer.
    Implements comprehensive static analysis and circular dependency detection.
    """
    
    def __init__(self, registry: WorkspaceRegistry):
        self.registry = registry
        self.workspace_packages = self._load_workspace_packages()
        self.typescript_references = self._load_typescript_references()
        self.import_cache = {}  # Cache for resolved imports
        self.symlink_cache = {}  # Cache for resolved symlinks
    
    def _load_workspace_packages(self) -> Dict[str, Dict]:
        """Load package.json from each workspace to understand package names and dependencies."""
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
                        "path": workspace.path,
                        "dependencies": package_data.get("dependencies", {}),
                        "devDependencies": package_data.get("devDependencies", {}),
                        "peerDependencies": package_data.get("peerDependencies", {}),
                        "workspaces": package_data.get("workspaces", [])
                    }
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to parse {package_json}: {e}")
        
        return packages
    
    def _load_typescript_references(self) -> Dict[str, List[str]]:
        """Load TypeScript project references from tsconfig.json files."""
        references = {}
        
        for workspace in self.registry.get_all_workspaces():
            tsconfig_path = workspace.full_path / "tsconfig.json"
            if tsconfig_path.exists():
                try:
                    with open(tsconfig_path, 'r') as f:
                        # Handle JSON with comments (TypeScript allows this)
                        content = f.read()
                        # Simple comment removal (not perfect but works for most cases)
                        content = re.sub(r'//.*', '', content)
                        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                        
                        tsconfig_data = json.loads(content)
                    
                    project_refs = tsconfig_data.get("references", [])
                    ref_paths = []
                    for ref in project_refs:
                        if isinstance(ref, dict) and "path" in ref:
                            ref_path = ref["path"]
                            # Resolve relative path
                            resolved_path = (workspace.full_path / ref_path).resolve()
                            target_workspace = self.registry.get_workspace_by_path(resolved_path)
                            if target_workspace:
                                ref_paths.append(target_workspace)
                    
                    if ref_paths:
                        references[workspace.name] = ref_paths
                        
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to parse {tsconfig_path}: {e}")
        
        return references
    
    def analyze_all_workspaces(self) -> Dict[str, Dict]:
        """
        Analyze all workspaces for cross-workspace dependencies.
        Returns the complete dependency graph with circular dependency detection.
        """
        # Step 1: Analyze individual workspace imports
        all_imports = []
        workspace_imports = {}
        
        for workspace in self.registry.get_all_workspaces():
            imports = self._analyze_workspace_imports(workspace)
            all_imports.extend(imports)
            workspace_imports[workspace.name] = imports
        
        # Step 2: Build dependency graph
        dependency_graph = self._build_dependency_graph(all_imports)
        
        # Step 3: Detect circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_graph)
        
        # Step 4: Extract shared types and interfaces
        shared_types = self._extract_shared_types(all_imports)
        
        # Step 5: Build bidirectional relationships
        bidirectional_deps = self._build_bidirectional_relationships(dependency_graph)
        
        return {
            "dependency_graph": dependency_graph,
            "circular_dependencies": [self._circular_dep_to_dict(cd) for cd in circular_deps],
            "shared_types": shared_types,
            "bidirectional_dependencies": bidirectional_deps,
            "workspace_imports": workspace_imports,
            "analysis_metadata": {
                "total_workspaces": len(self.registry.get_all_workspaces()),
                "total_imports": len(all_imports),
                "circular_count": len(circular_deps),
                "analyzed_at": str(Path.cwd())
            }
        }
    
    def _analyze_workspace_imports(self, workspace: WorkspaceConfig) -> List[ImportInfo]:
        """Analyze all imports in a workspace for cross-workspace dependencies."""
        imports = []
        
        # Analyze source files
        for file_path in workspace.full_path.rglob('*'):
            if not file_path.is_file():
                continue
                
            file_imports = self._analyze_file_imports(file_path, workspace)
            imports.extend(file_imports)
        
        # Analyze package.json dependencies
        package_imports = self._analyze_package_dependencies(workspace)
        imports.extend(package_imports)
        
        # Analyze TypeScript project references
        if workspace.name in self.typescript_references:
            for target_workspace in self.typescript_references[workspace.name]:
                imports.append(ImportInfo(
                    source_workspace=workspace.name,
                    target_workspace=target_workspace,
                    source_file="tsconfig.json",
                    import_statement=f"references: {target_workspace}",
                    import_type="project_reference"
                ))
        
        return imports
    
    def _analyze_file_imports(self, file_path: Path, workspace: WorkspaceConfig) -> List[ImportInfo]:
        """Analyze imports in a single file."""
        if not file_path.suffix in ['.py', '.js', '.ts', '.jsx', '.tsx']:
            return []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return []
        
        imports = []
        relative_file_path = str(file_path.relative_to(workspace.full_path))
        
        if file_path.suffix == '.py':
            imports.extend(self._analyze_python_imports(content, workspace, relative_file_path))
        elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            imports.extend(self._analyze_javascript_imports(content, workspace, relative_file_path))
        
        return imports
    
    def _analyze_python_imports(self, content: str, workspace: WorkspaceConfig, file_path: str) -> List[ImportInfo]:
        """Analyze Python imports for cross-workspace dependencies with AST parsing."""
        imports = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fallback to regex parsing for invalid syntax
            return self._analyze_python_imports_regex(content, workspace, file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target_workspace = self._resolve_python_import(alias.name, workspace)
                    if target_workspace and target_workspace != workspace.name:
                        imports.append(ImportInfo(
                            source_workspace=workspace.name,
                            target_workspace=target_workspace,
                            source_file=file_path,
                            import_statement=f"import {alias.name}",
                            import_type="direct",
                            shared_types=self._extract_python_types_from_import(alias.name, content)
                        ))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    target_workspace = self._resolve_python_import(node.module, workspace)
                    if target_workspace and target_workspace != workspace.name:
                        # Extract imported names for shared types tracking
                        imported_names = [alias.name for alias in node.names]
                        imports.append(ImportInfo(
                            source_workspace=workspace.name,
                            target_workspace=target_workspace,
                            source_file=file_path,
                            import_statement=f"from {node.module} import {', '.join(imported_names)}",
                            import_type="direct",
                            shared_types=self._filter_type_names(imported_names)
                        ))
        
        return imports
    
    def _analyze_python_imports_regex(self, content: str, workspace: WorkspaceConfig, file_path: str) -> List[ImportInfo]:
        """Fallback regex-based Python import analysis."""
        imports = []
        
        # Pattern for import statements
        import_patterns = [
            r'from\s+([^\s]+)\s+import\s+([^#\n]+)',
            r'import\s+([^\s,#\n]+)'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if 'from' in pattern:
                    module, imported_items = match.groups()
                    target_workspace = self._resolve_python_import(module, workspace)
                    if target_workspace and target_workspace != workspace.name:
                        imported_names = [name.strip() for name in imported_items.split(',')]
                        imports.append(ImportInfo(
                            source_workspace=workspace.name,
                            target_workspace=target_workspace,
                            source_file=file_path,
                            import_statement=match.group(0),
                            import_type="direct",
                            shared_types=self._filter_type_names(imported_names)
                        ))
                else:
                    module = match.group(1)
                    target_workspace = self._resolve_python_import(module, workspace)
                    if target_workspace and target_workspace != workspace.name:
                        imports.append(ImportInfo(
                            source_workspace=workspace.name,
                            target_workspace=target_workspace,
                            source_file=file_path,
                            import_statement=match.group(0),
                            import_type="direct"
                        ))
        
        return imports
    
    def _analyze_javascript_imports(self, content: str, workspace: WorkspaceConfig, file_path: str) -> List[ImportInfo]:
        """Analyze JavaScript/TypeScript imports for cross-workspace dependencies."""
        imports = []
        
        # Patterns for different import types
        import_patterns = [
            # ES6 imports: import X from 'Y', import {X} from 'Y', import * as X from 'Y'
            r'import\s+(?:(?:(\w+)|{([^}]+)}|\*\s+as\s+(\w+))\s+from\s+)?[\'"]([^\'"]+)[\'"]',
            # CommonJS require: require('X')
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
            # Dynamic imports: import('X')
            r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Extract the module path (last group in all patterns)
                module_path = match.groups()[-1]
                
                # Resolve to workspace
                target_workspace, import_type = self._resolve_javascript_import(module_path, workspace)
                if target_workspace and target_workspace != workspace.name:
                    # Extract imported names for type tracking
                    imported_names = []
                    if len(match.groups()) > 1:
                        if match.group(1):  # default import
                            imported_names = [match.group(1)]
                        elif match.group(2):  # named imports
                            imported_names = [name.strip() for name in match.group(2).split(',')]
                        elif match.group(3):  # namespace import
                            imported_names = [match.group(3)]
                    
                    imports.append(ImportInfo(
                        source_workspace=workspace.name,
                        target_workspace=target_workspace,
                        source_file=file_path,
                        import_statement=match.group(0),
                        import_type=import_type,
                        shared_types=self._filter_type_names(imported_names)
                    ))
        
        return imports
    
    def _resolve_python_import(self, import_path: str, workspace: WorkspaceConfig) -> Optional[str]:
        """Resolve a Python import to a workspace name."""
        # Cache key for performance
        cache_key = f"python:{workspace.name}:{import_path}"
        if cache_key in self.import_cache:
            return self.import_cache[cache_key]
        
        result = None
        
        # Check relative imports
        if import_path.startswith('.'):
            # Relative import - check if it goes outside the current workspace
            result = self._resolve_relative_python_import(import_path, workspace)
        else:
            # Absolute import - check if it matches another workspace's package
            for ws_name, pkg_info in self.workspace_packages.items():
                if ws_name != workspace.name and import_path.startswith(pkg_info.get("name", ws_name)):
                    result = ws_name
                    break
        
        self.import_cache[cache_key] = result
        return result
    
    def _resolve_javascript_import(self, import_path: str, workspace: WorkspaceConfig) -> Tuple[Optional[str], str]:
        """Resolve a JavaScript/TypeScript import to a workspace name and import type."""
        cache_key = f"js:{workspace.name}:{import_path}"
        if cache_key in self.import_cache:
            return self.import_cache[cache_key]
        
        result_workspace = None
        import_type = "direct"
        
        if import_path.startswith('.') or import_path.startswith('/'):
            # Relative or absolute path import
            result_workspace, import_type = self._resolve_relative_javascript_import(import_path, workspace)
        else:
            # Package import - check if it's a workspace package
            for ws_name, pkg_info in self.workspace_packages.items():
                if ws_name != workspace.name and import_path == pkg_info.get("name"):
                    result_workspace = ws_name
                    import_type = "package"
                    break
        
        result = (result_workspace, import_type)
        self.import_cache[cache_key] = result
        return result
    
    def _resolve_relative_python_import(self, import_path: str, workspace: WorkspaceConfig) -> Optional[str]:
        """Resolve relative Python imports that might cross workspace boundaries."""
        # This is a simplified implementation - a full version would need to parse
        # the actual directory structure and follow the import path
        
        # Count the number of parent directory references
        parts = import_path.split('.')
        parent_levels = len([p for p in parts if p == ''])
        
        # If it goes up enough levels, it might exit the workspace
        if parent_levels > 2:  # Heuristic
            # Try to resolve the actual path
            current_path = workspace.full_path
            for _ in range(parent_levels):
                current_path = current_path.parent
            
            # Check if this path is in another workspace
            return self.registry.get_workspace_by_path(current_path)
        
        return None
    
    def _resolve_relative_javascript_import(self, import_path: str, workspace: WorkspaceConfig) -> Tuple[Optional[str], str]:
        """Resolve relative JavaScript/TypeScript imports that might cross workspace boundaries."""
        try:
            # Resolve the import path relative to the workspace
            if import_path.startswith('./'):
                # Same directory import
                resolved_path = workspace.full_path / import_path[2:]
            elif import_path.startswith('../'):
                # Parent directory import
                resolved_path = workspace.full_path / import_path
            elif import_path.startswith('/'):
                # Absolute path import (relative to project root)
                resolved_path = self.registry.root_path / import_path[1:]
            else:
                return None, "direct"
            
            resolved_path = resolved_path.resolve()
            
            # Check if resolved path is in another workspace
            target_workspace = self.registry.get_workspace_by_path(resolved_path)
            if target_workspace and target_workspace != workspace.name:
                return target_workspace, "relative"
            
        except Exception:
            pass
        
        return None, "direct"
    
    def _analyze_package_dependencies(self, workspace: WorkspaceConfig) -> List[ImportInfo]:
        """Analyze package.json dependencies for cross-workspace references."""
        imports = []
        
        if workspace.name not in self.workspace_packages:
            return imports
        
        pkg_info = self.workspace_packages[workspace.name]
        
        # Check all dependency types
        dep_types = ["dependencies", "devDependencies", "peerDependencies"]
        for dep_type in dep_types:
            for package_name, version in pkg_info.get(dep_type, {}).items():
                # Check if this package belongs to another workspace
                for ws_name, target_pkg_info in self.workspace_packages.items():
                    if ws_name != workspace.name and target_pkg_info.get("name") == package_name:
                        imports.append(ImportInfo(
                            source_workspace=workspace.name,
                            target_workspace=ws_name,
                            source_file="package.json",
                            import_statement=f'"{package_name}": "{version}"',
                            import_type="package"
                        ))
                        break
        
        return imports
    
    def _build_dependency_graph(self, imports: List[ImportInfo]) -> Dict[str, Dict]:
        """Build the cross-workspace dependency graph."""
        graph = defaultdict(lambda: {
            "imports_from": set(),
            "imported_by": set(),
            "shared_types": set()
        })
        
        # Initialize all workspaces
        for workspace in self.registry.get_all_workspaces():
            graph[workspace.name]  # Ensure all workspaces are in the graph
        
        # Process imports
        for import_info in imports:
            source = import_info.source_workspace
            target = import_info.target_workspace
            
            graph[source]["imports_from"].add(target)
            graph[target]["imported_by"].add(source)
            
            # Add shared types
            if import_info.shared_types:
                graph[source]["shared_types"].update(import_info.shared_types)
        
        # Convert sets to lists for JSON serialization
        result = {}
        for workspace, deps in graph.items():
            result[workspace] = {
                "imports_from": list(deps["imports_from"]),
                "imported_by": list(deps["imported_by"]),
                "shared_types": list(deps["shared_types"])
            }
        
        return result
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, Dict]) -> List[CircularDependency]:
        """Detect circular dependencies using DFS algorithm."""
        circular_deps = []
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            if node in recursion_stack:
                # Found a cycle
                cycle_start_index = path.index(node)
                cycle = path[cycle_start_index:] + [node]
                
                # Create CircularDependency object
                circular_deps.append(CircularDependency(
                    cycle=cycle,
                    imports=[],  # We'll populate this with actual import info if needed
                    severity=self._determine_cycle_severity(cycle)
                ))
                return
            
            if node in visited:
                return
            
            visited.add(node)
            recursion_stack.add(node)
            
            # Visit all dependencies
            for dependency in dependency_graph.get(node, {}).get("imports_from", []):
                dfs(dependency, path + [dependency])
            
            recursion_stack.remove(node)
        
        # Run DFS from each workspace
        for workspace in dependency_graph:
            if workspace not in visited:
                dfs(workspace, [workspace])
        
        return circular_deps
    
    def _determine_cycle_severity(self, cycle: List[str]) -> str:
        """Determine the severity of a circular dependency."""
        if len(cycle) <= 3:
            return "high"  # Direct or simple cycles are more problematic
        elif len(cycle) <= 5:
            return "medium"
        else:
            return "low"  # Long cycles might be less problematic
    
    def _extract_shared_types(self, imports: List[ImportInfo]) -> Dict[str, List[str]]:
        """Extract shared types and interfaces from imports."""
        shared_types = defaultdict(set)
        
        for import_info in imports:
            if import_info.shared_types:
                workspace_pair = f"{import_info.source_workspace} -> {import_info.target_workspace}"
                shared_types[workspace_pair].update(import_info.shared_types)
        
        # Convert to lists for JSON serialization
        return {k: list(v) for k, v in shared_types.items()}
    
    def _build_bidirectional_relationships(self, dependency_graph: Dict[str, Dict]) -> Dict[str, Dict]:
        """Build bidirectional relationship mapping for refactoring impact analysis."""
        relationships = {}
        
        for workspace, deps in dependency_graph.items():
            relationships[workspace] = {
                "affects": deps["imported_by"],  # Workspaces that would be affected if this workspace changes
                "affected_by": deps["imports_from"],  # Workspaces that could affect this one
                "impact_score": len(deps["imported_by"])  # Simple impact metric
            }
        
        return relationships
    
    def _extract_python_types_from_import(self, import_name: str, content: str) -> List[str]:
        """Extract type names from Python imports."""
        # Simple heuristic: look for capitalized names that look like types
        types = []
        if import_name and import_name[0].isupper():
            types.append(import_name)
        return types
    
    def _filter_type_names(self, names: List[str]) -> List[str]:
        """Filter a list of names to likely type/interface names."""
        type_names = []
        for name in names:
            # Heuristic: types usually start with capital letters
            if name and name[0].isupper():
                type_names.append(name)
        return type_names
    
    def _circular_dep_to_dict(self, circular_dep: CircularDependency) -> Dict:
        """Convert CircularDependency to dictionary for serialization."""
        return {
            "cycle": circular_dep.cycle,
            "severity": circular_dep.severity,
            "length": len(circular_dep.cycle) - 1  # Exclude the repeated node
        }


def build_cross_workspace_dependencies(registry: WorkspaceRegistry) -> Dict[str, Dict]:
    """
    Main function to build cross-workspace dependencies.
    This is the key integration function referenced in the MCD.
    
    Args:
        registry: WorkspaceRegistry containing all workspace configurations
        
    Returns:
        Complete cross-workspace dependency analysis results
    """
    analyzer = CrossWorkspaceAnalyzer(registry)
    return analyzer.analyze_all_workspaces()


# CLI interface for testing
if __name__ == "__main__":
    import sys
    from workspace_config import WorkspaceConfigManager
    
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    try:
        config_manager = WorkspaceConfigManager(root_dir)
        registry = config_manager.load_configuration()
        
        print(f"Analyzing {len(registry.get_all_workspaces())} workspaces...")
        results = build_cross_workspace_dependencies(registry)
        
        print("\n=== Cross-Workspace Dependency Analysis Results ===")
        print(f"Total workspaces: {results['analysis_metadata']['total_workspaces']}")
        print(f"Total cross-workspace imports: {results['analysis_metadata']['total_imports']}")
        print(f"Circular dependencies found: {results['analysis_metadata']['circular_count']}")
        
        if results['circular_dependencies']:
            print("\n🔴 Circular Dependencies:")
            for i, cycle in enumerate(results['circular_dependencies'], 1):
                print(f"  {i}. {' -> '.join(cycle['cycle'])} (severity: {cycle['severity']})")
        
        print("\n📊 Dependency Graph Summary:")
        for workspace, deps in results['dependency_graph'].items():
            if deps['imports_from'] or deps['imported_by']:
                print(f"  {workspace}:")
                if deps['imports_from']:
                    print(f"    → imports from: {', '.join(deps['imports_from'])}")
                if deps['imported_by']:
                    print(f"    ← imported by: {', '.join(deps['imported_by'])}")
        
        if results['shared_types']:
            print(f"\n🔗 Shared Types: {len(results['shared_types'])} type relationships found")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)