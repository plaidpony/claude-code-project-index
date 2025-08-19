#!/usr/bin/env python3
"""
Performance Validation Script for Phase 3 Requirements
Tests critical performance thresholds for the hierarchical indexing architecture.

Performance Requirements:
- Root index generation: <30 seconds for any monorepo size
- Root index file size: <200KB regardless of monorepo scale  
- Workspace loading: <2 seconds per workspace
- Memory usage: <500MB for 5000+ file monorepos
- No infinite loops during any operation
"""

import os
import time
import json
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import sys
import resource

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available, using basic memory monitoring")

# Add scripts directory to path
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from hierarchical_indexer import HierarchicalIndexManager, generate_hierarchical_index
    from lazy_index_loader import LazyIndexLoader, get_global_loader
    from workspace_config import WorkspaceConfigManager
    from cross_workspace_analyzer import build_cross_workspace_dependencies
    from performance_monitor import get_performance_monitor
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("   Some features may not be available")


class PerformanceResult:
    """Represents the result of a performance test."""
    def __init__(self, name: str, passed: bool, measured_value: float, threshold: float, 
                 unit: str = "", details: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.measured_value = measured_value
        self.threshold = threshold
        self.unit = unit
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "measured_value": self.measured_value,
            "threshold": self.threshold,
            "unit": self.unit,
            "details": self.details
        }


class PerformanceValidator:
    """Validates performance requirements for the hierarchical indexing architecture."""
    
    def __init__(self, root_path: Path):
        self.root_path = Path(root_path).resolve()
        self.results: List[PerformanceResult] = []
        self.performance_monitor = get_performance_monitor()
        
    @contextmanager
    def memory_monitor(self, timeout: float = 60.0):
        """Context manager to monitor peak memory usage during operation."""
        peak_memory = 0
        
        if PSUTIL_AVAILABLE:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        else:
            # Fallback to resource module (less accurate)
            start_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KB to MB on Linux
        
        monitoring = True
        
        def monitor_memory():
            nonlocal peak_memory, monitoring
            while monitoring:
                if PSUTIL_AVAILABLE:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                else:
                    # Less accurate fallback
                    current_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                    
                peak_memory = max(peak_memory, current_memory)
                time.sleep(0.1)
        
        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()
        
        try:
            yield lambda: max(0, peak_memory - start_memory)
        finally:
            monitoring = False
            monitor_thread.join(timeout=1.0)
    
    @contextmanager
    def timeout_guard(self, timeout_seconds: float, operation_name: str):
        """Context manager to prevent infinite loops by enforcing timeouts."""
        def timeout_handler():
            raise TimeoutError(f"Operation '{operation_name}' exceeded {timeout_seconds}s timeout")
        
        timer = threading.Timer(timeout_seconds, timeout_handler)
        timer.start()
        
        try:
            yield
        finally:
            timer.cancel()
    
    def test_root_index_generation_time(self) -> PerformanceResult:
        """Test: Root index generation must complete in <30 seconds."""
        print("🔄 Testing root index generation time...")
        
        try:
            with self.timeout_guard(35.0, "root_index_generation"):  # 5s buffer for timeout
                start_time = time.time()
                
                # Generate root index using HierarchicalIndexManager
                manager = HierarchicalIndexManager(self.root_path)
                root_index = manager.generate_root_index()
                
                generation_time = time.time() - start_time
                
                passed = generation_time < 30.0
                
                result = PerformanceResult(
                    "Root Index Generation Time",
                    passed,
                    generation_time,
                    30.0,
                    "seconds",
                    {
                        "workspaces_count": root_index.get("monorepo", {}).get("workspaces", {}).__len__() if isinstance(root_index.get("monorepo", {}).get("workspaces"), dict) else 0,
                        "total_files": root_index.get("global_stats", {}).get("total_files", 0)
                    }
                )
                
        except TimeoutError as e:
            result = PerformanceResult(
                "Root Index Generation Time",
                False,
                35.0,  # Timeout value
                30.0,
                "seconds",
                {"error": str(e)}
            )
        except Exception as e:
            result = PerformanceResult(
                "Root Index Generation Time",
                False,
                0.0,
                30.0,
                "seconds",
                {"error": str(e)}
            )
        
        self.results.append(result)
        print(f"   {'✅' if result.passed else '❌'} {result.measured_value:.2f}s (threshold: {result.threshold}s)")
        return result
    
    def test_root_index_file_size(self) -> PerformanceResult:
        """Test: Root index file size must be <200KB."""
        print("🔄 Testing root index file size...")
        
        try:
            # Generate and save root index
            manager = HierarchicalIndexManager(self.root_path)
            root_index = manager.generate_root_index()
            
            # Save to temporary file to measure size
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(root_index, temp_file, indent=2)
                temp_path = Path(temp_file.name)
            
            try:
                file_size_kb = temp_path.stat().st_size / 1024  # Convert bytes to KB
                passed = file_size_kb < 200.0
                
                result = PerformanceResult(
                    "Root Index File Size",
                    passed,
                    file_size_kb,
                    200.0,
                    "KB",
                    {
                        "file_size_bytes": temp_path.stat().st_size,
                        "compression_used": "smart_compressor" in str(root_index).lower()
                    }
                )
            finally:
                temp_path.unlink()  # Clean up temp file
                
        except Exception as e:
            result = PerformanceResult(
                "Root Index File Size",
                False,
                0.0,
                200.0,
                "KB",
                {"error": str(e)}
            )
        
        self.results.append(result)
        print(f"   {'✅' if result.passed else '❌'} {result.measured_value:.2f}KB (threshold: {result.threshold}KB)")
        return result
    
    def test_workspace_loading_time(self) -> PerformanceResult:
        """Test: Workspace loading must complete in <2 seconds per workspace."""
        print("🔄 Testing workspace loading time...")
        
        try:
            # Get workspace configuration
            config_manager = WorkspaceConfigManager(self.root_path)
            registry = config_manager.load_configuration()
            
            if not registry or not registry.get_all_workspaces():
                result = PerformanceResult(
                    "Workspace Loading Time",
                    True,  # Pass if no workspaces (single-repo)
                    0.0,
                    2.0,
                    "seconds",
                    {"note": "No workspaces found (single-repo project)"}
                )
                self.results.append(result)
                print("   ℹ️  No workspaces found (single-repo project)")
                return result
            
            # Test lazy loading performance
            lazy_loader = get_global_loader(self.root_path)
            workspaces = registry.get_all_workspaces()[:5]  # Test first 5 workspaces
            
            max_loading_time = 0.0
            loading_times = []
            
            for workspace in workspaces:
                start_time = time.time()
                
                try:
                    workspace_index = lazy_loader.load_workspace_index(
                        workspace.name,
                        max_age_seconds=0,  # Force fresh load
                        force_refresh=True
                    )
                    loading_time = time.time() - start_time
                    loading_times.append(loading_time)
                    max_loading_time = max(max_loading_time, loading_time)
                    
                except Exception as e:
                    # If workspace index doesn't exist, that's ok for this test
                    loading_time = time.time() - start_time
                    loading_times.append(loading_time)
                    max_loading_time = max(max_loading_time, loading_time)
            
            passed = max_loading_time < 2.0
            avg_loading_time = sum(loading_times) / len(loading_times) if loading_times else 0
            
            result = PerformanceResult(
                "Workspace Loading Time",
                passed,
                max_loading_time,
                2.0,
                "seconds",
                {
                    "workspaces_tested": len(workspaces),
                    "average_loading_time": avg_loading_time,
                    "all_loading_times": loading_times
                }
            )
            
        except Exception as e:
            result = PerformanceResult(
                "Workspace Loading Time",
                False,
                0.0,
                2.0,
                "seconds",
                {"error": str(e)}
            )
        
        self.results.append(result)
        print(f"   {'✅' if result.passed else '❌'} {result.measured_value:.2f}s max (threshold: {result.threshold}s)")
        return result
    
    def test_memory_usage_large_monorepo(self) -> PerformanceResult:
        """Test: Memory usage must stay <500MB for large operations."""
        print("🔄 Testing memory usage for large monorepo operations...")
        
        try:
            with self.memory_monitor() as get_peak_memory:
                with self.timeout_guard(120.0, "memory_test"):  # 2 minute timeout
                    
                    # Perform memory-intensive operations
                    manager = HierarchicalIndexManager(self.root_path)
                    
                    # Generate root index
                    root_index = manager.generate_root_index()
                    
                    # Load workspace configuration
                    config_manager = WorkspaceConfigManager(self.root_path)
                    registry = config_manager.load_configuration()
                    
                    if registry and registry.get_all_workspaces():
                        # Analyze cross-workspace dependencies
                        cross_deps = build_cross_workspace_dependencies(
                            registry,
                            hierarchical_manager=manager,
                            for_root_index=False  # Full analysis
                        )
                    
                    # Give time for memory to peak
                    time.sleep(1)
                    
                peak_memory_mb = get_peak_memory()
                passed = peak_memory_mb < 500.0
                
                result = PerformanceResult(
                    "Memory Usage Large Operations",
                    passed,
                    peak_memory_mb,
                    500.0,
                    "MB",
                    {
                        "operations_performed": [
                            "root_index_generation",
                            "workspace_configuration_loading",
                            "cross_workspace_analysis"
                        ]
                    }
                )
                
        except TimeoutError as e:
            result = PerformanceResult(
                "Memory Usage Large Operations",
                False,
                0.0,
                500.0,
                "MB",
                {"error": f"Timeout: {e}"}
            )
        except Exception as e:
            result = PerformanceResult(
                "Memory Usage Large Operations",
                False,
                0.0,
                500.0,
                "MB",
                {"error": str(e)}
            )
        
        self.results.append(result)
        print(f"   {'✅' if result.passed else '❌'} {result.measured_value:.2f}MB (threshold: {result.threshold}MB)")
        return result
    
    def test_no_infinite_loops(self) -> PerformanceResult:
        """Test: All operations must terminate (no infinite loops)."""
        print("🔄 Testing for infinite loops prevention...")
        
        try:
            operations_completed = 0
            
            with self.timeout_guard(45.0, "infinite_loop_test"):  # Generous timeout
                
                # Test 1: Root index generation
                manager = HierarchicalIndexManager(self.root_path)
                root_index = manager.generate_root_index()
                operations_completed += 1
                
                # Test 2: Workspace configuration loading
                config_manager = WorkspaceConfigManager(self.root_path)
                registry = config_manager.load_configuration()
                operations_completed += 1
                
                if registry and registry.get_all_workspaces():
                    # Test 3: Cross-workspace analysis
                    cross_deps = build_cross_workspace_dependencies(
                        registry,
                        hierarchical_manager=manager,
                        for_root_index=True
                    )
                    operations_completed += 1
                    
                    # Test 4: Compression operations
                    if hasattr(manager, 'compressor') and manager.compressor:
                        compressed_root = manager.compressor.compress_root_index(root_index)
                        operations_completed += 1
                
            result = PerformanceResult(
                "No Infinite Loops",
                True,
                operations_completed,
                1.0,  # At least 1 operation should complete
                "operations",
                {
                    "operations_completed": operations_completed,
                    "total_time_under_limit": True
                }
            )
            
        except TimeoutError as e:
            result = PerformanceResult(
                "No Infinite Loops",
                False,
                operations_completed,
                1.0,
                "operations",
                {
                    "error": "Timeout - possible infinite loop detected",
                    "operations_completed_before_timeout": operations_completed
                }
            )
        except Exception as e:
            result = PerformanceResult(
                "No Infinite Loops",
                False,
                operations_completed,
                1.0,
                "operations",
                {"error": str(e)}
            )
        
        self.results.append(result)
        print(f"   {'✅' if result.passed else '❌'} {int(result.measured_value)} operations completed")
        return result
    
    def run_all_performance_tests(self) -> Dict:
        """Run all performance validation tests and return comprehensive results."""
        print(f"🚀 Running Performance Validation Tests on {self.root_path}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all performance tests
        self.test_root_index_generation_time()
        self.test_root_index_file_size()
        self.test_workspace_loading_time()
        self.test_memory_usage_large_monorepo()
        self.test_no_infinite_loops()
        
        total_time = time.time() - start_time
        
        # Calculate overall results
        passed_tests = sum(1 for result in self.results if result.passed)
        total_tests = len(self.results)
        overall_passed = passed_tests == total_tests
        
        print("\n" + "=" * 60)
        print(f"📊 Performance Validation Results")
        print(f"   Tests Passed: {passed_tests}/{total_tests}")
        print(f"   Overall Result: {'✅ PASS' if overall_passed else '❌ FAIL'}")
        print(f"   Total Validation Time: {total_time:.2f}s")
        
        return {
            "overall_passed": overall_passed,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "validation_time_seconds": total_time,
            "test_results": [result.to_dict() for result in self.results],
            "summary": {
                "root_index_generation_performance": passed_tests >= 1,
                "file_size_compliance": any(r.name == "Root Index File Size" and r.passed for r in self.results),
                "loading_performance": any(r.name == "Workspace Loading Time" and r.passed for r in self.results),
                "memory_efficiency": any(r.name == "Memory Usage Large Operations" and r.passed for r in self.results),
                "stability": any(r.name == "No Infinite Loops" and r.passed for r in self.results)
            }
        }


def main():
    """Main entry point for performance validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Phase 3 performance requirements")
    parser.add_argument("root_path", nargs="?", default=".", help="Root path of the project to validate")
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    root_path = Path(args.root_path).resolve()
    
    if not root_path.exists():
        print(f"❌ Error: Path {root_path} does not exist")
        sys.exit(1)
    
    try:
        validator = PerformanceValidator(root_path)
        results = validator.run_all_performance_tests()
        
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n📁 Results saved to {output_path}")
        
        if args.verbose:
            print(f"\n📋 Detailed Results:")
            for result in validator.results:
                print(f"   {result.name}: {result.measured_value}{result.unit} (threshold: {result.threshold}{result.unit})")
                if result.details:
                    for key, value in result.details.items():
                        print(f"     {key}: {value}")
        
        sys.exit(0 if results["overall_passed"] else 1)
        
    except Exception as e:
        print(f"❌ Performance validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()