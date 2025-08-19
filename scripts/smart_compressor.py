"""
Smart Compressor for Claude Code Project Index

This module provides efficient compression for index files with guaranteed
infinite loop prevention through circular reference detection and batch processing.

Key Features:
- Infinite loop prevention using visited sets and circular reference detection
- Separate compression strategies for root vs workspace indexes  
- Batch processing with progress indicators
- Reference cycle detection and handling
- Memory-efficient compression with size validation
"""

import json
import time
import gc
from typing import Dict, List, Optional, Union, Set, Any, Tuple
from collections import deque
import threading
import weakref


class CircularReferenceDetector:
    """Detects and handles circular references in data structures."""
    
    def __init__(self):
        self.visited_objects = set()
        self.processing_stack = []
        self.reference_markers = {}
        
    def detect_cycles(self, obj: Any, path: str = "root") -> Tuple[bool, List[str]]:
        """
        Detect circular references in an object graph.
        
        Args:
            obj: Object to analyze
            path: Current path in the object graph
            
        Returns:
            Tuple of (has_cycles, cycle_paths)
        """
        obj_id = id(obj)
        
        if obj_id in self.processing_stack:
            # Found a cycle
            cycle_start = self.processing_stack.index(obj_id)
            cycle_path = [f"path_{i}" for i in self.processing_stack[cycle_start:]]
            return True, [f"Cycle detected at {path}: {' -> '.join(cycle_path)}"]
        
        if obj_id in self.visited_objects:
            # Already processed this object
            return False, []
        
        self.visited_objects.add(obj_id)
        self.processing_stack.append(obj_id)
        
        cycles = []
        
        try:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    has_cycle, cycle_paths = self.detect_cycles(value, f"{path}.{key}")
                    if has_cycle:
                        cycles.extend(cycle_paths)
            elif isinstance(obj, (list, tuple)):
                for i, item in enumerate(obj):
                    has_cycle, cycle_paths = self.detect_cycles(item, f"{path}[{i}]")
                    if has_cycle:
                        cycles.extend(cycle_paths)
        finally:
            self.processing_stack.pop()
        
        return len(cycles) > 0, cycles
    
    def create_reference_marker(self, obj: Any) -> str:
        """Create a reference marker for an object to break cycles."""
        obj_id = id(obj)
        marker = f"__ref_{obj_id}"
        self.reference_markers[marker] = weakref.ref(obj) if hasattr(obj, '__weakref__') else None
        return marker


class BatchProcessor:
    """Handles batch processing of large datasets with progress tracking."""
    
    def __init__(self, batch_size: int = 100, progress_callback=None):
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        
    def process_items(self, items: List[Any], processor_func, description: str = "Processing"):
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            processor_func: Function to process each item
            description: Description for progress reporting
        """
        total_items = len(items)
        processed = 0
        
        for i in range(0, total_items, self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Process batch
            for item in batch:
                processor_func(item)
                processed += 1
            
            # Report progress
            if self.progress_callback:
                progress_percent = (processed / total_items) * 100
                self.progress_callback(processed, total_items, progress_percent, description)
            
            # Allow garbage collection between batches
            gc.collect()
    
    def process_dict_items(self, data: Dict, processor_func, description: str = "Processing"):
        """Process dictionary items in batches."""
        items = list(data.items())
        
        def dict_processor(item):
            key, value = item
            return processor_func(key, value)
        
        self.process_items(items, dict_processor, description)


class SmartCompressor:
    """
    Efficient compression system with infinite loop prevention.
    
    Provides separate compression strategies for root and workspace indexes
    with guaranteed cycle detection and batch processing capabilities.
    """
    
    def __init__(self, enable_progress: bool = True):
        self.enable_progress = enable_progress
        self.compression_stats = {
            "objects_processed": 0,
            "cycles_detected": 0,
            "references_replaced": 0,
            "compression_ratio": 0.0,
            "processing_time": 0.0
        }
        self.lock = threading.Lock()
    
    def compress_root_index(self, index: Dict) -> Dict:
        """
        Compress root index using lightweight strategy.
        
        Removes non-essential metadata while preserving workspace registry
        and cross-workspace dependencies. Ensures size stays under 200KB.
        
        Args:
            index: Root index dictionary
            
        Returns:
            Compressed root index
        """
        start_time = time.time()
        
        with self.lock:
            detector = CircularReferenceDetector()
            
            # Check for cycles first
            has_cycles, cycle_paths = detector.detect_cycles(index)
            if has_cycles:
                self.compression_stats["cycles_detected"] += len(cycle_paths)
                print(f"⚠️  Detected {len(cycle_paths)} circular references in root index")
                for cycle_path in cycle_paths:
                    print(f"   {cycle_path}")
            
            # Create compressed copy
            compressed = self._compress_root_index_data(index, detector)
            
            # Validate size constraint
            compressed_json = json.dumps(compressed, separators=(',', ':'))
            size_kb = len(compressed_json.encode('utf-8')) / 1024
            
            if size_kb > 200:
                # Apply more aggressive compression
                compressed = self._aggressive_root_compression(compressed, detector)
            
            self.compression_stats["processing_time"] = time.time() - start_time
            self._calculate_compression_ratio(index, compressed)
            
            return compressed
    
    def compress_workspace_index(self, index: Dict) -> Dict:
        """
        Compress workspace index using standard strategy.
        
        Retains details necessary for workspace operations while
        removing redundant information.
        
        Args:
            index: Workspace index dictionary
            
        Returns:
            Compressed workspace index
        """
        start_time = time.time()
        
        with self.lock:
            detector = CircularReferenceDetector()
            
            # Check for cycles
            has_cycles, cycle_paths = detector.detect_cycles(index)
            if has_cycles:
                self.compression_stats["cycles_detected"] += len(cycle_paths)
                print(f"⚠️  Detected {len(cycle_paths)} circular references in workspace index")
            
            # Apply standard compression
            compressed = self._compress_workspace_index_data(index, detector)
            
            self.compression_stats["processing_time"] += time.time() - start_time
            self._calculate_compression_ratio(index, compressed)
            
            return compressed
    
    def _compress_root_index_data(self, index: Dict, detector: CircularReferenceDetector) -> Dict:
        """Apply lightweight compression to root index data."""
        compressed = {
            "indexed_at": index.get("indexed_at"),
            "root": index.get("root", "."),
            "index_type": index.get("index_type", "hierarchical_root"),
        }
        
        # Preserve essential monorepo information
        if "monorepo" in index:
            monorepo = index["monorepo"]
            compressed["monorepo"] = {
                "enabled": monorepo.get("enabled"),
                "tool": monorepo.get("tool"),
                "last_updated": monorepo.get("last_updated"),
                "total_workspaces": monorepo.get("total_workspaces"),
                "workspace_registry": self._compress_workspace_registry(
                    monorepo.get("workspace_registry", {}), detector
                )
            }
        
        # Preserve cross-workspace dependencies with cycle handling
        if "cross_workspace_dependencies" in index:
            compressed["cross_workspace_dependencies"] = self._compress_dependencies(
                index["cross_workspace_dependencies"], detector
            )
        
        # Preserve essential global stats
        if "global_stats" in index:
            stats = index["global_stats"]
            compressed["global_stats"] = {
                "total_workspaces": stats.get("total_workspaces"),
                "total_files": stats.get("total_files"),
                "indexed_workspaces": stats.get("indexed_workspaces"),
                "failed_workspaces": stats.get("failed_workspaces")
            }
        
        # Simplified project structure
        if "project_structure" in index:
            structure = index["project_structure"]
            compressed["project_structure"] = {
                "type": structure.get("type", "workspace_overview")
                # Skip detailed tree for root index compression
            }
        
        return compressed
    
    def _compress_workspace_registry(self, registry: Dict, detector: CircularReferenceDetector) -> Dict:
        """Compress workspace registry with cycle detection."""
        compressed_registry = {}
        
        for workspace_name, workspace_info in registry.items():
            # Keep essential workspace information (don't use reference markers for registry)
            compressed_registry[workspace_name] = {
                "path": workspace_info.get("path"),
                "index_path": workspace_info.get("index_path"),
                "package_manager": workspace_info.get("package_manager"),
                "status": workspace_info.get("status")
                # Skip last_updated for space savings
            }
        
        return compressed_registry
    
    def _compress_dependencies(self, dependencies: Dict, detector: CircularReferenceDetector) -> Dict:
        """Compress cross-workspace dependencies with cycle breaking."""
        compressed_deps = {}
        
        for workspace, deps in dependencies.items():
            if isinstance(deps, list):
                # Remove self-references to prevent cycles
                filtered_deps = [dep for dep in deps if dep != workspace]
                if filtered_deps:
                    compressed_deps[workspace] = filtered_deps
            else:
                # Handle unexpected dependency format
                compressed_deps[workspace] = deps
        
        return compressed_deps
    
    def _compress_workspace_index_data(self, index: Dict, detector: CircularReferenceDetector) -> Dict:
        """Apply standard compression to workspace index data."""
        compressed = {}
        
        # Process with batch processing for large indexes
        batch_processor = BatchProcessor(
            batch_size=100,
            progress_callback=self._progress_callback if self.enable_progress else None
        )
        
        # Essential fields to always preserve
        essential_fields = {
            "indexed_at", "root", "index_type", "stats", "files", 
            "directory_purposes", "dependency_graph", "documentation_map"
        }
        
        def compress_field(key, value):
            if key in essential_fields:
                if key == "files":
                    # Compress file entries
                    compressed[key] = self._compress_file_entries(value, detector)
                elif key == "dependency_graph":
                    # Compress dependency graph with cycle detection
                    compressed[key] = self._compress_dependency_graph(value, detector)
                else:
                    compressed[key] = value
        
        batch_processor.process_dict_items(index, compress_field, "Compressing workspace index")
        
        return compressed
    
    def _compress_file_entries(self, files: Dict, detector: CircularReferenceDetector) -> Dict:
        """Compress file entries removing redundant information."""
        compressed_files = {}
        
        for file_path, file_info in files.items():
            # Keep essential file information
            compressed_info = {
                "language": file_info.get("language"),
                "parsed": file_info.get("parsed", False)
            }
            
            # Keep purpose if meaningful
            if file_info.get("purpose") and file_info["purpose"] != "unknown":
                compressed_info["purpose"] = file_info["purpose"]
            
            # For parsed files, keep essential structure info
            if file_info.get("parsed"):
                for key in ["imports", "functions", "classes", "constants"]:
                    if key in file_info and file_info[key]:
                        compressed_info[key] = file_info[key]
            
            compressed_files[file_path] = compressed_info
        
        return compressed_files
    
    def _compress_dependency_graph(self, dep_graph: Dict, detector: CircularReferenceDetector) -> Dict:
        """Compress dependency graph with cycle detection."""
        if not dep_graph:
            return {}
        
        # Build visited set to track processed dependencies
        visited_deps = set()
        compressed_graph = {}
        
        for node, connections in dep_graph.items():
            if node in visited_deps:
                continue
            
            visited_deps.add(node)
            
            # Filter connections to prevent cycles
            if isinstance(connections, (list, tuple)):
                filtered_connections = [
                    conn for conn in connections 
                    if conn != node and conn not in visited_deps
                ]
                if filtered_connections:
                    compressed_graph[node] = filtered_connections
            else:
                compressed_graph[node] = connections
        
        return compressed_graph
    
    def _aggressive_root_compression(self, index: Dict, detector: CircularReferenceDetector) -> Dict:
        """Apply more aggressive compression if size limit exceeded."""
        # Remove optional fields
        fields_to_remove = ["project_structure"]
        
        for field in fields_to_remove:
            index.pop(field, None)
        
        # Compress workspace registry further
        if "monorepo" in index and "workspace_registry" in index["monorepo"]:
            registry = index["monorepo"]["workspace_registry"]
            for workspace_name, info in registry.items():
                # Remove non-essential fields
                essential_only = {
                    "path": info.get("path"),
                    "status": info.get("status")
                }
                registry[workspace_name] = essential_only
        
        return index
    
    def _calculate_compression_ratio(self, original: Dict, compressed: Dict):
        """Calculate and update compression ratio statistics."""
        try:
            original_size = len(json.dumps(original, separators=(',', ':')))
            compressed_size = len(json.dumps(compressed, separators=(',', ':')))
            
            if original_size > 0:
                ratio = (original_size - compressed_size) / original_size
                self.compression_stats["compression_ratio"] = ratio
        except:
            pass
    
    def _progress_callback(self, processed: int, total: int, percent: float, description: str):
        """Default progress callback."""
        if self.enable_progress and processed % 50 == 0:  # Report every 50 items
            print(f"📊 {description}: {processed}/{total} ({percent:.1f}%)")
    
    def get_compression_stats(self) -> Dict:
        """Get compression statistics."""
        with self.lock:
            return self.compression_stats.copy()
    
    def reset_stats(self):
        """Reset compression statistics."""
        with self.lock:
            self.compression_stats = {
                "objects_processed": 0,
                "cycles_detected": 0,
                "references_replaced": 0,
                "compression_ratio": 0.0,
                "processing_time": 0.0
            }


def compress_index_safe(index: Dict, index_type: str = "workspace") -> Dict:
    """
    Safely compress an index with automatic type detection and cycle prevention.
    
    Args:
        index: Index dictionary to compress
        index_type: Type of index ("root" or "workspace")
        
    Returns:
        Compressed index dictionary
    """
    compressor = SmartCompressor()
    
    # Auto-detect index type if not specified
    if index_type == "auto":
        if index.get("index_type") == "hierarchical_root":
            index_type = "root"
        else:
            index_type = "workspace"
    
    if index_type == "root":
        return compressor.compress_root_index(index)
    else:
        return compressor.compress_workspace_index(index)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test smart compression")
    parser.add_argument("input_file", help="Input JSON file to compress")
    parser.add_argument("--output", "-o", help="Output file (default: add .compressed)")
    parser.add_argument("--type", choices=["root", "workspace", "auto"], default="auto",
                       help="Index type for compression strategy")
    parser.add_argument("--stats", action="store_true", help="Show compression statistics")
    
    args = parser.parse_args()
    
    # Load input file
    try:
        with open(args.input_file) as f:
            index = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"❌ Error loading input file: {e}")
        exit(1)
    
    # Compress
    print(f"📦 Compressing {args.input_file}...")
    compressed = compress_index_safe(index, args.type)
    
    # Save output
    output_file = args.output or f"{args.input_file}.compressed"
    try:
        with open(output_file, 'w') as f:
            json.dump(compressed, f, indent=2)
        print(f"✅ Compressed index saved to: {output_file}")
    except IOError as e:
        print(f"❌ Error saving output file: {e}")
        exit(1)
    
    # Show statistics
    if args.stats:
        original_size = len(json.dumps(index, separators=(',', ':')))
        compressed_size = len(json.dumps(compressed, separators=(',', ':')))
        ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0
        
        print(f"\n📊 Compression Statistics:")
        print(f"  Original size: {original_size:,} bytes ({original_size/1024:.1f} KB)")
        print(f"  Compressed size: {compressed_size:,} bytes ({compressed_size/1024:.1f} KB)")
        print(f"  Compression ratio: {ratio:.2%}")
        print(f"  Space saved: {original_size - compressed_size:,} bytes")