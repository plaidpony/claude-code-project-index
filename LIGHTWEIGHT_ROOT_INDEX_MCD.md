# Lightweight Root Index Architecture MCD (Main Context Document)

## 🎯 Overview & Goals

### Project Vision
Transform the current monorepo project indexer from a single-file, heavyweight approach to a hierarchical, lightweight root index system that scales efficiently with large monorepos without performance bottlenecks.

### Target Users
- **Development Teams**: Working with large monorepos (>1000 files, >10 workspaces)
- **Claude Code Users**: Needing fast architectural awareness without waiting for compression
- **CI/CD Systems**: Requiring quick index generation and updates
- **Project Maintainers**: Managing complex multi-workspace dependencies

### Core Features
1. **Lightweight Root Registry**: Root `PROJECT_INDEX.json` contains only workspace metadata (~100KB max)
2. **Individual Workspace Indexes**: Detailed file information stored per workspace
3. **Lazy Loading**: Load workspace details only when needed
4. **Fast Compression**: Eliminate infinite loops and reduce serialization overhead
5. **Hierarchical Updates**: Update only affected workspaces, not entire index

### Success Criteria
- Root index generation completes in <30 seconds for any monorepo size
- Root index file size stays under 200KB regardless of monorepo scale
- Workspace index updates affect only relevant workspaces
- No infinite loops during compression
- Maintain backward compatibility with single-repo projects

### Business Context
Large monorepos are becoming standard in enterprise development. The current indexer fails at scale, creating 30+ minute hangs that block developer workflows. This architectural change enables Claude Code to work seamlessly with enterprise codebases.

## 🏗️ Technical Architecture

### Current Architecture Issues
```
Current: Single Monolithic Index
┌─────────────────────────┐
│  PROJECT_INDEX.json     │ ← 2.2MB, causes infinite loop
│  - All files           │
│  - All workspaces      │
│  - All dependencies    │
└─────────────────────────┘
```

### Proposed Hierarchical Architecture
```
New: Lightweight Root + Detailed Workspaces
┌─────────────────────────┐
│  PROJECT_INDEX.json     │ ← <200KB, fast generation
│  - Workspace registry   │
│  - Cross-workspace deps │
│  - Global metadata      │
└─────────────────────────┘
           │
           ├── workspace1/PROJECT_INDEX.json (detailed)
           ├── workspace2/PROJECT_INDEX.json (detailed)
           └── workspace3/PROJECT_INDEX.json (detailed)
```

### Technology Choices
- **Python 3.8+**: Existing codebase compatibility
- **JSON**: Human-readable, Claude-compatible format
- **File-based Storage**: No database dependencies
- **Lazy Loading Pattern**: Load details on-demand
- **Batch Processing**: Efficient workspace updates

### API Integration Points
- **Claude Code**: Reads root index first, then specific workspace indexes
- **Git Hooks**: Update only affected workspaces
- **CI/CD**: Parallel workspace index generation
- **IDE Extensions**: Quick architectural queries from root index

## 📋 Detailed Implementation

### Root Index Schema
```json
{
  "indexed_at": "ISO timestamp",
  "root": ".",
  "index_type": "hierarchical_root",
  "monorepo": {
    "enabled": true,
    "tool": "nx|lerna|pnpm|rush|manual",
    "total_workspaces": 12,
    "workspace_registry": {
      "workspace-name": {
        "path": "relative/path",
        "index_path": "relative/path/PROJECT_INDEX.json",
        "package_manager": "npm|yarn|pnpm",
        "last_updated": "ISO timestamp",
        "file_count": 150,
        "status": "indexed|stale|error"
      }
    }
  },
  "cross_workspace_dependencies": {
    "workspace-a": ["workspace-b", "shared-lib"],
    "workspace-b": ["shared-lib"]
  },
  "global_stats": {
    "total_workspaces": 12,
    "total_files": 5000,
    "indexed_workspaces": 12,
    "failed_workspaces": 0
  },
  "project_structure": {
    "type": "workspace_overview",
    "tree": ["high-level workspace tree"]
  }
}
```

### Workspace Index Schema
```json
{
  "workspace_name": "api-service",
  "workspace_path": "services/api",
  "indexed_at": "ISO timestamp", 
  "parent_index": "../../PROJECT_INDEX.json",
  "files": {
    "detailed file information per current schema"
  },
  "stats": "current file statistics",
  "dependency_graph": "workspace-specific dependencies",
  "cross_workspace_imports": [
    {
      "import": "@shared/utils",
      "target_workspace": "shared-utils",
      "file": "src/index.ts"
    }
  ]
}
```

### Core Components

#### 1. HierarchicalIndexManager
```python
class HierarchicalIndexManager:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.workspace_registry = None
        
    def build_root_index(self) -> Dict:
        """Build lightweight root index with workspace registry"""
        
    def build_workspace_index(self, workspace_name: str) -> Dict:
        """Build detailed index for specific workspace"""
        
    def update_workspace_index(self, workspace_name: str, changed_files: List[str]):
        """Incrementally update specific workspace index"""
```

#### 2. LazyIndexLoader  
```python
class LazyIndexLoader:
    def load_root_index(self) -> Dict:
        """Load root index for architectural overview"""
        
    def load_workspace_index(self, workspace_name: str) -> Dict:
        """Load detailed workspace index on demand"""
        
    def get_cross_workspace_dependencies(self) -> Dict:
        """Get dependency graph from root index"""
```

#### 3. SmartCompressor
```python
class SmartCompressor:
    def compress_root_index(self, index: Dict) -> Dict:
        """Lightweight compression - remove only non-essential metadata"""
        
    def compress_workspace_index(self, index: Dict) -> Dict:
        """Standard compression for workspace details"""
```

## 📁 File Structure & Organization

### Directory Layout
```
project-root/
├── PROJECT_INDEX.json              # Lightweight root index
├── scripts/
│   ├── hierarchical_indexer.py     # New main indexer
│   ├── lazy_index_loader.py        # Lazy loading utilities
│   ├── smart_compressor.py         # Improved compression
│   └── project_index.py            # Modified to support hierarchical
├── services/
│   ├── api/
│   │   └── PROJECT_INDEX.json      # Detailed workspace index
│   └── auth/
│       └── PROJECT_INDEX.json      # Detailed workspace index
└── packages/
    ├── shared/
    │   └── PROJECT_INDEX.json      # Detailed workspace index
    └── ui/
        └── PROJECT_INDEX.json      # Detailed workspace index
```

### Naming Conventions
- **Root Index**: `PROJECT_INDEX.json` (lightweight)
- **Workspace Indexes**: `{workspace-path}/PROJECT_INDEX.json` (detailed)
- **Python Modules**: `hierarchical_*` prefix for new components
- **Backup Files**: `.PROJECT_INDEX.backup.json` during updates

### Environment Setup
- Existing Python environment compatibility
- No additional dependencies required
- Backward compatibility flags for single-repo projects

## ✅ Task Breakdown

### Phase 1: Core Infrastructure (Week 1)
**Task 1.1: Create HierarchicalIndexManager**
- **Deliverable**: `hierarchical_indexer.py` with root index generation
- **Acceptance Criteria**: 
  - Root index under 200KB for any monorepo
  - Generates in <30 seconds
  - Contains complete workspace registry
- **Dependencies**: None
- **Complexity**: Medium

**Task 1.2: Implement LazyIndexLoader**  
- **Deliverable**: `lazy_index_loader.py` with on-demand loading
- **Acceptance Criteria**:
  - Loads root index in <2 seconds
  - Caches loaded workspace indexes
  - Handles missing workspace indexes gracefully
- **Dependencies**: Task 1.1
- **Complexity**: Low

**Task 1.3: Create SmartCompressor**
- **Deliverable**: `smart_compressor.py` with efficient compression
- **Acceptance Criteria**:
  - No infinite loops
  - Batch processing for file removal
  - Progress indicators during compression
- **Dependencies**: None  
- **Complexity**: Medium

### Phase 2: Integration (Week 2)
**Task 2.1: Modify project_index.py**
- **Deliverable**: Updated main script with hierarchical support  
- **Acceptance Criteria**:
  - Detects monorepo vs single-repo
  - Routes to appropriate indexer
  - Maintains backward compatibility
- **Dependencies**: Phase 1 complete
- **Complexity**: High

**Task 2.2: Update Hook Scripts**
- **Deliverable**: Modified update hooks for workspace-specific updates
- **Acceptance Criteria**:
  - Updates only affected workspace indexes
  - Updates root index when workspace structure changes
  - Performance improvement over current hooks
- **Dependencies**: Task 2.1
- **Complexity**: Medium

### Phase 3: Enhancement & Testing (Week 3)
**Task 3.1: Cross-Workspace Dependency Tracking**
- **Deliverable**: Enhanced dependency analysis in root index
- **Acceptance Criteria**:
  - Accurate cross-workspace import detection
  - Circular dependency detection
  - Performance impact analysis
- **Dependencies**: Phase 2 complete
- **Complexity**: High

**Task 3.2: Comprehensive Testing**
- **Deliverable**: Test suite covering all scenarios
- **Acceptance Criteria**: 
  - 90%+ code coverage
  - Tests for large monorepos (1000+ files)
  - Performance regression tests
- **Dependencies**: All previous tasks
- **Complexity**: Medium

## 🔗 Integration & Dependencies

### Internal Component Relationships
```
HierarchicalIndexManager
    ├── depends on: workspace_config.py (existing)
    ├── depends on: monorepo_detector.py (existing)
    └── uses: SmartCompressor

LazyIndexLoader  
    ├── depends on: HierarchicalIndexManager
    └── caches: workspace indexes

SmartCompressor
    ├── replaces: compress_index_if_needed() in project_index.py
    └── uses: batch processing algorithms
```

### External Service Integrations
- **Claude Code**: Reads root index first, loads workspace details on-demand
- **Git Hooks**: Trigger workspace-specific index updates
- **CI/CD Pipelines**: Parallel workspace indexing for faster builds
- **IDE Extensions**: Quick architecture queries from lightweight root

### Data Flow
1. **Index Generation**: Root → Individual Workspaces (parallel)
2. **Index Loading**: Root (always) → Workspace (on-demand)  
3. **Index Updates**: Affected Workspace → Root (if structure changes)
4. **Dependency Analysis**: Root Index → Cross-workspace imports

### Error Handling Strategies
- **Missing Workspace Index**: Generate on-demand with warning
- **Corrupted Root Index**: Regenerate from workspace detection
- **Workspace Indexing Failure**: Mark as failed in root, continue others
- **Cross-workspace Dependency Errors**: Log warnings, don't fail build

## 🧪 Testing Strategy

### Unit Tests
```python
# test_hierarchical_indexer.py
def test_root_index_size_limit()
def test_workspace_registry_completeness() 
def test_monorepo_detection_integration()

# test_lazy_loader.py  
def test_root_index_loading_performance()
def test_workspace_index_caching()
def test_missing_index_handling()

# test_smart_compressor.py
def test_no_infinite_loops()
def test_batch_compression_efficiency()
def test_compression_effectiveness()
```

### Integration Tests  
```python
# test_end_to_end.py
def test_large_monorepo_indexing_performance()  # 1000+ files
def test_nx_monorepo_integration()
def test_lerna_monorepo_integration()
def test_pnpm_workspace_integration()
def test_backward_compatibility_single_repo()
```

### Performance Tests
```python
# test_performance.py
def test_root_index_generation_time()      # <30 seconds target
def test_workspace_index_loading_time()    # <2 seconds target  
def test_memory_usage_large_monorepos()    # Memory efficiency
def test_compression_performance()         # vs current implementation
```

### Acceptance Criteria
- Root index generation: <30 seconds for any monorepo
- Root index size: <200KB regardless of monorepo scale
- No infinite loops during any operation
- Workspace loading: <2 seconds per workspace
- Memory usage: <500MB for 5000+ file monorepos

## 🚀 Deployment & Operations

### Environment Configuration
```bash
# Environment Variables
PROJECT_INDEX_MODE=hierarchical  # vs 'legacy' for single-repo
MAX_ROOT_INDEX_SIZE=204800       # 200KB limit
WORKSPACE_INDEX_TIMEOUT=300      # 5 minute timeout per workspace
ENABLE_WORKSPACE_PARALLEL=true   # Parallel workspace processing
```

### Deployment Process
1. **Backward Compatibility Phase**: Deploy with feature flag
2. **Gradual Rollout**: Enable for specific monorepos first  
3. **Performance Monitoring**: Track index generation times
4. **Full Migration**: Default to hierarchical mode
5. **Legacy Cleanup**: Remove old compression logic after validation

### Monitoring Approach
```python
# Performance Metrics
- root_index_generation_time_seconds
- workspace_index_generation_time_seconds  
- root_index_size_bytes
- workspace_index_count
- compression_infinite_loop_incidents (should be 0)
```

### Scaling Strategies  
- **Horizontal**: Parallel workspace index generation
- **Vertical**: Optimize workspace index size limits
- **Caching**: Redis cache for frequently-accessed workspace indexes
- **CDN**: Distribute workspace indexes for large distributed teams

### Migration Strategy
1. **Week 1**: Deploy alongside existing system with feature flag
2. **Week 2**: Enable for internal testing monorepos
3. **Week 3**: Enable for select customer monorepos  
4. **Week 4**: Default to hierarchical mode
5. **Week 5**: Remove legacy compression logic

This MCD provides the complete blueprint for implementing the Lightweight Root Index architecture, eliminating the infinite loop compression issue while enabling Claude Code to scale efficiently with enterprise monorepos.