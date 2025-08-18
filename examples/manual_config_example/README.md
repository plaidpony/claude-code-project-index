# Manual Configuration Example

This is a complete working example of a manually configured monorepo for the Project Index system, demonstrating advanced configuration options and custom workspace structures.

## Structure

```
manual_config_example/
├── .project-index-config.json  # Manual monorepo configuration
├── package.json                # Root package.json with workspaces
├── backend/                    # Backend services
│   ├── api/                   # Main API server
│   └── auth/                  # Authentication service
├── frontend/                  # Frontend applications  
│   ├── web/                   # Web app with Next.js
│   └── mobile/                # React Native mobile app
├── shared/                    # Shared libraries
│   ├── types/                 # TypeScript type definitions
│   └── utils/                 # Utility functions
└── tools/                     # Development and build tools
    ├── build/                 # Build scripts and configs
    └── cli/                   # CLI development tools
```

## Key Features

### Manual Workspace Configuration
Complete control over workspace detection and configuration via `.project-index-config.json`:

- **Custom paths**: Non-standard directory structures
- **Workspace-specific settings**: Tailored ignore patterns, language hints, indexing depth
- **Advanced options**: Performance tuning, dependency analysis, hooks configuration
- **Metadata**: Project documentation and repository information

### Advanced Configuration Options
- **Performance modes**: Balanced mode with custom worker count
- **Cross-workspace analysis**: Full dependency tracking and circular dependency detection
- **Custom ignore patterns**: Global and workspace-specific patterns
- **Indexing options**: File size limits, parsing depth, symlink handling
- **Output options**: Compression, hashing, dependency graphs

### Multi-Language Support
Demonstrates language-specific optimizations:
- **TypeScript**: Full type analysis and reference resolution
- **JavaScript**: ES6+ parsing and module resolution
- **CSS/SCSS**: Styling and asset management
- **Shell scripts**: Build tool and deployment script handling

## Workspaces

### Backend Services
- **api** (`backend/api/`) - Express + GraphQL API server with TypeORM
- **auth** (`backend/auth/`) - JWT authentication microservice

### Frontend Applications  
- **web** (`frontend/web/`) - Next.js web application with React Query
- **mobile** (`frontend/mobile/`) - React Native app with Expo

### Shared Libraries
- **types** (`shared/types/`) - TypeScript type definitions and Zod schemas
- **utils** (`shared/utils/`) - Shared utility functions and helpers

### Development Tools
- **build-tools** (`tools/build/`) - Webpack, esbuild, and deployment scripts
- **cli** (`tools/cli/`) - Custom CLI for development workflows

## Setup Instructions

1. **Clone this example:**
   ```bash
   cp -r examples/manual_config_example/ my-manual-project
   cd my-manual-project
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Generate Project Index:**
   ```bash
   python3 ../../scripts/project_index.py
   ```

4. **Verify detection:**
   ```bash
   # Should show manual configuration detected
   jq '.monorepo_info.tool' PROJECT_INDEX.json
   
   # Should show 8 workspaces
   jq '.workspace_registry | keys | length' PROJECT_INDEX.json
   
   # Check custom metadata
   jq '.metadata' PROJECT_INDEX.json
   ```

## Expected Output

After running the project indexer, you should see:

```json
{
  "monorepo_info": {
    "detected": true,
    "tool": "manual",
    "config_file": ".project-index-config.json",
    "workspace_count": 8,
    "custom_configuration": true
  },
  "workspace_registry": {
    "api": {
      "path": "backend/api",
      "description": "Main API server with REST and GraphQL endpoints",
      "language_hints": ["typescript", "javascript"],
      "package_manager": "npm",
      "custom_settings": {
        "entry_points": ["src/server.ts", "src/app.ts"],
        "build_outputs": ["dist/"]
      }
    },
    "auth": {
      "path": "backend/auth", 
      "description": "Authentication and authorization microservice",
      "custom_settings": {
        "security_critical": true
      }
    },
    "web": {
      "path": "frontend/web",
      "description": "Web application built with React and Next.js",
      "custom_settings": {
        "static_assets": ["public/", "assets/"]
      }
    },
    "mobile": {
      "path": "frontend/mobile",
      "description": "React Native mobile application",
      "custom_settings": {
        "platforms": ["ios", "android"]
      }
    },
    "types": {
      "path": "shared/types",
      "description": "Shared TypeScript type definitions and interfaces",
      "custom_settings": {
        "type_definitions_only": true
      }
    },
    "utils": {
      "path": "shared/utils",
      "description": "Shared utility functions and helpers",
      "custom_settings": {
        "pure_functions": true
      }
    },
    "build-tools": {
      "path": "tools/build",
      "description": "Build scripts and configuration tools",
      "custom_settings": {
        "executable": true
      }
    },
    "cli": {
      "path": "tools/cli",
      "description": "Command-line interface and development tools",
      "custom_settings": {
        "executable": true,
        "global_install": true
      }
    }
  },
  "cross_workspace_dependencies": {
    "dependencies": {
      "auth": ["types", "utils"],
      "api": ["types", "utils", "auth"],
      "web": ["types", "utils"],
      "mobile": ["types", "utils"],
      "utils": ["types"],
      "build-tools": ["types", "utils"],
      "cli": ["types", "utils", "build-tools"]
    }
  },
  "metadata": {
    "project_name": "Custom Monorepo Example",
    "version": "1.0.0",
    "created_by": "manual_configuration"
  }
}
```

## Configuration Details

### Workspace-Specific Settings

Each workspace can be configured with:

```json
{
  "workspace-name": {
    "path": "relative/path",
    "description": "Workspace description",
    "language_hints": ["typescript", "javascript"],
    "package_manager": "npm",
    "ignore_patterns": ["*.test.ts", "dist/"],
    "indexing_depth": 6,
    "include_tests": false,
    "custom_settings": {
      "entry_points": ["src/index.ts"],
      "build_outputs": ["dist/"],
      "security_critical": true
    }
  }
}
```

### Performance Tuning

```json
{
  "performance_mode": "balanced",
  "parallel_workers": 4,
  "cache_ttl": 300,
  "indexing_options": {
    "max_file_size": 1048576,
    "enable_detailed_parsing": true
  }
}
```

### Dependency Analysis

```json
{
  "cross_workspace_analysis": true,
  "detect_circular_deps": true,
  "dependency_analysis": {
    "typescript_references": true,
    "resolve_path_mapping": true,
    "detect_monorepo_imports": true
  }
}
```

## Development Commands

### Root Commands
```bash
# Build all workspaces in dependency order
npm run build

# Run development servers
npm run dev

# Test all workspaces
npm test

# Lint all code
npm run lint
```

### Workspace-Specific Commands
```bash
# Backend development
npm run dev --workspace=backend/api
npm run test:integration --workspace=backend/api

# Frontend development  
npm run dev --workspace=frontend/web
npm run test:e2e --workspace=frontend/web

# Mobile development
npm run ios --workspace=frontend/mobile
npm run android --workspace=frontend/mobile
```

### Build Tools
```bash
# Use custom build tools
npm run build --workspace=tools/build

# Use CLI tools
npm run build --workspace=tools/cli
npm run link --workspace=tools/cli  # Install globally
```

## Project Index Commands

```bash
# Index specific workspace
python3 ../../scripts/project_index.py --workspace api

# Index by category
python3 ../../scripts/project_index.py --workspace-pattern "backend/*"
python3 ../../scripts/project_index.py --workspace-pattern "shared/*"

# View dependencies
python3 ../../scripts/project_index.py --dependencies

# Performance analysis
time python3 ../../scripts/project_index.py
```

## Performance Expectations

This example should meet these benchmarks:
- **Full indexing**: <5 seconds (8 workspaces)
- **Workspace updates**: <200ms
- **Memory usage**: <60MB additional

## Advanced Features Demonstrated

### 1. Custom Workspace Paths
```json
{
  "workspaces": {
    "api": {
      "path": "backend/api"  // Non-standard nesting
    }
  }
}
```

### 2. Language-Specific Optimization
```json
{
  "api": {
    "language_hints": ["typescript", "javascript"],
    "ignore_patterns": ["*.spec.ts", "coverage/"]
  },
  "mobile": {
    "language_hints": ["typescript", "javascript"],
    "ignore_patterns": ["ios/build/", "android/build/"]
  }
}
```

### 3. Security-Critical Workspaces
```json
{
  "auth": {
    "custom_settings": {
      "security_critical": true,
      "include_tests": true
    }
  }
}
```

### 4. Build Output Tracking
```json
{
  "custom_settings": {
    "entry_points": ["src/server.ts"],
    "build_outputs": ["dist/"],
    "executable": true
  }
}
```

## Integration with Claude Code

Add to your `CLAUDE.md`:

```markdown
@PROJECT_INDEX.json

This manually configured monorepo contains 8 specialized workspaces:

**Backend Services:**
- backend/api: Express + GraphQL API server
- backend/auth: JWT authentication service

**Frontend Apps:**
- frontend/web: Next.js web application
- frontend/mobile: React Native mobile app

**Shared Libraries:**
- shared/types: TypeScript definitions
- shared/utils: Utility functions  

**Development Tools:**
- tools/build: Build scripts and configs
- tools/cli: Development CLI tools

Use `/index --workspace <name>` for workspace-specific operations.
```

## Best Practices Demonstrated

1. **Logical grouping**: Related workspaces in directories (backend/, frontend/, etc.)
2. **Dependency layers**: Clear separation of shared code, services, and apps
3. **Custom configuration**: Workspace-specific optimizations
4. **Security awareness**: Special handling for authentication code
5. **Tool integration**: CLI and build tools as first-class workspaces
6. **Performance tuning**: Optimized ignore patterns and indexing settings
7. **Documentation**: Comprehensive workspace descriptions and metadata

## Troubleshooting

**Manual configuration not detected:**
```bash
# Check file exists and is valid JSON
cat .project-index-config.json | jq . > /dev/null || echo "Invalid JSON"

# Verify tool is set to manual
jq '.tool' .project-index-config.json
```

**Workspace paths not resolved:**
```bash
# Check workspace paths exist
jq -r '.workspaces | to_entries[] | "\(.key): \(.value.path)"' .project-index-config.json | while read line; do
    name=$(echo $line | cut -d: -f1)
    path=$(echo $line | cut -d: -f2 | xargs)
    if [ -d "$path" ]; then
        echo "✓ $name ($path)"
    else
        echo "✗ $name ($path) - NOT FOUND"
    fi
done
```

**Performance issues:**
```bash
# Adjust performance mode
jq '.performance_mode = "fast"' .project-index-config.json > tmp.json && mv tmp.json .project-index-config.json

# Add more ignore patterns
jq '.global_ignore_patterns += ["*.log", "tmp/", "cache/"]' .project-index-config.json > tmp.json && mv tmp.json .project-index-config.json
```

## Migration from Tool-Based Config

To convert an existing tool-based monorepo:

1. **Create base configuration:**
   ```bash
   cp examples/manual_config_example/.project-index-config.json .
   ```

2. **Update workspace paths:**
   ```bash
   # Edit .project-index-config.json workspaces section
   ```

3. **Test configuration:**
   ```bash
   python3 scripts/project_index.py --validate
   ```

4. **Generate new index:**
   ```bash
   python3 scripts/project_index.py
   ```

This manual configuration example showcases the full flexibility and power of the Project Index system when you need complete control over workspace detection and configuration.