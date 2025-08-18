# Troubleshooting Guide

This guide helps resolve common issues with the Project Index monorepo system.

## Quick Diagnostics

Run these commands to quickly identify common issues:

```bash
# Check basic system health
python3 scripts/project_index.py --health-check

# Validate configuration
python3 scripts/workspace_config.py --validate

# Test workspace detection
python3 scripts/monorepo_detector.py --test

# Performance check
python3 scripts/performance_monitor.py --summary
```

## Common Issues and Solutions

### 1. Monorepo Not Detected

**Symptoms:**
- `"monorepo": false` in PROJECT_INDEX.json
- Single workspace or no workspace registry
- Tool shows as "none" or "single-repo"

**Diagnosis:**
```bash
# Check for configuration files
ls -la | grep -E "\.(json|yaml)$"

# Test detection manually
python3 -c "
from scripts.monorepo_detector import detect_monorepo
result = detect_monorepo('.')
print('Detection result:', result)
"
```

**Solutions:**

**A. Missing Configuration File:**
```bash
# For Yarn workspaces - check package.json
cat package.json | jq '.workspaces'

# For Lerna - check lerna.json
cat lerna.json | jq '.packages'

# For Nx - check nx.json  
cat nx.json | jq '.projects'

# For PNPM - check pnpm-workspace.yaml
cat pnpm-workspace.yaml

# For Rush - check rush.json
cat rush.json | jq '.projects'
```

**B. Invalid Configuration:**
```bash
# Validate JSON syntax
jq . package.json > /dev/null || echo "Invalid package.json"
jq . lerna.json > /dev/null || echo "Invalid lerna.json"
jq . nx.json > /dev/null || echo "Invalid nx.json"

# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('pnpm-workspace.yaml'))" || echo "Invalid YAML"
```

**C. Force Manual Detection:**
```bash
# Create manual configuration
cat > .project-index-config.json << EOF
{
  "monorepo": true,
  "tool": "manual",
  "workspaces": {
    "app1": "path/to/app1",
    "app2": "path/to/app2"
  }
}
EOF

# Regenerate index
rm PROJECT_INDEX.json
python3 scripts/project_index.py
```

### 2. Missing Workspaces

**Symptoms:**
- Some workspaces not appearing in workspace registry
- Incorrect workspace count
- Workspace paths not resolved

**Diagnosis:**
```bash
# Check workspace patterns
python3 -c "
from scripts.workspace_config import load_workspace_config
registry = load_workspace_config('.')
print('Detected workspaces:')
for name in registry.get_workspace_names():
    ws = registry.get_workspace(name)
    print(f'  {name}: {ws.path}')
"

# Verify workspace directories exist
jq -r '.workspace_registry | to_entries[] | "\(.key): \(.value.path)"' PROJECT_INDEX.json | while read line; do
    name=$(echo $line | cut -d: -f1)
    path=$(echo $line | cut -d: -f2 | xargs)
    if [ -d "$path" ]; then
        echo "✓ $name ($path)"
    else
        echo "✗ $name ($path) - NOT FOUND"
    fi
done
```

**Solutions:**

**A. Fix Workspace Patterns:**
```bash
# For glob patterns that don't match
# Yarn workspaces example:
cat package.json | jq '.workspaces = ["packages/*", "apps/*", "services/*"]'

# Lerna example:
cat lerna.json | jq '.packages = ["packages/*", "apps/*"]'
```

**B. Check Directory Structure:**
```bash
# Ensure directories exist
find . -name "package.json" -not -path "./node_modules/*" | head -10

# Create missing directories if needed
mkdir -p packages/missing-workspace
echo '{"name": "@myorg/missing", "version": "1.0.0"}' > packages/missing-workspace/package.json
```

**C. Override Detection:**
```bash
# Manual workspace specification
cat > .project-index-config.json << EOF
{
  "workspaces": {
    "api": "services/api-server",
    "web": "apps/web-client",
    "shared": "libraries/shared-utils"
  }
}
EOF
```

### 3. Performance Issues

**Symptoms:**
- Indexing takes longer than 30 seconds
- File updates take longer than 2 seconds
- High memory usage (>100MB additional)
- System becomes unresponsive

**Diagnosis:**
```bash
# Check index size
ls -lh PROJECT_INDEX.json

# Profile performance
time python3 scripts/project_index.py

# Monitor resource usage
python3 scripts/performance_monitor.py --profile &
python3 scripts/project_index.py
```

**Solutions:**

**A. Adjust Performance Mode:**
```bash
# Use fast mode for large repositories
cat > .project-index-config.json << EOF
{
  "performance_mode": "fast",
  "cross_workspace_analysis": false,
  "indexing_depth": 3
}
EOF
```

**B. Optimize Ignore Patterns:**
```bash
# Add comprehensive ignore patterns
cat > .project-index-config.json << EOF
{
  "ignore_patterns": [
    "*/node_modules/*",
    "*/dist/*",
    "*/build/*",
    "*/.next/*",
    "*/coverage/*",
    "*.log",
    "*.min.js",
    "*.bundle.js"
  ]
}
EOF
```

**C. Reduce Parallel Workers:**
```bash
# For systems with limited resources
export PROJECT_INDEX_WORKERS=2
python3 scripts/project_index.py
```

### 4. Cross-Workspace Dependencies Not Detected

**Symptoms:**
- Empty `cross_workspace_dependencies` in index
- Missing dependency relationships
- Circular dependencies not caught

**Diagnosis:**
```bash
# Test cross-workspace analysis
python3 scripts/cross_workspace_analyzer.py --test

# Check for import statements
grep -r "import.*@" packages/ apps/ || echo "No scoped imports found"
grep -r "from.*\.\." packages/ apps/ || echo "No relative imports found"
```

**Solutions:**

**A. Enable Cross-Workspace Analysis:**
```bash
cat > .project-index-config.json << EOF
{
  "cross_workspace_analysis": true,
  "detect_circular_deps": true,
  "extract_shared_types": true
}
EOF
```

**B. Configure Package Names:**
```bash
# Ensure workspaces have proper package.json files
for dir in packages/*/; do
    if [ ! -f "$dir/package.json" ]; then
        name=$(basename "$dir")
        echo "{\"name\": \"@myorg/$name\", \"version\": \"1.0.0\"}" > "$dir/package.json"
    fi
done
```

**C. Force Dependency Rebuild:**
```bash
# Rebuild dependency graph
python3 scripts/cross_workspace_analyzer.py --rebuild
python3 scripts/project_index.py --force
```

### 5. File Update Hooks Not Working

**Symptoms:**
- Changes not reflected in index
- Hook timeouts or errors
- Index becomes stale

**Diagnosis:**
```bash
# Test hook functionality
touch packages/test/src/test-file.js
python3 scripts/update_index.py --debug

# Check hook permissions
ls -la scripts/update_index.py
which python3
```

**Solutions:**

**A. Fix Python Path:**
```bash
# Ensure Python is available
python3 --version
which python3

# Use absolute path if needed
sed -i '1s|.*|#!/usr/bin/env python3|' scripts/update_index.py
```

**B. Check File Permissions:**
```bash
# Make scripts executable
chmod +x scripts/*.py
chmod +x scripts/*.sh
```

**C. Manual Hook Testing:**
```bash
# Test hook directly
echo '{"file": "packages/test/src/test.js", "type": "edit"}' | python3 scripts/update_index.py

# Force full reindex
python3 scripts/reindex_if_needed.py --force
```

### 6. Index Corruption or Invalid Format

**Symptoms:**
- JSON parse errors
- Missing required fields
- Inconsistent data structure

**Diagnosis:**
```bash
# Validate JSON structure
jq . PROJECT_INDEX.json > /dev/null || echo "Invalid JSON"

# Check required fields
python3 -c "
import json
with open('PROJECT_INDEX.json') as f:
    data = json.load(f)
    required = ['indexed_at', 'files', 'project_structure']
    for field in required:
        if field not in data:
            print(f'Missing required field: {field}')
"
```

**Solutions:**

**A. Backup and Regenerate:**
```bash
# Backup corrupted index
cp PROJECT_INDEX.json PROJECT_INDEX.json.corrupt

# Regenerate from scratch
rm PROJECT_INDEX.json
python3 scripts/project_index.py
```

**B. Repair Partial Corruption:**
```bash
# Extract and repair specific sections
python3 -c "
import json
with open('PROJECT_INDEX.json.corrupt') as f:
    data = json.load(f)
    
# Repair missing fields
if 'workspace_registry' not in data:
    data['workspace_registry'] = {}
    
with open('PROJECT_INDEX.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

### 7. Memory Issues with Large Monorepos

**Symptoms:**
- Python process uses excessive memory
- System becomes slow or unresponsive
- Out of memory errors

**Diagnosis:**
```bash
# Monitor memory usage during indexing
/usr/bin/time -v python3 scripts/project_index.py 2>&1 | grep -E "(Maximum|Average) resident"

# Check repository size
du -sh . --exclude=node_modules --exclude=.git
```

**Solutions:**

**A. Streaming Mode:**
```bash
# Enable streaming for large files
export PROJECT_INDEX_STREAMING=1
export PROJECT_INDEX_MAX_SIZE=52428800  # 50MB
```

**B. Selective Indexing:**
```bash
# Index workspaces individually
for workspace in $(jq -r '.workspace_registry | keys[]' PROJECT_INDEX.json); do
    echo "Indexing $workspace..."
    python3 scripts/project_index.py --workspace "$workspace"
done
```

### 8. Claude Code Integration Issues

**Symptoms:**
- Index not loaded in Claude Code
- Commands not recognized
- Workspace-specific operations failing

**Diagnosis:**
```bash
# Check CLAUDE.md configuration
cat CLAUDE.md | grep PROJECT_INDEX

# Verify index accessibility
ls -la PROJECT_INDEX.json
```

**Solutions:**

**A. Fix CLAUDE.md Reference:**
```bash
# Add or fix reference
echo "" >> CLAUDE.md
echo "@PROJECT_INDEX.json" >> CLAUDE.md
```

**B. Test Index Loading:**
```bash
# Verify index can be loaded
python3 -c "
import json
with open('PROJECT_INDEX.json') as f:
    data = json.load(f)
    print('Index loaded successfully')
    print(f'Workspaces: {list(data.get(\"workspace_registry\", {}).keys())}')
"
```

## Platform-Specific Issues

### Windows

**Path Separators:**
```bash
# Use forward slashes in configuration
# Wrong: "path": "packages\\api"  
# Correct: "path": "packages/api"
```

**Python Path:**
```bash
# Use py launcher if python3 not available
py -3 scripts/project_index.py
```

### macOS

**Case Sensitivity:**
```bash
# Check filesystem case sensitivity
touch test_file.txt
ls test_FILE.txt 2>/dev/null && echo "Case insensitive" || echo "Case sensitive"
rm test_file.txt
```

### Linux

**Permissions:**
```bash
# Fix script permissions
find scripts -name "*.py" -exec chmod +x {} \;
find scripts -name "*.sh" -exec chmod +x {} \;
```

## Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Environment variable
export PROJECT_INDEX_DEBUG=1
python3 scripts/project_index.py

# Configuration file
cat > .project-index-config.json << EOF
{
  "debug": {
    "enabled": true,
    "log_level": "DEBUG",
    "log_performance": true,
    "log_file": ".project-index-debug.log"
  }
}
EOF

# View debug output
tail -f .project-index-debug.log
```

## Health Check Script

Create a comprehensive health check:

```bash
#!/bin/bash
# health-check.sh

echo "=== Project Index Health Check ==="

# 1. Check Python environment
echo "1. Python Environment:"
python3 --version
echo "Python path: $(which python3)"

# 2. Check configuration files
echo -e "\n2. Configuration Files:"
ls -la | grep -E "\.(json|yaml)$" | while read -r line; do
    file=$(echo "$line" | awk '{print $NF}')
    if [[ "$file" == *.json ]]; then
        jq . "$file" > /dev/null 2>&1 && echo "✓ $file" || echo "✗ $file (invalid JSON)"
    elif [[ "$file" == *.yaml ]]; then
        python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null && echo "✓ $file" || echo "✗ $file (invalid YAML)"
    fi
done

# 3. Check workspace detection
echo -e "\n3. Workspace Detection:"
if python3 scripts/monorepo_detector.py --test > /dev/null 2>&1; then
    echo "✓ Monorepo detection working"
else
    echo "✗ Monorepo detection failed"
fi

# 4. Check index integrity
echo -e "\n4. Index Integrity:"
if [ -f PROJECT_INDEX.json ]; then
    if jq . PROJECT_INDEX.json > /dev/null 2>&1; then
        echo "✓ PROJECT_INDEX.json valid"
        workspaces=$(jq -r '.workspace_registry | length' PROJECT_INDEX.json)
        echo "  Workspaces: $workspaces"
    else
        echo "✗ PROJECT_INDEX.json invalid"
    fi
else
    echo "! PROJECT_INDEX.json not found"
fi

# 5. Check performance
echo -e "\n5. Performance Check:"
start_time=$(date +%s)
python3 scripts/project_index.py > /dev/null 2>&1
end_time=$(date +%s)
duration=$((end_time - start_time))
if [ $duration -lt 30 ]; then
    echo "✓ Indexing completed in ${duration}s (target: <30s)"
else
    echo "⚠ Indexing took ${duration}s (target: <30s)"
fi

echo -e "\nHealth check complete!"
```

## Getting Help

If issues persist after following this guide:

1. **Check the logs:** Look at `.project-index-debug.log` if debug mode is enabled
2. **Run health check:** Use the health check script above
3. **Review configuration:** Double-check [Configuration Reference](configuration-reference.md)
4. **Check examples:** Compare with working examples in `examples/`
5. **Performance issues:** Review [Performance Guide](performance-guide.md)
6. **File an issue:** Include your configuration, error output, and system information

## Issue Template

When reporting issues, include:

```
### System Information
- OS: [Linux/macOS/Windows]
- Python version: [output of `python3 --version`]
- Project size: [number of files/workspaces]

### Configuration
```json
[content of .project-index-config.json or relevant config files]
```

### Error Output
```
[full error message and stack trace]
```

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Behavior
[What you expected to happen]

### Actual Behavior
[What actually happened]
```