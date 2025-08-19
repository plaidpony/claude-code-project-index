"""
Lazy Index Loader for Claude Code Project Index

This module provides on-demand, cached loading of root and workspace indexes
with multi-level caching, LRU eviction, and dependency-aware cache invalidation.

Key Features:
- Sub-2-second loading performance for root and workspace indexes
- Multi-level caching (workspace mapping, dependency, filesystem, workspace indexes)
- LRU eviction with adaptive memory sizing (<100MB for 50+ workspaces)
- Dependency-aware cache invalidation
- Staleness detection for selective reloads
- Thread-safe cache operations
"""

import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, Any
import weakref
import hashlib

import sys
from pathlib import Path

# Add scripts directory to path if needed
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from hierarchical_indexer import HierarchicalIndexManager
    from workspace_config import WorkspaceConfigManager, WorkspaceRegistry
except ImportError as e:
    print(f"⚠️  Import error in lazy_index_loader: {e}")
    print("   Some features may not be available")
    HierarchicalIndexManager = None
    WorkspaceConfigManager = None
    WorkspaceRegistry = None


class CacheEntry:
    """Represents a single cache entry with metadata."""
    
    def __init__(self, data: Any, timestamp: float, size_bytes: int, access_count: int = 0):
        self.data = data
        self.timestamp = timestamp
        self.size_bytes = size_bytes
        self.access_count = access_count
        self.last_access = timestamp
    
    def access(self):
        """Mark this entry as accessed."""
        self.access_count += 1
        self.last_access = time.time()
    
    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if this cache entry is stale."""
        return time.time() - self.timestamp > max_age_seconds


class LRUCache:
    """Thread-safe LRU cache with size limits and staleness checking."""
    
    def __init__(self, max_size_mb: int = 50, max_entries: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.cache = OrderedDict()
        self.current_size_bytes = 0
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str, max_age_seconds: int = 3600) -> Optional[Any]:
        """Get item from cache if it exists and is not stale."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_stale(max_age_seconds):
                    self._remove_entry(key)
                    self.misses += 1
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.access()
                self.hits += 1
                return entry.data
            
            self.misses += 1
            return None
    
    def put(self, key: str, data: Any, size_bytes: Optional[int] = None) -> None:
        """Put item into cache, evicting old entries if necessary."""
        if size_bytes is None:
            size_bytes = self._estimate_size(data)
        
        with self.lock:
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)
            
            # Create new entry
            entry = CacheEntry(data, time.time(), size_bytes)
            
            # Evict entries if necessary
            while (len(self.cache) >= self.max_entries or 
                   self.current_size_bytes + size_bytes > self.max_size_bytes):
                if not self.cache:
                    break
                oldest_key = next(iter(self.cache))
                self._remove_entry(oldest_key)
                self.evictions += 1
            
            # Add new entry
            self.cache[key] = entry
            self.current_size_bytes += size_bytes
    
    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all keys matching pattern. Returns count of removed items."""
        with self.lock:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self._remove_entry(key)
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.current_size_bytes = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests) if total_requests > 0 else 0
            
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": hit_rate,
                "entries": len(self.cache),
                "size_mb": self.current_size_bytes / (1024 * 1024),
                "max_size_mb": self.max_size_bytes / (1024 * 1024)
            }
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and update size tracking."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_size_bytes -= entry.size_bytes
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate the memory size of data."""
        try:
            if isinstance(data, (dict, list)):
                return len(json.dumps(data, separators=(',', ':')).encode('utf-8'))
            elif isinstance(data, str):
                return len(data.encode('utf-8'))
            else:
                return 1024  # Default estimate
        except:
            return 1024


class LazyIndexLoader:
    """
    Provides on-demand loading and caching of project indexes.
    
    Implements multi-level caching with dependency-aware invalidation
    to achieve sub-2-second loading times while maintaining data consistency.
    """
    
    def __init__(self, root_path: Union[str, Path], cache_size_mb: int = 100):
        self.root_path = Path(root_path).resolve()
        self.workspace_manager = WorkspaceConfigManager(self.root_path)
        
        # Multi-level caches
        self.workspace_mapping_cache = LRUCache(max_size_mb=5, max_entries=100)
        self.dependency_cache = LRUCache(max_size_mb=10, max_entries=200)
        self.filesystem_cache = LRUCache(max_size_mb=15, max_entries=500)
        self.workspace_index_cache = LRUCache(max_size_mb=cache_size_mb - 30, max_entries=50)
        
        # Root index cache (separate, smaller)
        self.root_index_cache = LRUCache(max_size_mb=5, max_entries=10)
        
        # File modification time tracking for staleness detection
        self.file_mtimes = {}
        self.lock = threading.RLock()
        
        # Dependency tracking for cascade invalidation
        self.dependency_graph = {}
        
    def load_root_index(self, max_age_seconds: int = 3600, force_refresh: bool = False) -> Dict:
        """
        Load the root index with caching.
        
        Args:
            max_age_seconds: Maximum age for cached data
            force_refresh: Force reload from disk
            
        Returns:
            Root index dictionary
        """
        cache_key = "root_index"
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.root_index_cache.get(cache_key, max_age_seconds)
            if cached_data is not None:
                return cached_data
        
        # Load from disk
        root_index_path = self.root_path / "PROJECT_INDEX.json"
        
        if not root_index_path.exists():
            # Generate new root index
            manager = HierarchicalIndexManager(self.root_path)
            root_index = manager.generate_root_index()
            manager.save_root_index(root_index)
        else:
            # Check if file is stale
            if self._is_file_stale(root_index_path):
                manager = HierarchicalIndexManager(self.root_path)
                root_index = manager.generate_root_index()
                manager.save_root_index(root_index)
            else:
                # Load from disk
                with open(root_index_path) as f:
                    root_index = json.load(f)
        
        # Cache and return
        self.root_index_cache.put(cache_key, root_index)
        self._update_file_mtime(root_index_path)
        
        return root_index
    
    def load_workspace_index(self, workspace_name: str, 
                           max_age_seconds: int = 3600, 
                           force_refresh: bool = False) -> Optional[Dict]:
        """
        Load a specific workspace index with caching.
        
        Args:
            workspace_name: Name of the workspace
            max_age_seconds: Maximum age for cached data
            force_refresh: Force reload from disk
            
        Returns:
            Workspace index dictionary or None if not found
        """
        cache_key = f"workspace:{workspace_name}"
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.workspace_index_cache.get(cache_key, max_age_seconds)
            if cached_data is not None:
                return cached_data
        
        # Get workspace configuration
        workspace_info = self._get_workspace_mapping(workspace_name)
        if not workspace_info:
            return None
        
        workspace_index_path = self.root_path / workspace_info["index_path"]
        
        if not workspace_index_path.exists():
            return None
        
        # Check staleness
        if self._is_file_stale(workspace_index_path):
            # Workspace index is stale, but don't regenerate here
            # Let the workspace indexer handle regeneration
            return None
        
        # Load from disk
        try:
            with open(workspace_index_path) as f:
                workspace_index = json.load(f)
            
            # Cache and return
            self.workspace_index_cache.put(cache_key, workspace_index)
            self._update_file_mtime(workspace_index_path)
            
            return workspace_index
        except (json.JSONDecodeError, IOError):
            return None
    
    def get_workspace_dependencies(self, workspace_name: str) -> List[str]:
        """
        Get dependencies for a workspace with caching.
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            List of workspace names this workspace depends on
        """
        cache_key = f"deps:{workspace_name}"
        
        # Check cache first
        cached_deps = self.dependency_cache.get(cache_key)
        if cached_deps is not None:
            return cached_deps
        
        # Load from root index
        root_index = self.load_root_index()
        cross_deps = root_index.get("cross_workspace_dependencies", {})
        workspace_deps = cross_deps.get(workspace_name, [])
        
        # Cache and return
        self.dependency_cache.put(cache_key, workspace_deps)
        
        return workspace_deps
    
    def get_workspace_dependents(self, workspace_name: str) -> List[str]:
        """
        Get workspaces that depend on the given workspace.
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            List of workspace names that depend on this workspace
        """
        cache_key = f"dependents:{workspace_name}"
        
        # Check cache first
        cached_dependents = self.dependency_cache.get(cache_key)
        if cached_dependents is not None:
            return cached_dependents
        
        # Build reverse dependency mapping
        root_index = self.load_root_index()
        cross_deps = root_index.get("cross_workspace_dependencies", {})
        
        dependents = []
        for ws_name, deps in cross_deps.items():
            if workspace_name in deps:
                dependents.append(ws_name)
        
        # Cache and return
        self.dependency_cache.put(cache_key, dependents)
        
        return dependents
    
    def invalidate_workspace(self, workspace_name: str, cascade: bool = True) -> None:
        """
        Invalidate cache for a workspace and optionally its dependents.
        
        Args:
            workspace_name: Name of workspace to invalidate
            cascade: Whether to invalidate dependent workspaces
        """
        with self.lock:
            # Invalidate workspace index cache
            self.workspace_index_cache.invalidate(f"workspace:{workspace_name}")
            
            # Invalidate dependency caches
            self.dependency_cache.invalidate(f"deps:{workspace_name}")
            self.dependency_cache.invalidate(f"dependents:{workspace_name}")
            
            # Cascade invalidation to dependents
            if cascade:
                dependents = self.get_workspace_dependents(workspace_name)
                for dependent in dependents:
                    self.invalidate_workspace(dependent, cascade=False)
    
    def invalidate_root_index(self) -> None:
        """Invalidate the root index cache."""
        with self.lock:
            self.root_index_cache.clear()
            # Clear dependency caches as they depend on root index
            self.dependency_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "workspace_mapping": self.workspace_mapping_cache.get_stats(),
            "dependency": self.dependency_cache.get_stats(),
            "filesystem": self.filesystem_cache.get_stats(),
            "workspace_index": self.workspace_index_cache.get_stats(),
            "root_index": self.root_index_cache.get_stats(),
            "total_memory_mb": sum([
                self.workspace_mapping_cache.current_size_bytes,
                self.dependency_cache.current_size_bytes,
                self.filesystem_cache.current_size_bytes,
                self.workspace_index_cache.current_size_bytes,
                self.root_index_cache.current_size_bytes
            ]) / (1024 * 1024)
        }
    
    def _get_workspace_mapping(self, workspace_name: str) -> Optional[Dict]:
        """Get workspace mapping with caching."""
        cache_key = f"mapping:{workspace_name}"
        
        # Check cache first
        cached_mapping = self.workspace_mapping_cache.get(cache_key)
        if cached_mapping is not None:
            return cached_mapping
        
        # Load from root index
        root_index = self.load_root_index()
        workspace_registry = root_index.get("monorepo", {}).get("workspace_registry", {})
        workspace_info = workspace_registry.get(workspace_name)
        
        if workspace_info:
            self.workspace_mapping_cache.put(cache_key, workspace_info)
        
        return workspace_info
    
    def _is_file_stale(self, file_path: Path) -> bool:
        """Check if a file has been modified since last cache."""
        try:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = self.file_mtimes.get(str(file_path))
            
            if cached_mtime is None:
                return True
            
            return current_mtime > cached_mtime
        except (OSError, IOError):
            return True
    
    def _update_file_mtime(self, file_path: Path) -> None:
        """Update the cached modification time for a file."""
        try:
            self.file_mtimes[str(file_path)] = file_path.stat().st_mtime
        except (OSError, IOError):
            pass


# Global loader instance for module-level functions
_global_loader = None
_global_loader_lock = threading.Lock()


def get_global_loader(root_path: Union[str, Path]) -> LazyIndexLoader:
    """Get or create the global loader instance."""
    global _global_loader
    
    with _global_loader_lock:
        if _global_loader is None or _global_loader.root_path != Path(root_path).resolve():
            _global_loader = LazyIndexLoader(root_path)
        return _global_loader


def load_root_index(root_path: Union[str, Path] = ".") -> Dict:
    """Load root index using global loader."""
    loader = get_global_loader(root_path)
    return loader.load_root_index()


def load_workspace_index(workspace_name: str, root_path: Union[str, Path] = ".") -> Optional[Dict]:
    """Load workspace index using global loader."""
    loader = get_global_loader(root_path)
    return loader.load_workspace_index(workspace_name)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test lazy index loading")
    parser.add_argument("root_path", default=".", nargs="?",
                       help="Path to project root")
    parser.add_argument("--workspace", "-w", help="Load specific workspace")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    
    args = parser.parse_args()
    
    loader = LazyIndexLoader(args.root_path)
    
    if args.workspace:
        print(f"Loading workspace: {args.workspace}")
        start_time = time.time()
        workspace_index = loader.load_workspace_index(args.workspace)
        load_time = time.time() - start_time
        
        if workspace_index:
            print(f"✅ Loaded in {load_time:.3f}s")
            print(f"📄 Files: {workspace_index.get('stats', {}).get('total_files', 'unknown')}")
        else:
            print("❌ Workspace not found")
    else:
        print("Loading root index...")
        start_time = time.time()
        root_index = loader.load_root_index()
        load_time = time.time() - start_time
        
        print(f"✅ Loaded in {load_time:.3f}s")
        print(f"📊 Type: {root_index.get('index_type', 'unknown')}")
        
        if root_index.get('monorepo', {}).get('enabled'):
            stats = root_index.get('global_stats', {})
            print(f"📦 Workspaces: {stats.get('total_workspaces', 0)}")
    
    if args.stats:
        print("\nCache Statistics:")
        stats = loader.get_cache_stats()
        for cache_name, cache_stats in stats.items():
            if cache_name != "total_memory_mb":
                print(f"  {cache_name}: {cache_stats['entries']} entries, "
                      f"{cache_stats['hit_rate']:.2%} hit rate, "
                      f"{cache_stats['size_mb']:.1f}MB")
        print(f"  Total memory: {stats['total_memory_mb']:.1f}MB")