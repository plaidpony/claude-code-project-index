#!/usr/bin/env python3
"""
Monorepo Commands Module for Claude Code Project Index
Phase 4: Enhanced CLI Commands for advanced monorepo operations

Features:
- Complete CLI command suite for workspace management
- Interactive configuration tools
- Status and health monitoring
- Performance metrics and statistics
- Dependency graph visualization
- Integration with parallel workspace processing
- Backwards compatibility with single-repo setups
"""

import json
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from workspace_config import (
    WorkspaceConfigManager, 
    PERFORMANCE_PROFILES,
    load_workspace_config
)
from parallel_workspace_processor import (
    ParallelWorkspaceProcessor, 
    process_workspaces_parallel,
    process_workspaces_with_analysis
)
from performance_monitor import get_performance_monitor
from project_index import build_index


class MonorepoCommands:
    """Main command handler for monorepo operations."""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.config_manager = WorkspaceConfigManager(self.root_path)
        self.perf_monitor = get_performance_monitor()
        self.perf_monitor.set_performance_log_path(self.root_path)
    
    def index_workspace(self, workspace_name: Optional[str] = None, **kwargs) -> Dict:
        """
        Index a specific workspace or current workspace.
        
        Args:
            workspace_name: Name of workspace to index (None = detect current)
            **kwargs: Additional options
            
        Returns:
            Indexing results
        """
        registry = self.config_manager.load_configuration()
        
        # Detect current workspace if not specified
        if workspace_name is None:
            current_workspace = self.config_manager.get_workspace_for_file(Path.cwd())
            if current_workspace:
                workspace_name = current_workspace.name
            else:
                return {"error": "Not in a workspace directory and no workspace specified"}
        
        # Validate workspace exists
        if not registry.get_workspace(workspace_name):
            available = registry.get_workspace_names()
            return {
                "error": f"Workspace '{workspace_name}' not found",
                "available_workspaces": available
            }
        
        print(f"Indexing workspace: {workspace_name}")
        start_time = time.time()
        
        try:
            # Use parallel processor for consistency
            processor = ParallelWorkspaceProcessor(registry, max_workers=1)
            results = processor.process_workspaces_parallel([workspace_name], show_progress=True)
            
            elapsed = time.time() - start_time
            success = results.get(workspace_name) is not None
            
            return {
                "workspace": workspace_name,
                "success": success,
                "elapsed_time": elapsed,
                "result": results.get(workspace_name),
                "performance": {
                    "target_met": elapsed < 2.0,  # <2s target
                    "elapsed_seconds": elapsed
                }
            }
            
        except Exception as e:
            return {
                "workspace": workspace_name,
                "success": False,
                "error": str(e),
                "elapsed_time": time.time() - start_time
            }
    
    def index_monorepo(self, 
                      force: bool = False, 
                      selective: Optional[List[str]] = None,
                      **kwargs) -> Dict:
        """
        Index the entire monorepo with parallel processing.
        
        Args:
            force: Force recreation of indexes
            selective: List of specific workspaces to index
            **kwargs: Additional options
            
        Returns:
            Monorepo indexing results
        """
        registry = self.config_manager.load_configuration()
        
        if not registry.workspaces:
            return {"error": "No workspaces detected. Is this a monorepo?"}
        
        workspace_names = selective or registry.get_workspace_names()
        print(f"Indexing monorepo with {len(workspace_names)} workspaces")
        
        start_time = time.time()
        
        try:
            # Get global settings for parallel processing
            global_settings = self.config_manager.get_global_settings()
            
            # Create processor with global settings
            max_workers = global_settings.get("parallel_workers", "auto")
            if max_workers == "auto":
                max_workers = None
            elif max_workers == "conservative":
                max_workers = 2
            
            memory_limit = global_settings.get("memory_limit_mb", 100)
            
            processor = ParallelWorkspaceProcessor(
                registry, 
                max_workers=max_workers,
                memory_limit_mb=memory_limit
            )
            
            # Process with full analysis
            results = processor.process_workspaces_with_analysis(
                workspace_names, 
                include_cross_analysis=True,
                show_progress=True
            )
            
            elapsed = time.time() - start_time
            successful = results["processing_stats"]["successful"]
            total = results["processing_stats"]["total_workspaces"]
            
            # Update root index with monorepo structure
            root_index_path = self.root_path / "PROJECT_INDEX.json"
            if force or not root_index_path.exists():
                print("Updating root index with monorepo structure...")
                root_index, _ = build_index(str(self.root_path))
                
                # Add monorepo-specific information
                root_index["monorepo"] = True
                root_index["workspace_registry"] = {
                    ws.name: ws.path for ws in registry.get_all_workspaces()
                }
                root_index["cross_workspace_dependencies"] = results.get("cross_workspace_analysis", {})
                
                with open(root_index_path, 'w') as f:
                    json.dump(root_index, f, indent=2, default=str)
            
            return {
                "success": True,
                "total_workspaces": total,
                "successful_workspaces": successful,
                "failed_workspaces": total - successful,
                "elapsed_time": elapsed,
                "performance": {
                    "target_met": elapsed < 30.0,  # <30s target for 50 workspaces
                    "elapsed_seconds": elapsed,
                    "workspaces_per_second": total / elapsed if elapsed > 0 else 0
                },
                "cross_workspace_analysis": bool(results.get("cross_workspace_analysis")),
                "results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "elapsed_time": time.time() - start_time
            }
    
    def interactive_config(self, **kwargs) -> Dict:
        """
        Launch interactive configuration for monorepo settings.
        
        Returns:
            Configuration results
        """
        try:
            # Generate configuration template
            config_template = self.config_manager.create_interactive_config()
            config_path = self.root_path / ".project-index-config.json"
            
            print(f"Interactive Configuration for {self.root_path}")
            print("=" * 50)
            
            # Display current settings
            registry = self.config_manager.load_configuration()
            if registry.workspaces:
                print(f"Detected {len(registry.workspaces)} workspaces:")
                for ws in registry.get_all_workspaces():
                    print(f"  - {ws.name} ({ws.path}) [{ws.performance_profile}]")
                print()
            
            # Show available performance profiles
            print("Available performance profiles:")
            for name, profile in PERFORMANCE_PROFILES.items():
                print(f"  {name}: {profile['description']}")
            print()
            
            # Interactive prompts would go here in a real implementation
            print("Configuration template generated. To customize:")
            print(f"1. Edit: {config_path}")
            print("2. Available sections:")
            print("   - global_settings: Overall monorepo settings")
            print("   - workspace_settings: Per-workspace customization")
            print("   - dependencies: Manual dependency overrides")
            print("   - ignore_patterns: Global ignore patterns")
            print()
            
            # Write template if it doesn't exist
            if not config_path.exists():
                with open(config_path, 'w') as f:
                    json.dump(config_template, f, indent=2)
                print(f"Created configuration template: {config_path}")
            else:
                print(f"Configuration file exists: {config_path}")
                # Validate existing configuration
                errors = self.config_manager.validate_config_file()
                if errors:
                    print("Configuration validation errors:")
                    for error in errors:
                        print(f"  ❌ {error}")
                else:
                    print("  ✅ Configuration is valid")
            
            return {
                "success": True,
                "config_path": str(config_path),
                "template": config_template,
                "validation_errors": self.config_manager.validate_config_file()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def status(self, **kwargs) -> Dict:
        """
        Show workspace health and status overview.
        
        Returns:
            Status information
        """
        try:
            registry = self.config_manager.load_configuration()
            
            if not registry.workspaces:
                return {
                    "is_monorepo": False,
                    "message": "Not a monorepo - using single repository mode"
                }
            
            # Collect workspace status
            workspace_status = []
            for workspace in registry.get_all_workspaces():
                index_path = workspace.full_path / "PROJECT_INDEX.json"
                
                status_info = {
                    "name": workspace.name,
                    "path": workspace.path,
                    "performance_profile": workspace.performance_profile,
                    "include": workspace.include,
                    "package_manager": workspace.package_manager,
                    "indexed": index_path.exists(),
                    "index_age": None,
                    "dependencies": registry.get_dependencies(workspace.name),
                    "dependents": registry.get_dependents(workspace.name)
                }
                
                # Check index age
                if index_path.exists():
                    try:
                        with open(index_path, 'r') as f:
                            index_data = json.load(f)
                        indexed_at = index_data.get("indexed_at")
                        if indexed_at:
                            index_time = datetime.fromisoformat(indexed_at.replace('Z', '+00:00'))
                            age = datetime.now() - index_time.replace(tzinfo=None)
                            status_info["index_age"] = age.total_seconds() / 3600  # hours
                    except:
                        pass
                
                workspace_status.append(status_info)
            
            # Overall health
            indexed_count = sum(1 for ws in workspace_status if ws["indexed"])
            stale_count = sum(1 for ws in workspace_status 
                            if ws["index_age"] and ws["index_age"] > 24)  # >24 hours
            
            return {
                "is_monorepo": True,
                "tool": registry.detection_result.tool,
                "total_workspaces": len(workspace_status),
                "indexed_workspaces": indexed_count,
                "stale_indexes": stale_count,
                "health_score": indexed_count / len(workspace_status) if workspace_status else 0,
                "workspaces": workspace_status,
                "validation_errors": registry.errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def stats(self, **kwargs) -> Dict:
        """
        Show performance metrics and statistics.
        
        Returns:
            Performance statistics
        """
        try:
            # Get performance summary from monitor
            perf_summary = self.perf_monitor.get_performance_summary(hours=24)
            
            # Get registry info
            registry = self.config_manager.load_configuration()
            
            # Calculate additional metrics
            workspace_breakdown = {}
            for workspace in registry.get_all_workspaces():
                profile = workspace.get_performance_profile()
                if workspace.performance_profile not in workspace_breakdown:
                    workspace_breakdown[workspace.performance_profile] = 0
                workspace_breakdown[workspace.performance_profile] += 1
            
            return {
                "success": True,
                "performance_summary": perf_summary,
                "workspace_breakdown": workspace_breakdown,
                "available_profiles": list(PERFORMANCE_PROFILES.keys()),
                "global_settings": self.config_manager.get_global_settings(),
                "cache_status": {
                    "enabled": True,
                    "workspace_cache_size": len(self.config_manager._cache)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def dependencies(self, format: str = "text", **kwargs) -> Dict:
        """
        Show dependency graph visualization.
        
        Args:
            format: Output format (text, json, dot)
            
        Returns:
            Dependency graph information
        """
        try:
            registry = self.config_manager.load_configuration()
            
            if not registry.workspaces:
                return {"error": "Not a monorepo"}
            
            # Build dependency graph
            dependency_graph = {}
            reverse_deps = {}
            
            for workspace in registry.get_all_workspaces():
                deps = registry.get_dependencies(workspace.name)
                dependency_graph[workspace.name] = deps
                
                for dep in deps:
                    if dep not in reverse_deps:
                        reverse_deps[dep] = []
                    reverse_deps[dep].append(workspace.name)
            
            if format == "text":
                # Generate text visualization
                lines = ["Workspace Dependencies:", "=" * 25]
                for workspace_name in sorted(dependency_graph.keys()):
                    deps = dependency_graph[workspace_name]
                    dependents = reverse_deps.get(workspace_name, [])
                    
                    lines.append(f"\n{workspace_name}:")
                    if deps:
                        lines.append(f"  Depends on: {', '.join(deps)}")
                    if dependents:
                        lines.append(f"  Depended by: {', '.join(dependents)}")
                    if not deps and not dependents:
                        lines.append("  No dependencies")
                
                return {
                    "success": True,
                    "format": "text",
                    "visualization": "\n".join(lines),
                    "dependency_graph": dependency_graph
                }
            
            elif format == "dot":
                # Generate Graphviz DOT format
                dot_lines = [
                    "digraph dependencies {",
                    "  rankdir=TB;",
                    "  node [shape=box];"
                ]
                
                for workspace_name, deps in dependency_graph.items():
                    for dep in deps:
                        dot_lines.append(f'  "{workspace_name}" -> "{dep}";')
                
                dot_lines.append("}")
                
                return {
                    "success": True,
                    "format": "dot", 
                    "visualization": "\n".join(dot_lines),
                    "dependency_graph": dependency_graph
                }
            
            else:  # json format
                return {
                    "success": True,
                    "format": "json",
                    "dependency_graph": dependency_graph,
                    "reverse_dependencies": reverse_deps
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def migrate(self, **kwargs) -> Dict:
        """
        Migrate existing single-repo index to monorepo structure.
        
        Returns:
            Migration results
        """
        try:
            root_index_path = self.root_path / "PROJECT_INDEX.json"
            
            # Check if already a monorepo
            if root_index_path.exists():
                with open(root_index_path, 'r') as f:
                    current_index = json.load(f)
                
                if current_index.get("monorepo"):
                    return {
                        "success": False,
                        "error": "Already configured as monorepo"
                    }
            
            # Detect monorepo structure
            registry = self.config_manager.load_configuration()
            
            if not registry.workspaces:
                return {
                    "success": False,
                    "error": "No monorepo structure detected"
                }
            
            # Backup existing index
            if root_index_path.exists():
                backup_path = root_index_path.with_suffix(".json.backup")
                root_index_path.rename(backup_path)
                print(f"Backed up existing index to {backup_path}")
            
            # Run full monorepo indexing
            result = self.index_monorepo(force=True)
            
            if result["success"]:
                return {
                    "success": True,
                    "migrated_to_monorepo": True,
                    "workspaces_indexed": result["successful_workspaces"],
                    "elapsed_time": result["elapsed_time"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Migration failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """CLI entry point for monorepo commands."""
    parser = argparse.ArgumentParser(description="Monorepo Commands for Claude Code Project Index")
    parser.add_argument("--root", "-r", default=".", help="Root directory path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # /index --workspace
    workspace_parser = subparsers.add_parser("workspace", help="Index specific workspace")
    workspace_parser.add_argument("name", nargs="?", help="Workspace name (auto-detect if not specified)")
    
    # /index --monorepo
    monorepo_parser = subparsers.add_parser("monorepo", help="Index entire monorepo")
    monorepo_parser.add_argument("--force", action="store_true", help="Force recreation of indexes")
    monorepo_parser.add_argument("--selective", nargs="*", help="Index only specified workspaces")
    
    # /index --config
    subparsers.add_parser("config", help="Interactive configuration")
    
    # /index --status
    subparsers.add_parser("status", help="Show workspace status")
    
    # /index --stats
    subparsers.add_parser("stats", help="Show performance statistics")
    
    # /index --dependencies
    deps_parser = subparsers.add_parser("dependencies", help="Show dependency graph")
    deps_parser.add_argument("--format", choices=["text", "json", "dot"], default="text", 
                           help="Output format")
    
    # /index --migrate
    subparsers.add_parser("migrate", help="Migrate to monorepo structure")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create command handler
    commands = MonorepoCommands(args.root)
    
    # Execute command
    try:
        if args.command == "workspace":
            result = commands.index_workspace(args.name)
        elif args.command == "monorepo":
            result = commands.index_monorepo(force=args.force, selective=args.selective)
        elif args.command == "config":
            result = commands.interactive_config()
        elif args.command == "status":
            result = commands.status()
        elif args.command == "stats":
            result = commands.stats()
        elif args.command == "dependencies":
            result = commands.dependencies(format=args.format)
        elif args.command == "migrate":
            result = commands.migrate()
        else:
            result = {"error": f"Unknown command: {args.command}"}
        
        # Output result
        if result.get("success", True):
            if "visualization" in result:
                print(result["visualization"])
            else:
                print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()