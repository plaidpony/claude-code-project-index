#!/usr/bin/env python3
"""
Simple test runner to estimate code coverage for the test enhancement.
Runs all test files and reports results.
"""

import sys
import subprocess
import time
from pathlib import Path

def run_test_file(test_file):
    """Run a single test file and return results."""
    print(f"\n{'='*60}")
    print(f"Running: {test_file.name}")
    print('='*60)
    
    try:
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, str(test_file)], 
            capture_output=True, 
            text=True, 
            cwd=test_file.parent.parent
        )
        end_time = time.time()
        
        print(f"Exit code: {result.returncode}")
        print(f"Runtime: {end_time - start_time:.2f}s")
        
        if result.returncode == 0:
            # Count tests from output
            output_lines = result.stderr.split('\n')
            test_count = 0
            for line in output_lines:
                if line.startswith('Ran ') and 'test' in line:
                    try:
                        test_count = int(line.split()[1])
                        print(f"Tests passed: {test_count}")
                    except (IndexError, ValueError):
                        pass
            print("✅ PASSED")
            return True, test_count
        else:
            print("❌ FAILED")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            return False, 0
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, 0

def main():
    """Run all test files and summarize results."""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print("❌ Tests directory not found!")
        return
    
    # Find all test files
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found!")
        return
    
    print(f"Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    # Run all tests
    total_tests = 0
    passed_files = 0
    failed_files = []
    
    for test_file in test_files:
        success, test_count = run_test_file(test_file)
        if success:
            passed_files += 1
            total_tests += test_count
        else:
            failed_files.append(test_file.name)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total test files: {len(test_files)}")
    print(f"Passed: {passed_files}")
    print(f"Failed: {len(failed_files)}")
    print(f"Total tests run: {total_tests}")
    
    if failed_files:
        print(f"\nFailed files:")
        for failed_file in failed_files:
            print(f"  - {failed_file}")
    
    # Calculate estimated coverage
    scripts_dir = Path(__file__).parent / "scripts"
    python_files = list(scripts_dir.glob("*.py"))
    
    print(f"\nCOVERAGE ESTIMATION:")
    print(f"Scripts to test: {len(python_files)}")
    
    covered_modules = {
        'test_workspace_config.py': ['workspace_config.py', 'monorepo_detector.py'],
        'test_monorepo_detector.py': ['monorepo_detector.py'],
        'test_workspace_hooks.py': ['workspace_config.py', 'monorepo_detector.py', 'performance_monitor.py'],
        'test_project_indexer.py': ['project_index.py', 'index_utils.py'],
        'test_cross_workspace_analyzer.py': ['cross_workspace_analyzer.py', 'workspace_config.py'],
        'test_workspace_indexer.py': ['workspace_indexer.py', 'cross_workspace_analyzer.py', 'workspace_config.py'],
        'test_index_utils.py': ['index_utils.py'],
        'test_enhanced_hooks.py': ['update_index_enhanced.py', 'reindex_if_needed_enhanced.py'],
        'test_performance_monitor.py': ['performance_monitor.py'],
        'test_detect_external_changes.py': ['detect_external_changes.py'],
        'test_update_index.py': ['update_index.py'],
        'test_reindex_if_needed.py': ['reindex_if_needed.py'],
        'test_performance.py': ['performance_monitor.py'],
        'test_monorepo_commands.py': ['monorepo_commands.py'],
        'test_parallel_workspace_processor.py': ['parallel_workspace_processor.py']
    }
    
    all_covered = set()
    for test_file in test_files:
        if test_file.name in covered_modules:
            all_covered.update(covered_modules[test_file.name])
    
    estimated_coverage = len(all_covered) / len(python_files) * 100
    print(f"Estimated coverage: {estimated_coverage:.1f}%")
    
    print(f"\nCovered modules:")
    for module in sorted(all_covered):
        print(f"  ✅ {module}")
    
    uncovered = [f.name for f in python_files if f.name not in all_covered]
    if uncovered:
        print(f"\nUncovered modules:")
        for module in sorted(uncovered):
            print(f"  ❌ {module}")
    
    if estimated_coverage >= 90:
        print(f"\n🎉 EXCELLENT! Estimated coverage ({estimated_coverage:.1f}%) exceeds 90% target!")
    elif estimated_coverage >= 80:
        print(f"\n👍 GOOD! Estimated coverage ({estimated_coverage:.1f}%) is close to 90% target!")
    else:
        print(f"\n⚠️  Coverage ({estimated_coverage:.1f}%) needs improvement to reach 90% target")
    
    return passed_files == len(test_files)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)