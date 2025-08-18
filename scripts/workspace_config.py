#!/usr/bin/env python3
"""
Workspace Configuration Management for Claude Code Project Index
Handles loading, validation, and caching of workspace configurations.

Features:
- Load and validate workspace configurations from monorepo tools
- Support manual overrides via .project-index-config.json
- Configuration caching for performance
- Error reporting and validation
- Workspace-specific ignore patterns and settings
- Performance profiles (fast/balanced/comprehensive)
- Advanced configuration options for Phase 4
- Per-workspace indexing depth and inclusion/exclusion settings
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Tuple
from datetime import datetime

from monorepo_detector import MonorepoDetector, DetectionResult


# Performance profile definitions
PERFORMANCE_PROFILES = {
    "fast": {
        "max_files_per_workspace": 200,
        "max_indexing_depth": 2,
        "skip_dependency_analysis": False,
        "skip_cross_workspace_analysis": True,
        "parallel_workers": "auto",  # Use auto-detection
        "enable_caching": True,
        "file_size_limit_mb": 1.0,
        "description": "Fast indexing with limited files and depth"
    },
    "balanced": {
        "max_files_per_workspace": 1000,
        "max_indexing_depth": 4,
        "skip_dependency_analysis": False,
        "skip_cross_workspace_analysis": False,
        "parallel_workers": "auto",
        "enable_caching": True,
        "file_size_limit_mb": 5.0,
        "description": "Balanced performance and completeness"
    },
    "comprehensive": {
        "max_files_per_workspace": -1,  # Unlimited
        "max_indexing_depth": -1,  # Unlimited
        "skip_dependency_analysis": False,
        "skip_cross_workspace_analysis": False,
        "parallel_workers": "conservative",  # Fewer workers for stability
        "enable_caching": True,
        "file_size_limit_mb": 20.0,
        "description": "Complete analysis with no limits"
    }
}


class WorkspaceConfig:
    """Represents configuration for a single workspace."""
    
    def __init__(
        self,
        name: str,
        path: str,
        root_path: Path,
        ignore_patterns: Optional[List[str]] = None,
        custom_settings: Optional[Dict] = None,
        performance_profile: str = "balanced",
        include: bool = True,
        indexing_depth: Optional[int] = None,
        max_files: Optional[int] = None
    ):
        self.name = name
        self.path = path
        self.root_path = root_path
        self.full_path = root_path / path
        self.ignore_patterns = ignore_patterns or []
        self.custom_settings = custom_settings or {}
        self.performance_profile = performance_profile
        self.include = include
        self.indexing_depth = indexing_depth
        self.max_files = max_files
        self.package_manager = self._detect_package_manager()
        
        # Apply performance profile defaults
        self._apply_performance_profile()
    
    def _detect_package_manager(self) -> str:
        """Detect the package manager used in this workspace."""
        if (self.full_path / "package-lock.json").exists():
            return "npm"
        elif (self.full_path / "yarn.lock").exists():
            return "yarn"
        elif (self.full_path / "pnpm-lock.yaml").exists():
            return "pnpm"
        elif (self.full_path / "package.json").exists():
            return "npm"  # Default fallback
        return "unknown"
    
    def _apply_performance_profile(self):
        """Apply performance profile defaults if not explicitly set."""
        if self.performance_profile not in PERFORMANCE_PROFILES:
            self.performance_profile = "balanced"
        
        profile = PERFORMANCE_PROFILES[self.performance_profile]
        
        # Apply defaults only if not explicitly set
        if self.indexing_depth is None:
            depth = profile["max_indexing_depth"]
            self.indexing_depth = depth if depth > 0 else None
        
        if self.max_files is None:
            max_files = profile["max_files_per_workspace"]
            self.max_files = max_files if max_files > 0 else None
        
        # Merge profile settings into custom settings
        for key, value in profile.items():
            if key not in self.custom_settings and not key.startswith("max_"):
                self.custom_settings[key] = value
    
    def get_performance_profile(self) -> Dict:
        """Get the current performance profile settings."""
        return PERFORMANCE_PROFILES.get(self.performance_profile, PERFORMANCE_PROFILES["balanced"])
    
    def should_skip_dependency_analysis(self) -> bool:
        """Check if dependency analysis should be skipped."""
        return self.custom_settings.get("skip_dependency_analysis", False)
    
    def should_skip_cross_workspace_analysis(self) -> bool:
        """Check if cross-workspace analysis should be skipped."""
        return self.custom_settings.get("skip_cross_workspace_analysis", False)
    
    def get_max_files(self) -> Optional[int]:
        """Get the maximum number of files to index."""
        return self.max_files
    
    def get_indexing_depth(self) -> Optional[int]:
        """Get the maximum indexing depth."""
        return self.indexing_depth
    
    def get_file_size_limit_mb(self) -> float:
        """Get the file size limit in MB."""
        return self.custom_settings.get("file_size_limit_mb", 5.0)
    
    def get_ignore_patterns(self) -> Set[str]:
        """Get all ignore patterns for this workspace."""
        patterns = set(self.ignore_patterns)
        
        # Add workspace-specific gitignore if it exists
        workspace_gitignore = self.full_path / ".gitignore"
        if workspace_gitignore.exists():
            try:
                with open(workspace_gitignore, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.add(line)
            except IOError:
                pass
        
        return patterns
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "package_manager": self.package_manager,
            "performance_profile": self.performance_profile,
            "include": self.include,
            "indexing_depth": self.indexing_depth,
            "max_files": self.max_files,
            "ignore_patterns": list(self.get_ignore_patterns()),
            "custom_settings": self.custom_settings
        }


class WorkspaceRegistry:
    """Registry of all workspaces in the monorepo."""
    
    def __init__(self, root_path: Path, detection_result: DetectionResult):
        self.root_path = Path(root_path)
        self.detection_result = detection_result
        self.workspaces: Dict[str, WorkspaceConfig] = {}
        self._dependencies: Dict[str, List[str]] = {}
        self._dependents: Dict[str, List[str]] = {}
        self.errors: List[str] = []
        
        self._load_workspaces()
    
    def _load_workspaces(self):
        """Load workspace configurations from detection result."""
        if not self.detection_result.workspace_registry:
            return
        
        for name, path in self.detection_result.workspace_registry.items():
            try:
                workspace_config = WorkspaceConfig(
                    name=name,
                    path=path,
                    root_path=self.root_path
                )
                self.workspaces[name] = workspace_config
            except Exception as e:
                self.errors.append(f"Failed to load workspace '{name}': {str(e)}")
    
    def get_workspace(self, name: str) -> Optional[WorkspaceConfig]:
        """Get workspace configuration by name."""
        return self.workspaces.get(name)
    
    def get_workspace_by_path(self, file_path: Union[str, Path]) -> Optional[WorkspaceConfig]:
        """Determine which workspace a file belongs to."""
        file_path = Path(file_path)
        
        # Make path relative to root if it's absolute
        if file_path.is_absolute():
            try:
                file_path = file_path.relative_to(self.root_path)
            except ValueError:
                return None
        
        # Find the workspace that contains this file
        best_match = None
        best_match_depth = 0
        
        for workspace in self.workspaces.values():
            workspace_path = Path(workspace.path)
            
            # Check if file is within this workspace
            try:
                relative = file_path.relative_to(workspace_path)
                # Count depth - prefer deeper matches (more specific)
                depth = len(workspace_path.parts)
                if depth > best_match_depth:
                    best_match = workspace
                    best_match_depth = depth
            except ValueError:
                # File is not in this workspace
                continue
        
        return best_match
    
    def get_all_workspaces(self) -> List[WorkspaceConfig]:
        """Get all workspace configurations."""
        return list(self.workspaces.values())
    
    def get_workspace_names(self) -> List[str]:
        """Get all workspace names."""
        return list(self.workspaces.keys())
    
    def set_dependencies(self, workspace_name: str, dependencies: List[str]):
        """Set dependencies for a workspace."""
        self._dependencies[workspace_name] = dependencies
        
        # Update reverse dependencies
        for dep in dependencies:
            if dep not in self._dependents:
                self._dependents[dep] = []
            if workspace_name not in self._dependents[dep]:
                self._dependents[dep].append(workspace_name)
    
    def get_dependencies(self, workspace_name: str) -> List[str]:
        """Get dependencies for a workspace."""
        return self._dependencies.get(workspace_name, [])
    
    def get_dependents(self, workspace_name: str) -> List[str]:
        """Get workspaces that depend on this one."""
        return self._dependents.get(workspace_name, [])
    
    def validate(self) -> List[str]:
        """Validate the workspace configuration."""
        validation_errors = []
        
        # Check that all workspace paths exist
        for name, workspace in self.workspaces.items():
            if not workspace.full_path.exists():
                validation_errors.append(f"Workspace '{name}' path does not exist: {workspace.path}")
            elif not workspace.full_path.is_dir():
                validation_errors.append(f"Workspace '{name}' path is not a directory: {workspace.path}")
        
        # Check for circular dependencies
        def check_circular(workspace_name: str, visited: Set[str], path: List[str]) -> bool:
            if workspace_name in visited:
                return True
            
            visited.add(workspace_name)
            path.append(workspace_name)
            
            for dep in self.get_dependencies(workspace_name):
                if check_circular(dep, visited.copy(), path.copy()):
                    validation_errors.append(f"Circular dependency detected: {' -> '.join(path + [dep])}")
                    return True
            
            return False
        
        for workspace_name in self.workspaces:
            check_circular(workspace_name, set(), [])
        
        return validation_errors + self.errors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.detection_result.tool,
            "detection_method": self.detection_result.detection_method,
            "config_path": self.detection_result.config_path,
            "workspaces": {name: ws.to_dict() for name, ws in self.workspaces.items()},
            "dependencies": dict(self._dependencies),
            "dependents": dict(self._dependents),
            "errors": self.errors
        }


class WorkspaceConfigManager:
    """Main workspace configuration manager with caching and validation."""
    
    _cache: Dict[str, Tuple[WorkspaceRegistry, float]] = {}
    
    def __init__(self, root_path: Union[str, Path]):
        self.root_path = Path(root_path)
    
    def load_configuration(self, force_refresh: bool = False) -> WorkspaceRegistry:
        """
        Load workspace configuration with caching.
        
        Args:
            force_refresh: Force refresh of cached configuration
        
        Returns:
            WorkspaceRegistry instance
        """
        cache_key = str(self.root_path.resolve())
        current_time = datetime.now().timestamp()
        
        # Check cache (5 minute TTL)
        if not force_refresh and cache_key in self._cache:
            registry, cache_time = self._cache[cache_key]
            if current_time - cache_time < 300:  # 5 minutes
                return registry
        
        # Detect monorepo configuration
        detector = MonorepoDetector(self.root_path)
        detection_result = detector.detect()
        
        # Load workspace registry
        registry = WorkspaceRegistry(self.root_path, detection_result)
        
        # Apply manual overrides if present
        registry = self._apply_manual_overrides(registry)
        
        # Cache the result
        self._cache[cache_key] = (registry, current_time)
        
        return registry
    
    def _apply_manual_overrides(self, registry: WorkspaceRegistry) -> WorkspaceRegistry:
        """Apply manual configuration overrides."""
        config_file = self.root_path / ".project-index-config.json"
        
        if not config_file.exists():
            return registry
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            registry.errors.append(f"Failed to parse manual config: {str(e)}")
            return registry
        
        if "monorepo" not in config_data:
            return registry
        
        monorepo_config = config_data["monorepo"]
        
        # Apply global settings
        if "global_settings" in monorepo_config:
            global_settings = monorepo_config["global_settings"]
            # Global settings are handled by the parallel processor and CLI
        
        # Apply workspace-specific overrides
        if "workspace_settings" in monorepo_config:
            workspace_settings = monorepo_config["workspace_settings"]
            
            for workspace_name, settings in workspace_settings.items():
                workspace = registry.get_workspace(workspace_name)
                if workspace:
                    # Apply performance profile
                    if "performance_profile" in settings:
                        workspace.performance_profile = settings["performance_profile"]
                    
                    # Apply inclusion/exclusion
                    if "include" in settings:
                        workspace.include = settings["include"]
                    
                    # Apply indexing depth
                    if "indexing_depth" in settings:
                        workspace.indexing_depth = settings["indexing_depth"]
                    
                    # Apply max files
                    if "max_files" in settings:
                        workspace.max_files = settings["max_files"]
                    
                    # Apply ignore patterns
                    if "ignore_patterns" in settings:
                        workspace.ignore_patterns.extend(settings["ignore_patterns"])
                    
                    # Apply custom settings
                    if "custom_settings" in settings:
                        workspace.custom_settings.update(settings["custom_settings"])
                    
                    # Re-apply performance profile after manual overrides
                    workspace._apply_performance_profile()
        
        # Apply dependency overrides
        if "dependencies" in monorepo_config:
            dependencies = monorepo_config["dependencies"]
            for workspace_name, deps in dependencies.items():
                if isinstance(deps, list):
                    registry.set_dependencies(workspace_name, deps)
        
        return registry
    
    def get_workspace_for_file(self, file_path: Union[str, Path]) -> Optional[WorkspaceConfig]:
        """Get the workspace that contains the given file."""
        registry = self.load_configuration()
        return registry.get_workspace_by_path(file_path)
    
    def validate_configuration(self) -> List[str]:
        """Validate the current workspace configuration."""
        registry = self.load_configuration()
        return registry.validate()
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()
    
    def is_monorepo(self) -> bool:
        """Check if the current project is a monorepo."""
        registry = self.load_configuration()
        return len(registry.workspaces) > 1
    
    def get_monorepo_info(self) -> Dict:
        """Get comprehensive monorepo information."""
        registry = self.load_configuration()
        
        return {
            "is_monorepo": len(registry.workspaces) > 1,
            "tool": registry.detection_result.tool,
            "workspace_count": len(registry.workspaces),
            "workspace_names": registry.get_workspace_names(),
            "detection_method": registry.detection_result.detection_method,
            "config_path": registry.detection_result.config_path,
            "has_errors": bool(registry.errors),
            "errors": registry.errors
        }
    
    def get_workspace_by_performance_profile(self, profile: str) -> List[WorkspaceConfig]:
        """Get all workspaces using a specific performance profile."""
        registry = self.load_configuration()
        return [ws for ws in registry.get_all_workspaces() if ws.performance_profile == profile]
    
    def validate_performance_profile(self, profile: str) -> bool:
        """Validate that a performance profile is valid."""
        return profile in PERFORMANCE_PROFILES
    
    def get_available_performance_profiles(self) -> Dict[str, Dict]:
        """Get all available performance profiles with their descriptions."""
        return PERFORMANCE_PROFILES.copy()
    
    def create_interactive_config(self) -> Dict:
        """Create an interactive configuration template."""
        registry = self.load_configuration()
        
        config_template = {
            "version": "1.0",
            "monorepo": {
                "global_settings": {
                    "performance_profile": "balanced",
                    "parallel_workers": "auto",
                    "memory_limit_mb": 100,
                    "enable_caching": True
                },
                "workspace_settings": {},
                "dependencies": {},
                "ignore_patterns": [
                    "node_modules",
                    ".git",
                    "dist",
                    "build",
                    "*.log"
                ]
            }
        }
        
        # Add template for each workspace
        for workspace in registry.get_all_workspaces():
            config_template["monorepo"]["workspace_settings"][workspace.name] = {
                "performance_profile": workspace.performance_profile,
                "include": workspace.include,
                "indexing_depth": workspace.indexing_depth,
                "max_files": workspace.max_files,
                "ignore_patterns": list(workspace.ignore_patterns),
                "custom_settings": {
                    "skip_dependency_analysis": False,
                    "skip_cross_workspace_analysis": False,
                    "file_size_limit_mb": workspace.get_file_size_limit_mb()
                }
            }
        
        return config_template
    
    def validate_config_file(self, config_path: Optional[Path] = None) -> List[str]:
        """Validate configuration file format and values."""
        if config_path is None:
            config_path = self.root_path / ".project-index-config.json"
        
        validation_errors = []
        
        if not config_path.exists():
            return ["Configuration file not found"]
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            return [f"Invalid JSON format: {str(e)}"]
        except IOError as e:
            return [f"Cannot read config file: {str(e)}"]
        
        # Validate structure
        if "monorepo" not in config_data:
            validation_errors.append("Missing 'monorepo' section")
            return validation_errors
        
        monorepo_config = config_data["monorepo"]
        
        # Validate global settings
        if "global_settings" in monorepo_config:
            global_settings = monorepo_config["global_settings"]
            
            # Validate performance profile
            if "performance_profile" in global_settings:
                profile = global_settings["performance_profile"]
                if not self.validate_performance_profile(profile):
                    validation_errors.append(f"Invalid global performance profile: {profile}")
            
            # Validate memory limit
            if "memory_limit_mb" in global_settings:
                memory_limit = global_settings["memory_limit_mb"]
                if not isinstance(memory_limit, (int, float)) or memory_limit <= 0:
                    validation_errors.append("memory_limit_mb must be a positive number")
        
        # Validate workspace settings
        if "workspace_settings" in monorepo_config:
            workspace_settings = monorepo_config["workspace_settings"]
            registry = self.load_configuration()
            
            for workspace_name, settings in workspace_settings.items():
                if not registry.get_workspace(workspace_name):
                    validation_errors.append(f"Unknown workspace: {workspace_name}")
                    continue
                
                # Validate performance profile
                if "performance_profile" in settings:
                    profile = settings["performance_profile"]
                    if not self.validate_performance_profile(profile):
                        validation_errors.append(f"Invalid performance profile for {workspace_name}: {profile}")
                
                # Validate indexing depth
                if "indexing_depth" in settings:
                    depth = settings["indexing_depth"]
                    if not isinstance(depth, int) or (depth < -1 or depth == 0):
                        validation_errors.append(f"Invalid indexing_depth for {workspace_name}: must be -1 or positive integer")
                
                # Validate max files
                if "max_files" in settings:
                    max_files = settings["max_files"]
                    if not isinstance(max_files, int) or (max_files < -1 or max_files == 0):
                        validation_errors.append(f"Invalid max_files for {workspace_name}: must be -1 or positive integer")
        
        return validation_errors
    
    def get_global_settings(self) -> Dict:
        """Get global configuration settings."""
        config_file = self.root_path / ".project-index-config.json"
        
        default_settings = {
            "performance_profile": "balanced",
            "parallel_workers": "auto",
            "memory_limit_mb": 100,
            "enable_caching": True
        }
        
        if not config_file.exists():
            return default_settings
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            if "monorepo" in config_data and "global_settings" in config_data["monorepo"]:
                global_settings = config_data["monorepo"]["global_settings"]
                # Merge with defaults
                result = default_settings.copy()
                result.update(global_settings)
                return result
        except (json.JSONDecodeError, IOError):
            pass
        
        return default_settings


def load_workspace_config(root_path: Union[str, Path]) -> WorkspaceRegistry:
    """
    Convenience function to load workspace configuration.
    
    Args:
        root_path: Path to the project root directory
    
    Returns:
        WorkspaceRegistry instance
    """
    manager = WorkspaceConfigManager(root_path)
    return manager.load_configuration()


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    manager = WorkspaceConfigManager(root_dir)
    
    # Get monorepo info
    info = manager.get_monorepo_info()
    print("Monorepo Information:")
    print(json.dumps(info, indent=2))
    
    # Validate configuration
    errors = manager.validate_configuration()
    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\nConfiguration is valid.")
    
    # Show workspace details
    registry = manager.load_configuration()
    if registry.workspaces:
        print("\nWorkspaces:")
        for workspace in registry.get_all_workspaces():
            print(f"  {workspace.name}: {workspace.path} ({workspace.package_manager})")
            deps = registry.get_dependencies(workspace.name)
            if deps:
                print(f"    Dependencies: {', '.join(deps)}")
            dependents = registry.get_dependents(workspace.name)
            if dependents:
                print(f"    Dependents: {', '.join(dependents)}")