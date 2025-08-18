# Configuration Reference

This reference covers all configuration options for the Project Index monorepo system.

## Configuration Files

The system supports multiple configuration methods, applied in order of precedence:

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **`.project-index-config.json`** (manual configuration)
4. **Tool-specific files** (`nx.json`, `lerna.json`, etc.)
5. **Default settings** (lowest priority)

## Manual Configuration File

Create `.project-index-config.json` in your project root for custom configurations:

```json
{
  "monorepo": true,
  "tool": "manual",
  "workspaces": {
    "api": "services/api",
    "web": "apps/web",
    "shared": "packages/shared"
  },
  "ignore_patterns": [
    "*/node_modules/*",
    "*/dist/*",
    "*/.next/*",
    "*.log"
  ],
  "performance_mode": "balanced",
  "cross_workspace_analysis": true,
  "workspace_overrides": {
    "api": {
      "ignore_patterns": ["*.test.py", "__pycache__/"],
      "language_hints": ["python"],
      "indexing_depth": 5
    }
  }
}
```

## Global Configuration Options

### Basic Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `monorepo` | boolean | auto-detected | Force monorepo mode |
| `tool` | string | auto-detected | Monorepo tool (`nx`, `lerna`, `yarn`, `pnpm`, `rush`, `manual`) |
| `auto_detect` | boolean | `true` | Enable automatic monorepo detection |
| `root_path` | string | `"."` | Project root directory |

### Performance Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `performance_mode` | string | `"balanced"` | Performance profile (`fast`, `balanced`, `comprehensive`) |
| `parallel_workers` | number | CPU cores | Number of parallel indexing workers |
| `max_file_size` | number | `1048576` | Maximum file size to parse (1MB) |
| `cache_ttl` | number | `300` | Cache TTL in seconds (5 minutes) |
| `enable_caching` | boolean | `true` | Enable workspace metadata caching |

### Analysis Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cross_workspace_analysis` | boolean | `true` | Enable cross-workspace dependency analysis |
| `detect_circular_deps` | boolean | `true` | Detect circular dependencies |
| `extract_shared_types` | boolean | `true` | Extract shared type definitions |
| `max_analysis_depth` | number | `10` | Maximum dependency analysis depth |

## Workspace Configuration

Define workspace-specific settings in the `workspaces` object:

```json
{
  "workspaces": {
    "workspace-name": {
      "path": "relative/path",
      "ignore_patterns": ["pattern1", "pattern2"],
      "language_hints": ["javascript", "python"],
      "indexing_depth": 3,
      "custom_settings": {}
    }
  }
}
```

### Workspace Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `path` | string | required | Relative path from project root |
| `ignore_patterns` | array | `[]` | Additional ignore patterns |
| `language_hints` | array | auto-detected | Language hints for better parsing |
| `indexing_depth` | number | `5` | Maximum directory traversal depth |
| `include_tests` | boolean | `true` | Include test files in indexing |
| `package_manager` | string | auto-detected | Package manager (`npm`, `yarn`, `pnpm`) |

## Performance Modes

### Fast Mode (`"fast"`)
Optimized for speed, minimal analysis:
```json
{
  "performance_mode": "fast",
  "cross_workspace_analysis": false,
  "indexing_depth": 3,
  "max_file_size": 524288,
  "enable_detailed_parsing": false
}
```

### Balanced Mode (`"balanced"`)
Default mode, good balance of speed and features:
```json
{
  "performance_mode": "balanced",
  "cross_workspace_analysis": true,
  "indexing_depth": 5,
  "max_file_size": 1048576,
  "enable_detailed_parsing": true
}
```

### Comprehensive Mode (`"comprehensive"`)
Full analysis, slower but complete:
```json
{
  "performance_mode": "comprehensive",
  "cross_workspace_analysis": true,
  "indexing_depth": 10,
  "max_file_size": 2097152,
  "extract_all_metadata": true,
  "enable_type_analysis": true
}
```

## Environment Variables

Override configuration with environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_INDEX_PERFORMANCE` | Performance mode | `export PROJECT_INDEX_PERFORMANCE=fast` |
| `PROJECT_INDEX_WORKERS` | Number of parallel workers | `export PROJECT_INDEX_WORKERS=4` |
| `PROJECT_INDEX_CACHE_TTL` | Cache TTL in seconds | `export PROJECT_INDEX_CACHE_TTL=600` |
| `PROJECT_INDEX_MAX_SIZE` | Maximum index size | `export PROJECT_INDEX_MAX_SIZE=10485760` |
| `PROJECT_INDEX_DEBUG` | Enable debug logging | `export PROJECT_INDEX_DEBUG=1` |

## Ignore Patterns

### Global Ignore Patterns
Applied to all workspaces:
```json
{
  "ignore_patterns": [
    "*/node_modules/*",
    "*/dist/*",
    "*/build/*",
    "*/.git/*",
    "*.log",
    "*/.DS_Store"
  ]
}
```

### Common Patterns by Language

**JavaScript/TypeScript:**
```json
[
  "*/node_modules/*",
  "*/dist/*",
  "*/build/*",
  "*/.next/*",
  "*.min.js",
  "*.bundle.js"
]
```

**Python:**
```json
[
  "*/__pycache__/*",
  "*.pyc",
  "*/venv/*",
  "*.egg-info/*",
  "*/dist/*"
]
```

**Java:**
```json
[
  "*/target/*",
  "*.class",
  "*.jar",
  "*/.gradle/*"
]
```

**Rust:**
```json
[
  "*/target/*",
  "Cargo.lock"
]
```

## Tool-Specific Configuration

### Nx Configuration

Enhance existing `nx.json`:
```json
{
  "version": 2,
  "projects": {
    "api": "packages/api",
    "web": "packages/web"
  },
  "projectIndexConfig": {
    "performance_mode": "balanced",
    "workspace_overrides": {
      "api": {
        "ignore_patterns": ["*.spec.ts"]
      }
    }
  }
}
```

### Lerna Configuration

Enhance existing `lerna.json`:
```json
{
  "version": "independent",
  "packages": ["packages/*"],
  "projectIndexConfig": {
    "cross_workspace_analysis": true,
    "ignore_patterns": ["*/test/*"]
  }
}
```

### Package.json Configuration

For Yarn workspaces:
```json
{
  "workspaces": ["packages/*"],
  "projectIndexConfig": {
    "performance_mode": "fast",
    "workspace_overrides": {
      "core": {
        "indexing_depth": 8
      }
    }
  }
}
```

## Advanced Features

### Custom Language Detection

Override automatic language detection:
```json
{
  "language_mappings": {
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".vue": "vue",
    ".svelte": "svelte"
  },
  "workspace_overrides": {
    "frontend": {
      "language_hints": ["typescript", "vue"]
    }
  }
}
```

### Selective Workspace Inclusion

Include only specific workspaces:
```json
{
  "include_workspaces": ["api", "shared"],
  "exclude_workspaces": ["legacy-app"]
}
```

### Cross-Workspace Dependencies

Configure dependency analysis:
```json
{
  "cross_workspace_analysis": {
    "enabled": true,
    "detect_circular": true,
    "max_depth": 5,
    "include_dev_dependencies": false,
    "typescript_references": true,
    "extract_types": {
      "interfaces": true,
      "types": true,
      "enums": true
    }
  }
}
```

### Hooks Configuration

Configure update hooks:
```json
{
  "hooks": {
    "enable_workspace_routing": true,
    "cascade_updates": true,
    "performance_monitoring": true,
    "max_hook_timeout": 30000
  }
}
```

## Validation and Debugging

### Configuration Validation

Validate your configuration:
```bash
# Check configuration syntax
python3 -c "
import json
with open('.project-index-config.json') as f:
    config = json.load(f)
    print('✓ Configuration valid')
"

# Validate with the system
python3 scripts/workspace_config.py --validate

# Test workspace detection
python3 scripts/monorepo_detector.py --test
```

### Debug Configuration

Enable debug output:
```json
{
  "debug": {
    "enabled": true,
    "log_level": "INFO",
    "log_performance": true,
    "log_file": ".project-index-debug.log"
  }
}
```

### Configuration Examples by Use Case

#### Large Monorepo (50+ workspaces)
```json
{
  "performance_mode": "fast",
  "parallel_workers": 8,
  "cross_workspace_analysis": false,
  "indexing_depth": 3,
  "cache_ttl": 900,
  "ignore_patterns": [
    "*/node_modules/*",
    "*/dist/*",
    "*/coverage/*"
  ]
}
```

#### Development Focus
```json
{
  "performance_mode": "comprehensive",
  "cross_workspace_analysis": true,
  "extract_shared_types": true,
  "include_tests": true,
  "enable_type_analysis": true
}
```

#### CI/CD Pipeline
```json
{
  "performance_mode": "balanced",
  "parallel_workers": 4,
  "cache_ttl": 0,
  "enable_caching": false,
  "cross_workspace_analysis": true
}
```

## Migration and Compatibility

### Backward Compatibility

The system maintains 100% backward compatibility with single-repo setups:
```json
{
  "backward_compatibility": {
    "single_repo_fallback": true,
    "preserve_existing_index": true,
    "migration_warnings": true
  }
}
```

### Version-Specific Settings

Configure for different tool versions:
```json
{
  "tool_versions": {
    "nx": {
      "min_version": "14.0.0",
      "config_schema": "v2"
    },
    "lerna": {
      "min_version": "4.0.0"
    }
  }
}
```

## Best Practices

### Configuration Organization

1. **Start Simple:** Begin with automatic detection
2. **Add Gradually:** Introduce custom settings as needed
3. **Document Changes:** Comment complex configurations
4. **Test Thoroughly:** Validate after each change
5. **Version Control:** Commit `.project-index-config.json`

### Performance Optimization

1. **Use appropriate performance mode** for your use case
2. **Configure ignore patterns** to skip unnecessary files
3. **Adjust parallel workers** based on available CPU cores
4. **Monitor memory usage** for large monorepos
5. **Cache workspace metadata** for better performance

### Security Considerations

1. **Never commit secrets** in configuration files
2. **Use environment variables** for sensitive settings
3. **Validate ignore patterns** to avoid exposing sensitive files
4. **Regular security audits** of included files

## Troubleshooting Configuration

### Common Issues

**Configuration not loading:**
```bash
# Check file exists and is readable
ls -la .project-index-config.json
cat .project-index-config.json | jq . > /dev/null || echo "Invalid JSON"
```

**Workspaces not detected:**
```bash
# Verify workspace paths
python3 -c "
import json
with open('.project-index-config.json') as f:
    config = json.load(f)
    for name, path in config.get('workspaces', {}).items():
        print(f'{name}: {path} - exists: {os.path.exists(path)}')
"
```

**Performance issues:**
```bash
# Profile configuration
python3 scripts/performance_monitor.py --config-profile
```

For more troubleshooting help, see [troubleshooting.md](troubleshooting.md).

## Configuration Schema

The complete JSON schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
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
            "ignore_patterns": {"type": "array", "items": {"type": "string"}},
            "language_hints": {"type": "array", "items": {"type": "string"}},
            "indexing_depth": {"type": "number", "minimum": 1}
          }
        }
      }
    },
    "performance_mode": {"enum": ["fast", "balanced", "comprehensive"]},
    "ignore_patterns": {"type": "array", "items": {"type": "string"}},
    "cross_workspace_analysis": {"type": "boolean"}
  }
}
```

Save this schema as `.project-index-schema.json` for IDE validation support.