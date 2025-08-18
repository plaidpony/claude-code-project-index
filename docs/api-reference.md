# API Reference

This document provides detailed API reference for the Project Index monorepo system's internal APIs, useful for advanced users, integrators, and contributors.

## Core Modules

### `monorepo_detector.py`

Main monorepo detection and configuration parsing module.

#### Classes

##### `DetectionResult`
Standardized detection result structure.

```python
@dataclass
class DetectionResult:
    monorepo: bool = False
    tool: Optional[str] = None
    workspace_registry: Optional[Dict[str, str]] = None
    config_path: Optional[str] = None
    detection_method: str = "none"
    errors: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
```

##### `MonorepoDetector`
Main detection orchestrator.

```python
class MonorepoDetector:
    def __init__(self, root_path: Union[str, Path])
    def detect(self) -> DetectionResult
    def _heuristic_detection(self) -> DetectionResult
```

#### Tool-Specific Detectors

All inherit from `BaseDetector`:

```python
class BaseDetector:
    def __init__(self, root_path: Path)
    def detect(self) -> Optional[DetectionResult]
    def _safe_read_json(self, file_path: Path) -> Optional[Dict]
    def _safe_read_yaml(self, file_path: Path) -> Optional[Dict]
    def _resolve_workspace_paths(self, patterns: List[str]) -> Dict[str, str]
```

**Available Detectors:**
- `NxDetector` - Nx monorepos
- `LernaDetector` - Lerna monorepos  
- `YarnWorkspacesDetector` - Yarn workspaces
- `PnpmWorkspacesDetector` - PNPM workspaces
- `RushDetector` - Rush monorepos
- `ManualConfigDetector` - Manual configuration

#### Functions

```python
def detect_monorepo(root_path: Union[str, Path]) -> Dict:
    """
    Main detection entry point.
    
    Args:
        root_path: Project root directory
        
    Returns:
        Dictionary with detection results
    """
```

### `workspace_config.py`

Workspace configuration management and validation.

#### Classes

##### `WorkspaceConfig`
Represents configuration for a single workspace.

```python
class WorkspaceConfig:
    def __init__(self, name: str, path: str, root_path: Path, 
                 ignore_patterns: Optional[List[str]] = None,
                 custom_settings: Optional[Dict] = None)
    
    def get_ignore_patterns(self) -> Set[str]
    def to_dict(self) -> Dict
    def _detect_package_manager(self) -> str
```

**Properties:**
- `name: str` - Workspace name
- `path: Path` - Relative path from root
- `root_path: Path` - Project root path
- `ignore_patterns: Set[str]` - Ignore patterns
- `package_manager: str` - Detected package manager
- `custom_settings: Dict` - Custom workspace settings

##### `WorkspaceRegistry`
Registry of all workspaces in the monorepo.

```python
class WorkspaceRegistry:
    def __init__(self, root_path: Path, detection_result: DetectionResult)
    
    def get_workspace(self, name: str) -> Optional[WorkspaceConfig]
    def get_workspace_by_path(self, file_path: Union[str, Path]) -> Optional[WorkspaceConfig]
    def get_all_workspaces(self) -> List[WorkspaceConfig]
    def get_workspace_names(self) -> List[str]
    def set_dependencies(self, workspace_name: str, dependencies: List[str])
    def get_dependencies(self, workspace_name: str) -> List[str]
    def get_dependents(self, workspace_name: str) -> List[str]
    def validate(self) -> List[str]
    def to_dict(self) -> Dict
```

##### `WorkspaceConfigManager`
Main workspace configuration manager with caching.

```python
class WorkspaceConfigManager:
    def __init__(self, root_path: Union[str, Path])
    
    def load_configuration(self, force_refresh: bool = False) -> WorkspaceRegistry
    def get_workspace_for_file(self, file_path: Union[str, Path]) -> Optional[WorkspaceConfig]
    def validate_configuration(self) -> List[str]
    def clear_cache(self)
    def is_monorepo(self) -> bool
    def get_monorepo_info(self) -> Dict
```

#### Functions

```python
def load_workspace_config(root_path: Union[str, Path]) -> WorkspaceRegistry:
    """
    Load workspace configuration for a project.
    
    Args:
        root_path: Project root directory
        
    Returns:
        WorkspaceRegistry instance
    """
```

### `workspace_indexer.py`

Workspace indexing with cross-workspace awareness.

#### Classes

##### `WorkspaceIndexer`
Indexes individual workspaces with cross-workspace awareness.

```python
class WorkspaceIndexer:
    def __init__(self, registry: WorkspaceRegistry)
    
    def index_workspace(self, workspace_name: str) -> Optional[Dict]
    def index_all_workspaces(self) -> Dict[str, Dict]
    def _generate_workspace_tree(self, workspace_path: Path, workspace_root: str) -> List[str]
    def _parse_file_content(self, content: str, file_extension: str) -> Optional[Dict]
    def _build_workspace_dependency_graph(self, files: Dict) -> Dict
```

##### `CrossWorkspaceDependencyAnalyzer`
Analyzes dependencies between workspaces.

```python
class CrossWorkspaceDependencyAnalyzer:
    def __init__(self, registry: WorkspaceRegistry)
    
    def get_workspace_dependencies(self, workspace_name: str) -> Dict[str, List[str]]
    def analyze_file_imports(self, file_path: Path, workspace: WorkspaceConfig) -> List[str]
```

#### Functions

```python
def index_workspace(root_path: Union[str, Path], workspace_name: str) -> Optional[Dict]:
    """
    Index a specific workspace.
    
    Args:
        root_path: Project root directory
        workspace_name: Name of workspace to index
        
    Returns:
        Workspace index data or None if failed
    """

def index_all_workspaces(root_path: Union[str, Path]) -> Dict[str, Dict]:
    """
    Index all workspaces in a monorepo.
    
    Args:
        root_path: Project root directory
        
    Returns:
        Dictionary mapping workspace names to their index data
    """
```

### `cross_workspace_analyzer.py`

Cross-workspace dependency analysis and relationship tracking.

#### Classes

##### `ImportInfo`
Information about a cross-workspace import.

```python
@dataclass
class ImportInfo:
    source_workspace: str
    target_workspace: str
    source_file: str
    import_statement: str
    import_type: str  # 'direct', 'relative', 'package'
    shared_types: List[str]
```

##### `CircularDependency`
Information about a circular dependency.

```python
@dataclass
class CircularDependency:
    cycle: List[str]
    imports: List[ImportInfo]
    severity: str  # 'low', 'medium', 'high'
```

##### `CrossWorkspaceAnalyzer`
Main cross-workspace analysis engine.

```python
class CrossWorkspaceAnalyzer:
    def __init__(self, registry: WorkspaceRegistry)
    
    def analyze_all_workspaces(self) -> Dict[str, Dict]
    def _analyze_workspace_imports(self, workspace: WorkspaceConfig) -> List[ImportInfo]
    def _analyze_file_imports(self, file_path: Path, workspace: WorkspaceConfig) -> List[ImportInfo]
    def _build_dependency_graph(self, imports: List[ImportInfo]) -> Dict[str, Dict]
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, Dict]) -> List[CircularDependency]
    def _extract_shared_types(self, imports: List[ImportInfo]) -> Dict[str, List[str]]
```

#### Functions

```python
def build_cross_workspace_dependencies(registry: WorkspaceRegistry) -> Dict[str, Dict]:
    """
    Build comprehensive cross-workspace dependency analysis.
    
    Args:
        registry: WorkspaceRegistry instance
        
    Returns:
        Cross-workspace dependency data
    """
```

### `performance_monitor.py`

Performance monitoring and optimization system.

#### Classes

##### `PerformanceMonitor`
Central performance monitoring system.

```python
class PerformanceMonitor:
    def __init__(self)
    
    def set_performance_log_path(self, project_root: Path)
    def start_hook_timing(self, hook_name: str, operation: str, 
                         workspace: Optional[str] = None, 
                         file_path: Optional[str] = None) -> str
    def end_hook_timing(self, timing_id: str, success: bool = True, 
                       error_message: Optional[str] = None)
    def record_cache_hit(self, cache_name: str)
    def record_cache_miss(self, cache_name: str)
    def record_error(self, error_type: str)
    def get_performance_summary(self, hours: int = 24) -> Dict
    def optimize_caches(self, project_root: Path) -> Dict
```

#### Data Classes

```python
@dataclass
class HookTiming:
    hook_name: str
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    workspace: Optional[str]
    file_path: Optional[str]
    operation: str
    success: bool
    error_message: Optional[str]

@dataclass
class CacheStats:
    cache_name: str
    hits: int
    misses: int
    evictions: int
    size: int
    max_size: int
    hit_rate: float

@dataclass
class ResourceUsage:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    process_id: int
```

#### Functions and Decorators

```python
def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""

def performance_timing(hook_name: str, operation: str = "unknown"):
    """Decorator for timing hook operations."""
```

### `update_index.py`

Workspace-aware file update hooks.

#### Functions

```python
def handle_file_update(file_path: Path, project_root: Path) -> None:
    """
    Handle a file update with workspace awareness.
    
    Args:
        file_path: Path to the updated file
        project_root: Project root directory
    """

def get_workspace_for_file(file_path: Path, project_root: Path) -> Optional[str]:
    """
    Determine which workspace a file belongs to.
    
    Args:
        file_path: File path to check
        project_root: Project root directory
        
    Returns:
        Workspace name or None if not in a workspace
    """

def update_workspace_index(workspace_name: str, file_path: Path, 
                          project_root: Path) -> bool:
    """
    Update a specific workspace index.
    
    Args:
        workspace_name: Name of the workspace
        file_path: File that was updated
        project_root: Project root directory
        
    Returns:
        True if update was successful
    """

def handle_cross_workspace_dependencies(workspace_name: str, 
                                      project_root: Path) -> None:
    """
    Handle cascade updates for dependent workspaces.
    
    Args:
        workspace_name: Name of the updated workspace
        project_root: Project root directory
    """
```

## Command Line Interface

### `project_index.py`

Main indexing command with monorepo support.

```bash
python3 scripts/project_index.py [options]
```

**Options:**
- `--workspace <name>` - Index specific workspace only
- `--force` - Force full reindexing
- `--detect-monorepo` - Force monorepo detection
- `--config` - Interactive configuration
- `--health-check` - Run health diagnostics
- `--warm-cache` - Pre-warm caches

### Enhanced Commands

```bash
# Workspace-specific operations
python3 scripts/project_index.py --workspace api
python3 scripts/project_index.py --workspace web --force

# Monorepo operations  
python3 scripts/project_index.py --monorepo --performance fast
python3 scripts/project_index.py --dependencies --output deps.json

# Configuration and diagnostics
python3 scripts/project_index.py --config --interactive
python3 scripts/project_index.py --validate --verbose
```

## Configuration API

### Configuration Schema

```python
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "monorepo": {"type": "boolean"},
        "tool": {"enum": ["nx", "lerna", "yarn", "pnpm", "rush", "manual"]},
        "workspaces": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "ignore_patterns": {"type": "array"},
                        "language_hints": {"type": "array"},
                        "indexing_depth": {"type": "number"}
                    }
                }
            }
        },
        "performance_mode": {"enum": ["fast", "balanced", "comprehensive"]},
        "cross_workspace_analysis": {"type": "boolean"}
    }
}
```

### Environment Variables API

```python
# Performance monitoring
os.environ['PROJECT_INDEX_PERFORMANCE'] = 'fast'
os.environ['PROJECT_INDEX_WORKERS'] = '8' 
os.environ['PROJECT_INDEX_CACHE_TTL'] = '600'
os.environ['PROJECT_INDEX_DEBUG'] = '1'

# Memory limits
os.environ['PROJECT_INDEX_MAX_SIZE'] = '104857600'  # 100MB
os.environ['PROJECT_INDEX_MAX_WORKERS'] = '16'
os.environ['PROJECT_INDEX_STREAMING'] = '1'
```

## Hooks API

### Hook Registration

```python
from scripts.performance_monitor import performance_timing

@performance_timing("workspace_update", "file_change")
def custom_workspace_hook(workspace: str, file_path: str):
    """Custom workspace update hook."""
    pass
```

### Hook Types

1. **PreIndex** - Before indexing starts
2. **PostIndex** - After indexing completes  
3. **FileUpdate** - On individual file changes
4. **WorkspaceUpdate** - On workspace-level changes
5. **CrossWorkspace** - On cross-workspace dependency changes

## Integration APIs

### Claude Code Integration

```python
# CLAUDE.md integration
def update_claude_md(workspace_info: Dict):
    """Update CLAUDE.md with workspace information."""
    content = f"""
@PROJECT_INDEX.json

This monorepo contains {len(workspace_info)} workspaces:
{chr(10).join(f"- {name}: {info['description']}" for name, info in workspace_info.items())}

Use /index --workspace <name> for workspace-specific operations.
"""
```

### External Tool Integration

```python
# VS Code integration
def generate_vscode_settings(workspaces: Dict) -> Dict:
    """Generate VS Code workspace settings."""
    return {
        "folders": [
            {"name": name, "path": config["path"]} 
            for name, config in workspaces.items()
        ],
        "settings": {
            "search.exclude": {
                pattern: True for workspace in workspaces.values() 
                for pattern in workspace.get("ignore_patterns", [])
            }
        }
    }
```

## Error Handling

### Exception Classes

```python
class ProjectIndexError(Exception):
    """Base exception for project index errors."""

class WorkspaceNotFoundError(ProjectIndexError):
    """Workspace not found in registry."""

class ConfigurationError(ProjectIndexError):
    """Configuration validation error."""

class PerformanceError(ProjectIndexError):
    """Performance threshold exceeded."""

class DependencyError(ProjectIndexError):
    """Cross-workspace dependency error."""
```

### Error Handling Patterns

```python
try:
    registry = load_workspace_config(root_path)
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Fallback to single-repo mode
    registry = create_single_repo_registry(root_path)
```

## Testing APIs

### Test Utilities

```python
from tests.test_utils import create_test_monorepo, assert_performance

def test_workspace_indexing():
    """Test workspace indexing functionality."""
    with create_test_monorepo(['api', 'web', 'shared']) as repo_path:
        registry = load_workspace_config(repo_path)
        indexer = WorkspaceIndexer(registry)
        
        result = indexer.index_workspace('api')
        assert result is not None
        assert 'files' in result
        
        # Performance assertion
        assert_performance(lambda: indexer.index_workspace('api'), max_time=2.0)
```

### Mock Utilities

```python
from tests.mocks import MockWorkspaceRegistry, MockPerformanceMonitor

def test_with_mocks():
    """Test with mocked dependencies."""
    with MockWorkspaceRegistry(['test-workspace']) as registry:
        with MockPerformanceMonitor() as monitor:
            # Your test code here
            pass
```

## Extension Points

### Custom Detectors

```python
class CustomDetector(BaseDetector):
    """Custom monorepo tool detector."""
    
    def detect(self) -> Optional[DetectionResult]:
        config_file = self.root_path / "custom-monorepo.json"
        if config_file.exists():
            config = self._safe_read_json(config_file)
            if config and 'workspaces' in config:
                return DetectionResult(
                    monorepo=True,
                    tool='custom',
                    workspace_registry=config['workspaces'],
                    config_path=str(config_file),
                    detection_method='custom_config'
                )
        return None
```

### Custom Analyzers

```python
class CustomAnalyzer:
    """Custom cross-workspace analyzer."""
    
    def analyze_workspace(self, workspace: WorkspaceConfig) -> Dict:
        """Custom workspace analysis logic."""
        return {
            'custom_metrics': self._calculate_metrics(workspace),
            'dependencies': self._extract_dependencies(workspace)
        }
```

## Performance APIs

### Benchmarking API

```python
from scripts.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor()

# Timing context manager
with monitor.timing('custom_operation'):
    # Your operation here
    pass

# Manual timing
timing_id = monitor.start_hook_timing('test', 'benchmark')
# Your operation
monitor.end_hook_timing(timing_id, success=True)

# Get results
summary = monitor.get_performance_summary()
print(f"Average duration: {summary['avg_duration']}ms")
```

### Cache API

```python
from scripts.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()

# Record cache operations
monitor.record_cache_hit('workspace_metadata')
monitor.record_cache_miss('dependency_graph')

# Get cache statistics
cache_stats = monitor.get_performance_summary()['cache_stats']
for cache_name, stats in cache_stats.items():
    print(f"{cache_name}: {stats['hit_rate']:.1%} hit rate")
```

## Migration APIs

### Migration Utilities

```python
def migrate_single_to_monorepo(root_path: Path, 
                              monorepo_tool: str) -> MigrationResult:
    """
    Migrate from single-repo to monorepo configuration.
    
    Args:
        root_path: Project root directory
        monorepo_tool: Target monorepo tool
        
    Returns:
        Migration result with status and details
    """

def validate_migration(old_index: Dict, new_index: Dict) -> ValidationResult:
    """
    Validate migration from old to new index format.
    
    Args:
        old_index: Original index data
        new_index: New index data
        
    Returns:
        Validation result with any issues found
    """
```

## API Usage Examples

### Basic Usage

```python
from scripts.workspace_config import load_workspace_config
from scripts.workspace_indexer import WorkspaceIndexer

# Load configuration
registry = load_workspace_config('/path/to/monorepo')

# Check if monorepo
if registry.detection_result.monorepo:
    print(f"Detected {registry.detection_result.tool} monorepo")
    
    # Index all workspaces
    indexer = WorkspaceIndexer(registry)
    results = indexer.index_all_workspaces()
    
    for workspace_name, index_data in results.items():
        print(f"{workspace_name}: {len(index_data['files'])} files")
```

### Performance Monitoring

```python
from scripts.performance_monitor import get_performance_monitor, performance_timing

monitor = get_performance_monitor()

@performance_timing("custom_analysis", "workspace_processing")
def analyze_workspace(workspace_name: str):
    # Your analysis code
    pass

# Use the decorated function
analyze_workspace("api")

# Get performance summary
summary = monitor.get_performance_summary(hours=1)
print(f"Operations in last hour: {summary['total_operations']}")
```

### Cross-Workspace Analysis

```python
from scripts.cross_workspace_analyzer import build_cross_workspace_dependencies

# Analyze dependencies
deps = build_cross_workspace_dependencies(registry)

# Check for circular dependencies
if deps['circular_dependencies']:
    print("Found circular dependencies:")
    for cycle in deps['circular_dependencies']:
        print(f"  {' -> '.join(cycle['cycle'])}")

# Show workspace relationships
for workspace, dependents in deps['dependents'].items():
    if dependents:
        print(f"{workspace} is used by: {', '.join(dependents)}")
```

For more examples, see the `examples/` directory and the main documentation files.