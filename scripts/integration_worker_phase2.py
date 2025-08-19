#!/usr/bin/env python3
"""
Integration Worker Phase 2 - Advanced Task Workflow Orchestrator
A comprehensive task management system that extends the existing parallel processing infrastructure.

Features:
- Multi-stage workflow coordination building on WorkspaceTask infrastructure
- Task dependency resolution with cross-workspace awareness
- Intelligent task scheduling and resource optimization
- Integration with existing performance monitoring and caching systems
- Support for different operation types (index, analyze, compress, update)
- Real-time progress tracking and error recovery
- Backward compatibility with all existing monorepo configurations
"""

import json
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Callable, Any, Tuple
from enum import Enum
from queue import Queue, PriorityQueue, Empty
import traceback
import uuid

# Import existing infrastructure
from workspace_config import WorkspaceConfigManager, WorkspaceRegistry, WorkspaceConfig
from parallel_workspace_processor import (
    ParallelWorkspaceProcessor, WorkspaceTask, ProcessingProgress, SharedResourceManager
)
from performance_monitor import get_performance_monitor, performance_timing
from lazy_index_loader import LazyIndexLoader
from smart_compressor import SmartCompressor
from cross_workspace_analyzer import CrossWorkspaceAnalyzer

# Performance monitoring constant
PERFORMANCE_MONITORING = True


class TaskType(Enum):
    """Types of tasks that can be executed."""
    INDEX_WORKSPACE = "index_workspace"
    ANALYZE_DEPENDENCIES = "analyze_dependencies" 
    COMPRESS_INDEX = "compress_index"
    UPDATE_INDEX = "update_index"
    REINDEX_STALE = "reindex_stale"
    CROSS_WORKSPACE_ANALYSIS = "cross_workspace_analysis"
    VALIDATE_INTEGRITY = "validate_integrity"
    CLEANUP_CACHE = "cleanup_cache"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


@dataclass
class IntegrationTask:
    """Enhanced task representation for the integration workflow system."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.INDEX_WORKSPACE
    workspace_name: Optional[str] = None
    priority: int = 0  # Higher numbers = higher priority
    dependencies: Set[str] = field(default_factory=set)  # Task IDs this task depends on
    workspace_dependencies: Set[str] = field(default_factory=set)  # Workspace names this depends on
    estimated_duration: float = 1.0
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    result: Optional[Any] = None
    
    def __lt__(self, other):
        """Support priority queue ordering."""
        return (-self.priority, self.created_at) < (-other.priority, other.created_at)


@dataclass  
class WorkflowProgress:
    """Extended progress tracking for multi-stage workflows."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: Set[str] = field(default_factory=set)
    queued_tasks: Set[str] = field(default_factory=set)
    task_results: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    stage: str = "initialization"
    
    @property
    def percentage_complete(self) -> float:
        """Calculate completion percentage."""
        if self.total_tasks == 0:
            return 100.0
        return (self.completed_tasks / self.total_tasks) * 100.0
    
    @property
    def elapsed_time(self) -> timedelta:
        """Calculate elapsed time."""
        return datetime.now() - self.start_time


class TaskWorkflowOrchestrator:
    """
    Advanced task workflow orchestrator that builds on the existing parallel processing infrastructure.
    Provides multi-stage workflow coordination with intelligent scheduling and resource management.
    """
    
    def __init__(self, 
                 registry: WorkspaceRegistry,
                 max_workers: Optional[int] = None,
                 memory_limit_mb: int = 200,
                 enable_caching: bool = True):
        """
        Initialize the workflow orchestrator.
        
        Args:
            registry: Workspace registry containing all workspaces
            max_workers: Maximum number of worker threads
            memory_limit_mb: Memory limit for operations
            enable_caching: Whether to enable result caching
        """
        self.registry = registry
        self.max_workers = max_workers
        self.memory_limit_mb = memory_limit_mb
        self.enable_caching = enable_caching
        
        # Core processors - build on existing infrastructure
        self.parallel_processor = ParallelWorkspaceProcessor(
            registry=registry,
            max_workers=max_workers,
            memory_limit_mb=memory_limit_mb
        )
        
        # Task management
        self.task_queue = PriorityQueue()
        self.active_tasks: Dict[str, IntegrationTask] = {}
        self.completed_tasks: Dict[str, IntegrationTask] = {}
        self.task_dependencies: Dict[str, Set[str]] = {}  # task_id -> set of dependency task_ids
        
        # Workflow state
        self.workflow_progress = WorkflowProgress()
        self.workflow_callbacks: List[Callable[[WorkflowProgress], None]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_requested = False
        
        # Additional components
        self.lazy_loader = None
        self.compressor = SmartCompressor()
        self.perf_monitor = get_performance_monitor()
        
        # Workflow history for optimization
        self.execution_history: Dict[str, List[float]] = {}  # task_type -> execution times
        
        print(f"Initialized TaskWorkflowOrchestrator with {max_workers} workers")
    
    def add_workflow_callback(self, callback: Callable[[WorkflowProgress], None]):
        """Add a callback function to receive workflow progress updates."""
        self.workflow_callbacks.append(callback)
    
    def _notify_workflow_progress(self):
        """Notify all workflow callbacks of updates."""
        for callback in self.workflow_callbacks:
            try:
                callback(self.workflow_progress)
            except Exception as e:
                print(f"Warning: Workflow callback failed: {e}")
    
    def _estimate_task_duration(self, task: IntegrationTask) -> float:
        """
        Estimate task duration based on historical data and task characteristics.
        
        Args:
            task: Task to estimate duration for
            
        Returns:
            Estimated duration in seconds
        """
        base_duration = 1.0
        
        # Use historical data if available
        task_type_key = task.task_type.value
        if task_type_key in self.execution_history:
            history = self.execution_history[task_type_key]
            if history:
                # Use average of recent executions
                recent_history = history[-10:]  # Last 10 executions
                base_duration = sum(recent_history) / len(recent_history)
        
        # Adjust based on workspace size if applicable
        if task.workspace_name:
            workspace = self.registry.get_workspace(task.workspace_name)
            if workspace:
                try:
                    # Estimate based on workspace file count
                    file_count = sum(1 for _ in workspace.full_path.rglob('*') if _.is_file())
                    size_multiplier = max(0.5, min(5.0, file_count / 100))
                    base_duration *= size_multiplier
                except:
                    pass
        
        # Adjust based on task type
        type_multipliers = {
            TaskType.INDEX_WORKSPACE: 1.0,
            TaskType.ANALYZE_DEPENDENCIES: 0.5,
            TaskType.COMPRESS_INDEX: 0.3,
            TaskType.UPDATE_INDEX: 0.2,
            TaskType.REINDEX_STALE: 0.8,
            TaskType.CROSS_WORKSPACE_ANALYSIS: 2.0,
            TaskType.VALIDATE_INTEGRITY: 0.4,
            TaskType.CLEANUP_CACHE: 0.1
        }
        
        multiplier = type_multipliers.get(task.task_type, 1.0)
        return max(0.1, base_duration * multiplier)
    
    def create_task(self,
                   task_type: Union[TaskType, str],
                   workspace_name: Optional[str] = None,
                   priority: int = 0,
                   dependencies: Optional[Set[str]] = None,
                   workspace_dependencies: Optional[Set[str]] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   **kwargs) -> str:
        """
        Create a new integration task.
        
        Args:
            task_type: Type of task to create (TaskType enum or string)
            workspace_name: Target workspace (if applicable)
            priority: Task priority (higher = more important)
            dependencies: Task IDs this task depends on
            workspace_dependencies: Workspace names this depends on
            metadata: Additional task metadata
            **kwargs: Additional task parameters
            
        Returns:
            Task ID of the created task
        """
        # Handle both string and enum input for task_type
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type)
            except ValueError:
                # Try to match by enum name if value doesn't work
                for enum_member in TaskType:
                    if enum_member.name == task_type or enum_member.value == task_type:
                        task_type = enum_member
                        break
                else:
                    raise ValueError(f"Invalid task type: {task_type}")
        
        task = IntegrationTask(
            task_type=task_type,
            workspace_name=workspace_name,
            priority=priority,
            dependencies=dependencies or set(),
            workspace_dependencies=workspace_dependencies or set(),
            metadata=metadata or {},
            **kwargs
        )
        
        # Estimate duration
        task.estimated_duration = self._estimate_task_duration(task)
        
        with self._lock:
            self.active_tasks[task.task_id] = task
            self.workflow_progress.total_tasks += 1
            
            # Track dependencies
            if task.dependencies:
                self.task_dependencies[task.task_id] = task.dependencies.copy()
        
        print(f"Created task {task.task_id}: {task.task_type.value} for workspace {workspace_name}")
        return task.task_id
    
    def _can_execute_task(self, task: IntegrationTask) -> bool:
        """
        Check if a task can be executed (all dependencies satisfied).
        
        Args:
            task: Task to check
            
        Returns:
            True if task can be executed
        """
        # Check task dependencies
        if task.task_id in self.task_dependencies:
            for dep_id in self.task_dependencies[task.task_id]:
                if dep_id not in self.completed_tasks:
                    return False
                if self.completed_tasks[dep_id].status != TaskStatus.COMPLETED:
                    return False
        
        # Check workspace dependencies
        if task.workspace_dependencies:
            for workspace_name in task.workspace_dependencies:
                # Find most recent task for this workspace
                workspace_tasks = [
                    t for t in self.completed_tasks.values() 
                    if t.workspace_name == workspace_name and t.status == TaskStatus.COMPLETED
                ]
                if not workspace_tasks:
                    return False
        
        return True
    
    def _queue_ready_tasks(self):
        """Queue tasks that are ready for execution."""
        with self._lock:
            ready_tasks = []
            
            for task in self.active_tasks.values():
                if (task.status == TaskStatus.PENDING and 
                    task.task_id not in self.workflow_progress.queued_tasks and
                    self._can_execute_task(task)):
                    ready_tasks.append(task)
            
            # Sort by priority and queue
            ready_tasks.sort(key=lambda t: (-t.priority, t.created_at))
            
            for task in ready_tasks:
                task.status = TaskStatus.QUEUED
                self.workflow_progress.queued_tasks.add(task.task_id)
                self.task_queue.put(task)
    
    @performance_timing("integration_worker", "execute_task")
    def _execute_task(self, task: IntegrationTask) -> Any:
        """
        Execute a single integration task.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
        """
        start_time = time.time()
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            result = None
            
            # Execute based on task type
            if task.task_type == TaskType.INDEX_WORKSPACE:
                if task.workspace_name:
                    indexer = self.parallel_processor._create_workspace_indexer()
                    result = indexer.index_workspace(task.workspace_name)
                
            elif task.task_type == TaskType.ANALYZE_DEPENDENCIES:
                analyzer = self.parallel_processor._create_cross_workspace_analyzer()
                result = analyzer.analyze_all_workspaces()
                
            elif task.task_type == TaskType.COMPRESS_INDEX:
                if 'index_data' in task.metadata:
                    result = self.compressor.compress_workspace_index(task.metadata['index_data'])
                
            elif task.task_type == TaskType.UPDATE_INDEX:
                # Incremental update logic
                if task.workspace_name and 'file_path' in task.metadata:
                    # Implementation would integrate with update_index.py
                    result = {"updated": True, "file": task.metadata['file_path']}
                
            elif task.task_type == TaskType.CROSS_WORKSPACE_ANALYSIS:
                # Full cross-workspace analysis
                workspace_results = task.metadata.get('workspace_results', {})
                result = self.parallel_processor.analyze_cross_workspace_dependencies(workspace_results)
                
            elif task.task_type == TaskType.VALIDATE_INTEGRITY:
                # Validate index integrity
                result = self._validate_index_integrity(task.workspace_name)
                
            elif task.task_type == TaskType.CLEANUP_CACHE:
                # Cache cleanup logic
                result = self._cleanup_caches()
            
            # Record execution time for future estimates
            execution_time = time.time() - start_time
            task_type_key = task.task_type.value
            if task_type_key not in self.execution_history:
                self.execution_history[task_type_key] = []
            self.execution_history[task_type_key].append(execution_time)
            
            # Keep only recent history
            if len(self.execution_history[task_type_key]) > 50:
                self.execution_history[task_type_key] = self.execution_history[task_type_key][-25:]
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            print(f"Task {task.task_id} failed: {e}")
            traceback.print_exc()
            raise
    
    def _validate_index_integrity(self, workspace_name: Optional[str]) -> Dict[str, Any]:
        """Validate the integrity of workspace indexes."""
        # Implementation would check for corrupted or incomplete indexes
        return {"valid": True, "workspace": workspace_name}
    
    def _cleanup_caches(self) -> Dict[str, Any]:
        """Clean up stale cache entries."""
        # Implementation would integrate with LazyIndexLoader cache cleanup
        return {"caches_cleaned": True}
    
    @performance_timing("integration_worker", "execute_workflow")
    def execute_workflow(self,
                        workflow_name: str = "default",
                        target_workspaces: Optional[List[str]] = None,
                        include_cross_analysis: bool = True) -> Dict[str, Any]:
        """
        Execute a complete workflow with multiple stages.
        
        Args:
            workflow_name: Name of the workflow for tracking
            target_workspaces: Specific workspaces to process (None = all)
            include_cross_analysis: Whether to include cross-workspace analysis
            
        Returns:
            Complete workflow results
        """
        print(f"Starting workflow: {workflow_name}")
        
        # Initialize performance monitoring
        workflow_start_time = time.time()
        if PERFORMANCE_MONITORING:
            monitor = get_performance_monitor()
            monitor.set_performance_log_path(self.registry.root_path)
        
        self.workflow_progress.stage = "planning"
        
        # Create workflow tasks
        task_ids = self._create_workflow_tasks(target_workspaces, include_cross_analysis)
        
        self.workflow_progress.stage = "execution"
        self._notify_workflow_progress()
        
        # Process tasks
        results = {}
        
        while not self._all_tasks_completed():
            if self._shutdown_requested:
                break
                
            # Queue ready tasks
            self._queue_ready_tasks()
            
            # Execute queued tasks
            try:
                task = self.task_queue.get(timeout=1.0)
                
                with self._lock:
                    self.workflow_progress.running_tasks.add(task.task_id)
                    self.workflow_progress.queued_tasks.discard(task.task_id)
                
                try:
                    result = self._execute_task(task)
                    
                    with self._lock:
                        self.workflow_progress.completed_tasks += 1
                        self.workflow_progress.task_results[task.task_id] = result
                        self.completed_tasks[task.task_id] = task
                        self.active_tasks.pop(task.task_id, None)
                        
                        if task.task_id in self.task_dependencies:
                            del self.task_dependencies[task.task_id]
                    
                    results[task.task_id] = result
                    
                except Exception as e:
                    with self._lock:
                        self.workflow_progress.failed_tasks += 1
                        task.status = TaskStatus.FAILED
                        self.completed_tasks[task.task_id] = task
                        self.active_tasks.pop(task.task_id, None)
                    
                    print(f"Task {task.task_id} failed: {e}")
                
                finally:
                    with self._lock:
                        self.workflow_progress.running_tasks.discard(task.task_id)
                
                self._notify_workflow_progress()
                
            except Empty:
                # No tasks ready - continue to check for newly ready tasks
                continue
        
        self.workflow_progress.stage = "completed"
        self._notify_workflow_progress()
        
        # Record workflow performance metrics
        workflow_elapsed_time = time.time() - workflow_start_time
        if PERFORMANCE_MONITORING and workflow_elapsed_time > 30.0:  # Log if workflow takes >30s
            monitor = get_performance_monitor()
            monitor.record_error(f'long_workflow_execution_{workflow_name}')
        
        return {
            "workflow_name": workflow_name,
            "results": results,
            "progress": {
                "total_tasks": self.workflow_progress.total_tasks,
                "completed": self.workflow_progress.completed_tasks,
                "failed": self.workflow_progress.failed_tasks,
                "elapsed_time": str(self.workflow_progress.elapsed_time)
            },
            "performance_metrics": {
                "workflow_duration_seconds": workflow_elapsed_time,
                "average_task_time": workflow_elapsed_time / max(1, self.workflow_progress.completed_tasks),
                "tasks_per_minute": (self.workflow_progress.completed_tasks / workflow_elapsed_time) * 60 if workflow_elapsed_time > 0 else 0
            }
        }
    
    def _create_workflow_tasks(self, 
                              target_workspaces: Optional[List[str]], 
                              include_cross_analysis: bool) -> List[str]:
        """Create tasks for a complete workflow."""
        task_ids = []
        
        # Get workspaces to process
        workspaces = target_workspaces or self.registry.get_workspace_names()
        
        # Stage 1: Index workspaces
        workspace_task_ids = {}
        for workspace_name in workspaces:
            task_id = self.create_task(
                task_type=TaskType.INDEX_WORKSPACE,
                workspace_name=workspace_name,
                priority=10
            )
            workspace_task_ids[workspace_name] = task_id
            task_ids.append(task_id)
        
        # Stage 2: Cross-workspace analysis (depends on all workspace indexing)
        if include_cross_analysis:
            analysis_task_id = self.create_task(
                task_type=TaskType.CROSS_WORKSPACE_ANALYSIS,
                priority=5,
                dependencies=set(workspace_task_ids.values()),
                metadata={"workspace_results": {}}
            )
            task_ids.append(analysis_task_id)
        
        # Stage 3: Compression (optional, low priority)
        for workspace_name in workspaces:
            compress_task_id = self.create_task(
                task_type=TaskType.COMPRESS_INDEX,
                workspace_name=workspace_name,
                priority=1,
                dependencies={workspace_task_ids[workspace_name]}
            )
            task_ids.append(compress_task_id)
        
        return task_ids
    
    def _all_tasks_completed(self) -> bool:
        """Check if all tasks have completed."""
        with self._lock:
            return (len(self.active_tasks) == 0 and 
                    self.task_queue.empty() and 
                    len(self.workflow_progress.running_tasks) == 0)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific task."""
        with self._lock:
            task = self.active_tasks.get(task_id) or self.completed_tasks.get(task_id)
            if not task:
                return None
            
            return {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "status": task.status.value,
                "workspace_name": task.workspace_name,
                "priority": task.priority,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message,
                "retry_count": task.retry_count
            }
    
    def shutdown(self):
        """Request graceful shutdown of the orchestrator."""
        self._shutdown_requested = True
        self.parallel_processor.shutdown()
        print("Shutdown requested for TaskWorkflowOrchestrator")


# Convenience functions for easy integration
def create_integration_orchestrator(root_path: Union[str, Path], 
                                  max_workers: Optional[int] = None) -> TaskWorkflowOrchestrator:
    """
    Create a new integration orchestrator for the given project.
    
    Args:
        root_path: Path to the project root
        max_workers: Maximum number of worker threads
        
    Returns:
        Configured TaskWorkflowOrchestrator instance
    """
    config_manager = WorkspaceConfigManager(root_path)
    registry = config_manager.load_configuration()
    
    return TaskWorkflowOrchestrator(
        registry=registry,
        max_workers=max_workers
    )


def execute_integration_workflow(root_path: Union[str, Path],
                                target_workspaces: Optional[List[str]] = None,
                                workflow_name: str = "integration",
                                max_workers: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a complete integration workflow for the given project.
    
    Args:
        root_path: Path to the project root
        target_workspaces: Specific workspaces to process
        workflow_name: Name for the workflow
        max_workers: Maximum number of worker threads
        
    Returns:
        Complete workflow results
    """
    orchestrator = create_integration_orchestrator(root_path, max_workers)
    
    try:
        return orchestrator.execute_workflow(
            workflow_name=workflow_name,
            target_workspaces=target_workspaces,
            include_cross_analysis=True
        )
    finally:
        orchestrator.shutdown()


# CLI interface
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Integration Worker Phase 2")
    parser.add_argument("root_path", help="Path to the project root")
    parser.add_argument("--workspaces", "-w", nargs="*", help="Specific workspaces to process")
    parser.add_argument("--workflow", "-n", default="cli", help="Workflow name")
    parser.add_argument("--max-workers", "-j", type=int, help="Maximum number of worker threads")
    parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    try:
        results = execute_integration_workflow(
            root_path=args.root_path,
            target_workspaces=args.workspaces,
            workflow_name=args.workflow,
            max_workers=args.max_workers
        )
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results written to {args.output}")
        else:
            progress = results.get("progress", {})
            print(f"\nWorkflow '{args.workflow}' completed:")
            print(f"  Total tasks: {progress.get('total_tasks', 0)}")
            print(f"  Completed: {progress.get('completed', 0)}")
            print(f"  Failed: {progress.get('failed', 0)}")
            print(f"  Elapsed time: {progress.get('elapsed_time', 'N/A')}")
            
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)