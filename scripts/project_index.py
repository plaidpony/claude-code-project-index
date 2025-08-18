#!/usr/bin/env python3
"""
Project Index for Claude Code
Provides spatial-architectural awareness to prevent code duplication and misplacement.

Features:
- Directory tree structure visualization
- Markdown documentation mapping with section headers
- Directory purpose inference
- Full function and class signatures with type annotations
- Multi-language support (parsed vs listed)

Usage: python project_index.py
Output: PROJECT_INDEX.json
"""

__version__ = "0.1.0"

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared utilities
from index_utils import (
    IGNORE_DIRS, PARSEABLE_LANGUAGES, CODE_EXTENSIONS, MARKDOWN_EXTENSIONS,
    DIRECTORY_PURPOSES, extract_python_signatures, extract_javascript_signatures,
    extract_shell_signatures, extract_markdown_structure, infer_file_purpose, 
    infer_directory_purpose, get_language_name, should_index_file
)

# Import monorepo support (with fallback for backward compatibility)
try:
    from workspace_config import WorkspaceConfigManager
    from workspace_indexer import WorkspaceIndexer
    from cross_workspace_analyzer import build_cross_workspace_dependencies
    MONOREPO_SUPPORT = True
except ImportError:
    MONOREPO_SUPPORT = False

# Limits to keep it fast and simple
MAX_FILES = 10000
MAX_INDEX_SIZE = 1024 * 1024  # 1MB
MAX_TREE_DEPTH = 5


def generate_tree_structure(root_path: Path, max_depth: int = MAX_TREE_DEPTH) -> List[str]:
    """Generate a compact ASCII tree representation of the directory structure."""
    tree_lines = []
    
    def should_include_dir(path: Path) -> bool:
        """Check if directory should be included in tree."""
        return (
            path.name not in IGNORE_DIRS and
            not path.name.startswith('.') and
            path.is_dir()
        )
    
    def add_tree_level(path: Path, prefix: str = "", depth: int = 0):
        """Recursively build tree structure."""
        if depth > max_depth:
            if any(should_include_dir(p) for p in path.iterdir() if p.is_dir()):
                tree_lines.append(prefix + "└── ...")
            return
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return
        
        # Filter items
        dirs = [item for item in items if should_include_dir(item)]
        
        # Important files to show in tree
        important_files = [
            item for item in items 
            if item.is_file() and (
                item.name in ['README.md', 'package.json', 'requirements.txt', 
                             'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
                             'setup.py', 'pyproject.toml', 'Makefile']
            )
        ]
        
        all_items = dirs + important_files
        
        for i, item in enumerate(all_items):
            is_last = i == len(all_items) - 1
            current_prefix = "└── " if is_last else "├── "
            
            name = item.name
            if item.is_dir():
                name += "/"
                # Add file count for directories
                try:
                    file_count = sum(1 for f in item.rglob('*') if f.is_file() and f.suffix in CODE_EXTENSIONS)
                    if file_count > 0:
                        name += f" ({file_count} files)"
                except:
                    pass
            
            tree_lines.append(prefix + current_prefix + name)
            
            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                add_tree_level(item, next_prefix, depth + 1)
    
    # Start with root
    tree_lines.append(".")
    add_tree_level(root_path, "")
    return tree_lines


# These functions are now imported from index_utils

def _generate_monorepo_tree(root_path: Path, registry) -> List[str]:
    """Generate a high-level tree view for monorepos showing workspaces."""
    tree_lines = ["."]
    
    # Group workspaces by their parent directories
    workspace_groups = {}
    for workspace_name, workspace in registry.workspaces.items():
        workspace_path = Path(workspace.path)
        parent_dir = workspace_path.parent if len(workspace_path.parts) > 1 else Path(".")
        
        if parent_dir not in workspace_groups:
            workspace_groups[parent_dir] = []
        workspace_groups[parent_dir].append((workspace_name, workspace_path))
    
    # Sort parent directories  
    sorted_parents = sorted(workspace_groups.keys(), key=lambda x: str(x))
    
    for i, parent_dir in enumerate(sorted_parents):
        is_last_parent = i == len(sorted_parents) - 1
        parent_prefix = "└── " if is_last_parent else "├── "
        
        if str(parent_dir) == ".":
            # Root-level workspaces
            workspaces = workspace_groups[parent_dir]
            for j, (workspace_name, workspace_path) in enumerate(sorted(workspaces)):
                is_last_workspace = j == len(workspaces) - 1 and is_last_parent
                workspace_prefix = "└── " if is_last_workspace else "├── "
                tree_lines.append(workspace_prefix + f"{workspace_path}/ (workspace: {workspace_name})")
        else:
            # Workspaces under a parent directory
            tree_lines.append(parent_prefix + f"{parent_dir}/")
            
            workspaces = workspace_groups[parent_dir]
            for j, (workspace_name, workspace_path) in enumerate(sorted(workspaces)):
                is_last_workspace = j == len(workspaces) - 1
                workspace_prefix = "    └── " if is_last_workspace else "    ├── "
                if not is_last_parent:
                    workspace_prefix = "│" + workspace_prefix
                
                workspace_dir_name = workspace_path.name
                tree_lines.append(workspace_prefix + f"{workspace_dir_name}/ (workspace: {workspace_name})")
    
    return tree_lines


def build_index(root_dir: str) -> Tuple[Dict, int]:
    """Build the enhanced index with architectural awareness."""
    root = Path(root_dir)
    index = {
        'indexed_at': datetime.now().isoformat(),
        'root': str(root),
        'project_structure': {
            'type': 'tree',
            'root': '.',
            'tree': []
        },
        'documentation_map': {},
        'directory_purposes': {},
        'stats': {
            'total_files': 0,
            'total_directories': 0,
            'fully_parsed': {},
            'listed_only': {},
            'markdown_files': 0
        },
        'files': {},
        'dependency_graph': {}
    }
    
    # Check for monorepo and add monorepo-specific fields if detected
    monorepo_registry = None
    if MONOREPO_SUPPORT:
        try:
            config_manager = WorkspaceConfigManager(root)
            monorepo_registry = config_manager.load_configuration()
            
            # If we detected a monorepo, add monorepo-specific fields
            if monorepo_registry and len(monorepo_registry.workspaces) > 1:
                print("🏢 Monorepo detected! Building enhanced workspace index...")
                
                # Add monorepo metadata to root index
                index['monorepo'] = {
                    'enabled': True,
                    'tool': monorepo_registry.detection_result.tool,
                    'config_path': monorepo_registry.detection_result.config_path,
                    'workspace_pattern': getattr(monorepo_registry.detection_result, 'workspace_pattern', None),
                    'workspaces': {}
                }
                
                # Build workspace registry with metadata
                for workspace_name, workspace in monorepo_registry.workspaces.items():
                    workspace_index_path = f"{workspace.path}/PROJECT_INDEX.json"
                    index['monorepo']['workspaces'][workspace_name] = {
                        'path': workspace.path,
                        'index_path': workspace_index_path,
                        'last_updated': datetime.now().isoformat(),
                        'dependencies': monorepo_registry.get_dependencies(workspace_name),
                        'dependents': monorepo_registry.get_dependents(workspace_name),
                        'package_manager': workspace.package_manager
                    }
                
                # Update global stats to include workspace information
                index['global_stats'] = {
                    'total_workspaces': len(monorepo_registry.workspaces),
                    'total_files': 0,
                    'total_directories': 0,
                    'languages': {}
                }
                
                # Generate individual workspace indexes
                print("📦 Generating individual workspace indexes...")
                workspace_indexer = WorkspaceIndexer(monorepo_registry)
                
                for workspace_name in monorepo_registry.get_workspace_names():
                    workspace_index = workspace_indexer.index_workspace(workspace_name)
                    if workspace_index:
                        # Save individual workspace index
                        workspace_path = monorepo_registry.workspaces[workspace_name].full_path
                        workspace_index_file = workspace_path / "PROJECT_INDEX.json"
                        try:
                            workspace_index_file.write_text(json.dumps(workspace_index, indent=2))
                            print(f"  ✅ {workspace_name}: {workspace_index['stats']['total_files']} files indexed")
                            
                            # Aggregate stats for global summary
                            index['global_stats']['total_files'] += workspace_index['stats']['total_files']
                            index['global_stats']['total_directories'] += workspace_index['stats']['total_directories']
                            
                            # Aggregate language stats
                            for lang_category in ['fully_parsed', 'listed_only']:
                                if lang_category in workspace_index['stats']:
                                    for lang, count in workspace_index['stats'][lang_category].items():
                                        if lang not in index['global_stats']['languages']:
                                            index['global_stats']['languages'][lang] = 0
                                        index['global_stats']['languages'][lang] += count
                        except Exception as e:
                            print(f"  ⚠️ Failed to save index for {workspace_name}: {e}")
                            
                # For monorepos, we focus on the global view in the root index
                # The detailed file indexing will be in individual workspace indexes
                print("🌍 Building global monorepo overview...")
                
                # Generate a high-level tree that shows workspaces
                index['project_structure']['tree'] = _generate_monorepo_tree(root, monorepo_registry)
                
                # Add comprehensive cross-workspace dependency information
                print("🔍 Analyzing cross-workspace dependencies...")
                try:
                    cross_workspace_analysis = build_cross_workspace_dependencies(monorepo_registry)
                    
                    # Add the comprehensive dependency graph
                    index['cross_workspace_dependencies'] = cross_workspace_analysis['dependency_graph']
                    
                    # Add circular dependency information
                    if cross_workspace_analysis['circular_dependencies']:
                        index['circular_dependencies'] = cross_workspace_analysis['circular_dependencies']
                        print(f"  ⚠️ Found {len(cross_workspace_analysis['circular_dependencies'])} circular dependencies")
                    
                    # Add shared types information
                    if cross_workspace_analysis['shared_types']:
                        index['shared_types'] = cross_workspace_analysis['shared_types']
                        print(f"  🔗 Tracked {len(cross_workspace_analysis['shared_types'])} shared type relationships")
                    
                    # Add bidirectional dependency information for refactoring impact analysis
                    index['refactoring_impact_analysis'] = cross_workspace_analysis['bidirectional_dependencies']
                    
                    # Add analysis metadata
                    index['dependency_analysis_metadata'] = cross_workspace_analysis['analysis_metadata']
                    
                    print(f"  ✅ Cross-workspace analysis complete: {cross_workspace_analysis['analysis_metadata']['total_imports']} imports analyzed")
                    
                except Exception as e:
                    print(f"  ⚠️ Cross-workspace analysis failed: {e}")
                    # Fallback to basic dependency tracking
                    index['cross_workspace_dependencies'] = {}
                    for workspace_name in monorepo_registry.get_workspace_names():
                        deps = monorepo_registry.get_dependencies(workspace_name)
                        if deps:
                            index['cross_workspace_dependencies'][workspace_name] = {
                                "imports_from": deps,
                                "imported_by": [],
                                "shared_types": []
                            }
                
                # Return early for monorepos - we've built the registry-focused index
                return index, 0
                
        except Exception as e:
            print(f"⚠️ Monorepo detection failed: {e}")
            print("📁 Falling back to single-repo indexing...")
            # Continue with normal single-repo indexing
    
    # Generate directory tree
    print("📊 Building directory tree...")
    index['project_structure']['tree'] = generate_tree_structure(root)
    
    file_count = 0
    dir_count = 0
    skipped_count = 0
    directory_files = {}  # Track files per directory
    
    # Walk the directory tree
    print("🔍 Indexing files...")
    for file_path in root.rglob('*'):
        if file_count >= MAX_FILES:
            print(f"⚠️  Stopping at {MAX_FILES} files (project too large)")
            break
            
        if file_path.is_dir():
            # Track directories
            if not any(part in IGNORE_DIRS for part in file_path.parts):
                dir_count += 1
                directory_files[file_path] = []
            continue
            
        if not file_path.is_file():
            continue
            
        if not should_index_file(file_path, root):
            skipped_count += 1
            continue
        
        # Track files in their directories
        parent_dir = file_path.parent
        if parent_dir in directory_files:
            directory_files[parent_dir].append(file_path.name)
        
        # Get relative path and language
        rel_path = file_path.relative_to(root)
        
        # Handle markdown files specially
        if file_path.suffix in MARKDOWN_EXTENSIONS:
            doc_structure = extract_markdown_structure(file_path)
            if doc_structure['sections'] or doc_structure['architecture_hints']:
                index['documentation_map'][str(rel_path)] = doc_structure
                index['stats']['markdown_files'] += 1
            continue
        
        # Handle code files
        language = get_language_name(file_path.suffix)
        
        # Base info for all files
        file_info = {
            'language': language,
            'parsed': False
        }
        
        # Add file purpose if we can infer it
        file_purpose = infer_file_purpose(file_path)
        if file_purpose:
            file_info['purpose'] = file_purpose
        
        # Try to parse if we support this language
        if file_path.suffix in PARSEABLE_LANGUAGES:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Extract based on language
                if file_path.suffix == '.py':
                    extracted = extract_python_signatures(content)
                elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                    extracted = extract_javascript_signatures(content)
                elif file_path.suffix in {'.sh', '.bash'}:
                    extracted = extract_shell_signatures(content)
                else:
                    extracted = {'functions': {}, 'classes': {}}
                
                # Only add if we found something
                if extracted['functions'] or extracted['classes']:
                    file_info.update(extracted)
                    file_info['parsed'] = True
                    
                # Update stats
                lang_key = PARSEABLE_LANGUAGES[file_path.suffix]
                index['stats']['fully_parsed'][lang_key] = \
                    index['stats']['fully_parsed'].get(lang_key, 0) + 1
                    
            except Exception as e:
                # Parse error - just list the file
                index['stats']['listed_only'][language] = \
                    index['stats']['listed_only'].get(language, 0) + 1
        else:
            # Language not supported for parsing
            index['stats']['listed_only'][language] = \
                index['stats']['listed_only'].get(language, 0) + 1
        
        # Add to index
        index['files'][str(rel_path)] = file_info
        file_count += 1
        
        # Progress indicator every 100 files
        if file_count % 100 == 0:
            print(f"  Indexed {file_count} files...")
    
    # Infer directory purposes
    print("🏗️  Analyzing directory purposes...")
    for dir_path, files in directory_files.items():
        if files:  # Only process directories with files
            purpose = infer_directory_purpose(dir_path, files)
            if purpose:
                rel_dir = str(dir_path.relative_to(root))
                if rel_dir != '.':
                    index['directory_purposes'][rel_dir] = purpose
    
    index['stats']['total_files'] = file_count
    index['stats']['total_directories'] = dir_count
    
    # Build dependency graph
    print("🔗 Building dependency graph...")
    dependency_graph = {}
    
    for file_path, file_info in index['files'].items():
        if file_info.get('imports'):
            # Normalize imports to resolve relative paths
            file_dir = Path(file_path).parent
            dependencies = []
            
            for imp in file_info['imports']:
                # Handle relative imports
                if imp.startswith('.'):
                    # Resolve relative import
                    if imp.startswith('./'):
                        # Same directory
                        resolved = str(file_dir / imp[2:])
                    elif imp.startswith('../'):
                        # Parent directory
                        parts = imp.split('/')
                        up_levels = len([p for p in parts if p == '..'])
                        target_dir = file_dir
                        for _ in range(up_levels):
                            target_dir = target_dir.parent
                        remaining = '/'.join(p for p in parts if p != '..')
                        resolved = str(target_dir / remaining) if remaining else str(target_dir)
                    else:
                        # Module import like from . import X
                        resolved = str(file_dir)
                    
                    # Try to find actual file
                    for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '']:
                        potential_file = resolved + ext
                        if potential_file in index['files'] or potential_file.replace('\\', '/') in index['files']:
                            dependencies.append(potential_file.replace('\\', '/'))
                            break
                else:
                    # External dependency or absolute import
                    dependencies.append(imp)
            
            if dependencies:
                dependency_graph[file_path] = dependencies
    
    # Only add if not empty
    if dependency_graph:
        index['dependency_graph'] = dependency_graph
    
    # Build bidirectional call graph
    print("📞 Building call graph...")
    call_graph = {}
    called_by_graph = {}
    
    # Process all files to build call relationships
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        # Process functions in this file
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if isinstance(func_data, dict) and 'calls' in func_data:
                    # Track what this function calls
                    full_func_name = f"{file_path}:{func_name}"
                    call_graph[full_func_name] = func_data['calls']
                    
                    # Build reverse index (called_by)
                    for called in func_data['calls']:
                        if called not in called_by_graph:
                            called_by_graph[called] = []
                        called_by_graph[called].append(func_name)
        
        # Process methods in classes
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        if isinstance(method_data, dict) and 'calls' in method_data:
                            # Track what this method calls
                            full_method_name = f"{file_path}:{class_name}.{method_name}"
                            call_graph[full_method_name] = method_data['calls']
                            
                            # Build reverse index
                            for called in method_data['calls']:
                                if called not in called_by_graph:
                                    called_by_graph[called] = []
                                called_by_graph[called].append(f"{class_name}.{method_name}")
    
    # Add called_by information back to functions
    for file_path, file_info in index['files'].items():
        if not isinstance(file_info, dict):
            continue
            
        if 'functions' in file_info:
            for func_name, func_data in file_info['functions'].items():
                if func_name in called_by_graph:
                    if isinstance(func_data, dict):
                        func_data['called_by'] = called_by_graph[func_name]
                    else:
                        # Convert string signature to dict
                        index['files'][file_path]['functions'][func_name] = {
                            'signature': func_data,
                            'called_by': called_by_graph[func_name]
                        }
        
        if 'classes' in file_info:
            for class_name, class_data in file_info['classes'].items():
                if isinstance(class_data, dict) and 'methods' in class_data:
                    for method_name, method_data in class_data['methods'].items():
                        full_name = f"{class_name}.{method_name}"
                        if method_name in called_by_graph or full_name in called_by_graph:
                            callers = called_by_graph.get(method_name, []) + called_by_graph.get(full_name, [])
                            if callers:
                                if isinstance(method_data, dict):
                                    method_data['called_by'] = list(set(callers))
                                else:
                                    # Convert string signature to dict
                                    class_data['methods'][method_name] = {
                                        'signature': method_data,
                                        'called_by': list(set(callers))
                                    }
    
    # Add staleness check
    week_old = datetime.now().timestamp() - 7 * 24 * 60 * 60
    index['staleness_check'] = week_old
    
    return index, skipped_count


# infer_file_purpose is now imported from index_utils


def compress_index_if_needed(index: Dict) -> Dict:
    """Compress index if it exceeds size limit."""
    index_json = json.dumps(index, indent=2)
    
    if len(index_json) <= MAX_INDEX_SIZE:
        return index
    
    print(f"⚠️  Index too large ({len(index_json)} bytes), compressing...")
    
    # First, reduce tree depth
    if len(index['project_structure']['tree']) > 100:
        index['project_structure']['tree'] = index['project_structure']['tree'][:100]
        index['project_structure']['tree'].append("... (truncated)")
    
    # If still too large, remove some listed-only files
    while len(json.dumps(index, indent=2)) > MAX_INDEX_SIZE and index['files']:
        # Find and remove a listed-only file
        for path, info in list(index['files'].items()):
            if not info.get('parsed', False):
                del index['files'][path]
                break
    
    return index


def print_summary(index: Dict, skipped_count: int):
    """Print a helpful summary of what was indexed."""
    # Check if this is a monorepo
    if 'monorepo' in index and index['monorepo'].get('enabled'):
        print_monorepo_summary(index)
        return
    
    # Original single-repo summary
    stats = index['stats']
    
    # Add warning if no files were found
    if stats['total_files'] == 0:
        print("\n⚠️  WARNING: No files were indexed!")
        print("   This might mean:")
        print("   • You're in the wrong directory")
        print("   • All files are being ignored (check .gitignore)")
        print("   • The project has no supported file types")
        print(f"\n   Current directory: {os.getcwd()}")
        print("   Try running from your project root directory.")
        return
    
    print(f"\n📊 Project Analysis Complete:")
    print(f"   📁 {stats['total_directories']} directories indexed")
    print(f"   📄 {stats['total_files']} code files found")
    print(f"   📝 {stats['markdown_files']} documentation files analyzed")
    
    # Show fully parsed languages
    if stats['fully_parsed']:
        print("\n✅ Languages with full parsing:")
        for lang, count in sorted(stats['fully_parsed'].items()):
            print(f"   • {count} {lang.capitalize()} files (with signatures)")
    
    # Show listed-only languages
    if stats['listed_only']:
        print("\n📋 Languages listed only:")
        for lang, count in sorted(stats['listed_only'].items()):
            print(f"   • {count} {lang.capitalize()} files")
    
    # Show documentation insights
    if index['documentation_map']:
        print(f"\n📚 Documentation insights:")
        for doc_file, info in list(index['documentation_map'].items())[:3]:
            print(f"   • {doc_file}: {len(info['sections'])} sections")
    
    # Show directory purposes
    if index['directory_purposes']:
        print(f"\n🏗️  Directory structure:")
        for dir_path, purpose in list(index['directory_purposes'].items())[:5]:
            print(f"   • {dir_path}/: {purpose}")
    
    if skipped_count > 0:
        print(f"\n   (Skipped {skipped_count} files in ignored directories)")


def print_monorepo_summary(index: Dict):
    """Print a summary for monorepo indexing."""
    monorepo_info = index['monorepo']
    global_stats = index.get('global_stats', {})
    
    print(f"\n🏢 Monorepo Analysis Complete:")
    print(f"   🔧 Tool: {monorepo_info['tool'].capitalize()}")
    print(f"   📦 {global_stats.get('total_workspaces', 0)} workspaces indexed")
    print(f"   📄 {global_stats.get('total_files', 0)} total files across all workspaces")
    print(f"   📁 {global_stats.get('total_directories', 0)} total directories")
    
    # Show workspace details
    if monorepo_info['workspaces']:
        print(f"\n📦 Workspaces:")
        for workspace_name, workspace_info in monorepo_info['workspaces'].items():
            deps_info = ""
            if workspace_info['dependencies']:
                deps_info = f" → depends on: {', '.join(workspace_info['dependencies'])}"
            print(f"   • {workspace_name}: {workspace_info['path']}/{deps_info}")
    
    # Show language distribution
    if global_stats.get('languages'):
        print(f"\n🌍 Global Language Distribution:")
        for lang, count in sorted(global_stats['languages'].items()):
            print(f"   • {count} {lang.capitalize()} files")
    
    # Show cross-workspace dependencies
    if 'cross_workspace_dependencies' in index and index['cross_workspace_dependencies']:
        print(f"\n🔗 Cross-Workspace Dependencies:")
        for workspace, deps in index['cross_workspace_dependencies'].items():
            if deps.get('imports_from'):
                print(f"   • {workspace} → {', '.join(deps['imports_from'])}")
    
    # Show circular dependencies if any
    if 'circular_dependencies' in index and index['circular_dependencies']:
        print(f"\n🔴 Circular Dependencies Found: {len(index['circular_dependencies'])}")
        for i, cycle in enumerate(index['circular_dependencies'][:3], 1):  # Show first 3
            print(f"   {i}. {' → '.join(cycle['cycle'])} (severity: {cycle['severity']})")
        if len(index['circular_dependencies']) > 3:
            print(f"   ... and {len(index['circular_dependencies']) - 3} more")
    
    # Show shared types summary
    if 'shared_types' in index and index['shared_types']:
        print(f"\n🔗 Shared Types: {len(index['shared_types'])} type relationships")
    
    # Show dependency analysis metadata
    if 'dependency_analysis_metadata' in index:
        metadata = index['dependency_analysis_metadata']
        print(f"\n📈 Dependency Analysis:")
        print(f"   • {metadata.get('total_imports', 0)} cross-workspace imports analyzed")
        if metadata.get('circular_count', 0) == 0:
            print(f"   • ✅ No circular dependencies detected")
    
    print(f"\n✨ Individual workspace indexes saved to:")
    for workspace_name, workspace_info in monorepo_info['workspaces'].items():
        print(f"   • {workspace_info['index_path']}")
    
    print(f"\n💡 Monorepo Benefits Enabled:")
    print(f"   • Cross-workspace dependency tracking")
    print(f"   • Workspace-aware file routing")
    print(f"   • Hierarchical project structure")
    print(f"   • Individual workspace context preservation")


def main():
    """Run the enhanced indexer."""
    print("🚀 Building Project Index...")
    print("   Analyzing project structure and documentation...")
    
    # Build index for current directory
    index, skipped_count = build_index('.')
    
    # Compress if needed
    index = compress_index_if_needed(index)
    
    # Save to PROJECT_INDEX.json
    output_path = Path('PROJECT_INDEX.json')
    output_path.write_text(json.dumps(index, indent=2))
    
    # Print summary
    print_summary(index, skipped_count)
    
    print(f"\n💾 Saved to: {output_path}")
    print("\n✨ Claude now has architectural awareness of your project!")
    print("   • Knows WHERE to place new code")
    print("   • Understands project structure")
    print("   • Can navigate documentation")
    print("\n📌 Benefits:")
    print("   • Prevents code duplication")
    print("   • Ensures proper file placement")
    print("   • Maintains architectural consistency")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        print(f"PROJECT_INDEX v{__version__}")
        sys.exit(0)
    main()