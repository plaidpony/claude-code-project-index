#!/usr/bin/env python3
"""
Performance Monitoring and Optimization for Workspace-Aware Hooks
Tracks response times, cache performance, and resource usage.

Features:
- Hook performance tracking and alerting
- Workspace cache optimization and monitoring
- Performance metrics collection and reporting
- Resource usage monitoring
- Performance regression detection
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import os
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Global performance tracking
_performance_data = {
    'hook_timings': deque(maxlen=1000),  # Keep last 1000 hook executions
    'cache_stats': defaultdict(int),
    'resource_usage': deque(maxlen=100),
    'error_counts': defaultdict(int)
}
_lock = threading.Lock()


@dataclass
class HookTiming:
    """Track timing data for hook executions."""
    hook_name: str
    start_time: float
    end_time: float
    duration: float
    workspace: Optional[str]
    file_path: Optional[str]
    operation: str
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CacheStats:
    """Track cache performance statistics."""
    cache_name: str
    hits: int
    misses: int
    evictions: int
    size: int
    max_size: int
    hit_rate: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ResourceUsage:
    """Track system resource usage during operations."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    process_id: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class PerformanceMonitor:
    """Central performance monitoring and optimization system."""
    
    def __init__(self):
        self.process = psutil.Process() if HAS_PSUTIL else None
        self.performance_log_path = None
        self.thresholds = {
            'hook_duration_warning': 2.0,  # seconds
            'hook_duration_critical': 5.0,  # seconds
            'memory_usage_warning': 100,    # MB
            'cpu_usage_warning': 50,        # percent
        }
    
    def set_performance_log_path(self, project_root: Path):
        """Set the path for performance logging."""
        self.performance_log_path = project_root / '.performance' / 'hook_performance.jsonl'
        self.performance_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def start_hook_timing(self, hook_name: str, operation: str, workspace: Optional[str] = None, file_path: Optional[str] = None) -> str:
        """Start timing a hook operation."""
        timing_id = f"{hook_name}_{int(time.time() * 1000000)}"
        
        with _lock:
            # Record resource usage at start
            self._record_resource_usage()
            
            # Store timing start in thread-local or global storage
            _performance_data[f'timing_start_{timing_id}'] = {
                'hook_name': hook_name,
                'operation': operation,
                'workspace': workspace,
                'file_path': file_path,
                'start_time': time.time()
            }
        
        return timing_id
    
    def end_hook_timing(self, timing_id: str, success: bool = True, error_message: Optional[str] = None):
        """End timing a hook operation and record performance data."""
        end_time = time.time()
        
        with _lock:
            start_data = _performance_data.get(f'timing_start_{timing_id}')
            if not start_data:
                return
            
            # Calculate duration
            duration = end_time - start_data['start_time']
            
            # Create timing record
            timing = HookTiming(
                hook_name=start_data['hook_name'],
                start_time=start_data['start_time'],
                end_time=end_time,
                duration=duration,
                workspace=start_data['workspace'],
                file_path=start_data['file_path'],
                operation=start_data['operation'],
                success=success,
                error_message=error_message
            )
            
            # Store in performance data
            _performance_data['hook_timings'].append(timing)
            
            # Record resource usage at end
            self._record_resource_usage()
            
            # Check performance thresholds
            self._check_performance_thresholds(timing)
            
            # Log to file if configured
            if self.performance_log_path:
                self._log_performance_data(timing)
            
            # Clean up start data
            del _performance_data[f'timing_start_{timing_id}']
    
    def record_cache_hit(self, cache_name: str):
        """Record a cache hit."""
        with _lock:
            _performance_data['cache_stats'][f'{cache_name}_hits'] += 1
    
    def record_cache_miss(self, cache_name: str):
        """Record a cache miss."""
        with _lock:
            _performance_data['cache_stats'][f'{cache_name}_misses'] += 1
    
    def record_cache_eviction(self, cache_name: str):
        """Record a cache eviction."""
        with _lock:
            _performance_data['cache_stats'][f'{cache_name}_evictions'] += 1
    
    def record_error(self, error_type: str):
        """Record an error occurrence."""
        with _lock:
            _performance_data['error_counts'][error_type] += 1
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """Get performance summary for the last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        
        with _lock:
            # Filter recent timings
            recent_timings = [
                timing for timing in _performance_data['hook_timings']
                if timing.start_time > cutoff_time
            ]
            
            if not recent_timings:
                return {'message': 'No performance data available'}
            
            # Calculate statistics
            durations = [t.duration for t in recent_timings]
            
            summary = {
                'time_period_hours': hours,
                'total_hook_executions': len(recent_timings),
                'successful_executions': sum(1 for t in recent_timings if t.success),
                'failed_executions': sum(1 for t in recent_timings if not t.success),
                'performance_metrics': {
                    'avg_duration': sum(durations) / len(durations) if durations else 0,
                    'min_duration': min(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'p95_duration': self._percentile(durations, 0.95) if durations else 0,
                    'p99_duration': self._percentile(durations, 0.99) if durations else 0,
                },
                'performance_violations': {
                    'warning_threshold_violations': sum(
                        1 for d in durations 
                        if d > self.thresholds['hook_duration_warning']
                    ),
                    'critical_threshold_violations': sum(
                        1 for d in durations 
                        if d > self.thresholds['hook_duration_critical']
                    )
                },
                'hook_breakdown': self._get_hook_breakdown(recent_timings),
                'workspace_breakdown': self._get_workspace_breakdown(recent_timings),
                'cache_statistics': self._get_cache_statistics(),
                'error_statistics': dict(_performance_data['error_counts'])
            }
            
            return summary
    
    def optimize_caches(self, project_root: Path) -> Dict:
        """Analyze and optimize cache configurations."""
        optimizations = []
        
        with _lock:
            cache_stats = _performance_data['cache_stats']
            
            # Analyze workspace cache performance
            workspace_hits = cache_stats.get('workspace_config_hits', 0)
            workspace_misses = cache_stats.get('workspace_config_misses', 0)
            
            if workspace_hits + workspace_misses > 0:
                hit_rate = workspace_hits / (workspace_hits + workspace_misses)
                
                if hit_rate < 0.8:  # Less than 80% hit rate
                    optimizations.append({
                        'cache': 'workspace_config',
                        'issue': 'Low hit rate',
                        'current_hit_rate': hit_rate,
                        'recommendation': 'Consider increasing cache TTL or cache size'
                    })
            
            # Check for excessive evictions
            for key, value in cache_stats.items():
                if key.endswith('_evictions') and value > 10:
                    cache_name = key.replace('_evictions', '')
                    optimizations.append({
                        'cache': cache_name,
                        'issue': 'High eviction rate',
                        'evictions': value,
                        'recommendation': 'Consider increasing cache size'
                    })
        
        return {
            'optimizations_found': len(optimizations),
            'optimizations': optimizations
        }
    
    def _record_resource_usage(self):
        """Record current resource usage."""
        try:
            if self.process:
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                io_counters = self.process.io_counters() if hasattr(self.process, 'io_counters') else None
            else:
                cpu_percent = 0.0
                memory_info = type('MemoryInfo', (), {'rss': 0})()
                io_counters = None
            
            usage = ResourceUsage(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_info.rss / 1024 / 1024,  # Convert to MB
                disk_io_read=io_counters.read_bytes if io_counters else 0,
                disk_io_write=io_counters.write_bytes if io_counters else 0,
                process_id=os.getpid()
            )
            
            _performance_data['resource_usage'].append(usage)
            
        except Exception:
            pass  # Ignore resource monitoring errors
    
    def _check_performance_thresholds(self, timing: HookTiming):
        """Check if performance thresholds are violated."""
        if timing.duration > self.thresholds['hook_duration_critical']:
            print(f"CRITICAL: Hook {timing.hook_name} took {timing.duration:.2f}s (threshold: {self.thresholds['hook_duration_critical']}s)", file=sys.stderr)
        elif timing.duration > self.thresholds['hook_duration_warning']:
            print(f"WARNING: Hook {timing.hook_name} took {timing.duration:.2f}s (threshold: {self.thresholds['hook_duration_warning']}s)", file=sys.stderr)
        
        # Check resource usage
        if _performance_data['resource_usage']:
            latest_usage = _performance_data['resource_usage'][-1]
            
            if latest_usage.memory_mb > self.thresholds['memory_usage_warning']:
                print(f"WARNING: High memory usage: {latest_usage.memory_mb:.1f}MB", file=sys.stderr)
            
            if latest_usage.cpu_percent > self.thresholds['cpu_usage_warning']:
                print(f"WARNING: High CPU usage: {latest_usage.cpu_percent:.1f}%", file=sys.stderr)
    
    def _log_performance_data(self, timing: HookTiming):
        """Log performance data to file."""
        try:
            with open(self.performance_log_path, 'a') as f:
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'timing': timing.to_dict()
                }
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass  # Ignore logging errors
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]
    
    def _get_hook_breakdown(self, timings: List[HookTiming]) -> Dict:
        """Get performance breakdown by hook type."""
        hook_stats = defaultdict(list)
        
        for timing in timings:
            hook_stats[timing.hook_name].append(timing.duration)
        
        breakdown = {}
        for hook_name, durations in hook_stats.items():
            breakdown[hook_name] = {
                'executions': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'p95_duration': self._percentile(durations, 0.95)
            }
        
        return breakdown
    
    def _get_workspace_breakdown(self, timings: List[HookTiming]) -> Dict:
        """Get performance breakdown by workspace."""
        workspace_stats = defaultdict(list)
        
        for timing in timings:
            workspace_key = timing.workspace or 'root'
            workspace_stats[workspace_key].append(timing.duration)
        
        breakdown = {}
        for workspace, durations in workspace_stats.items():
            breakdown[workspace] = {
                'executions': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations)
            }
        
        return breakdown
    
    def _get_cache_statistics(self) -> Dict:
        """Get cache performance statistics."""
        stats = {}
        cache_names = set()
        
        # Extract unique cache names
        for key in _performance_data['cache_stats'].keys():
            if key.endswith(('_hits', '_misses', '_evictions')):
                cache_name = '_'.join(key.split('_')[:-1])
                cache_names.add(cache_name)
        
        # Calculate statistics for each cache
        for cache_name in cache_names:
            hits = _performance_data['cache_stats'].get(f'{cache_name}_hits', 0)
            misses = _performance_data['cache_stats'].get(f'{cache_name}_misses', 0)
            evictions = _performance_data['cache_stats'].get(f'{cache_name}_evictions', 0)
            
            total_requests = hits + misses
            hit_rate = hits / total_requests if total_requests > 0 else 0
            
            stats[cache_name] = {
                'hits': hits,
                'misses': misses,
                'evictions': evictions,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
        
        return stats


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_timing(hook_name: str, operation: str = "unknown"):
    """Decorator for timing hook operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            timing_id = _performance_monitor.start_hook_timing(hook_name, operation)
            
            try:
                result = func(*args, **kwargs)
                _performance_monitor.end_hook_timing(timing_id, success=True)
                return result
            except Exception as e:
                _performance_monitor.end_hook_timing(
                    timing_id, 
                    success=False, 
                    error_message=str(e)
                )
                _performance_monitor.record_error(type(e).__name__)
                raise
        
        return wrapper
    return decorator


# CLI interface for performance monitoring
if __name__ == "__main__":
    import sys
    
    monitor = get_performance_monitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        # Get performance summary
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        summary = monitor.get_performance_summary(hours)
        print(json.dumps(summary, indent=2))
    
    elif len(sys.argv) > 1 and sys.argv[1] == "optimize":
        # Get optimization recommendations
        project_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        optimizations = monitor.optimize_caches(project_root)
        print(json.dumps(optimizations, indent=2))
    
    else:
        print("Usage:")
        print("  python performance_monitor.py summary [hours]")
        print("  python performance_monitor.py optimize [project_root]")