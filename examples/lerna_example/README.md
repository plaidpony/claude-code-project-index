# Lerna Monorepo Example

This is a complete working example of a Lerna monorepo configuration for the Project Index system.

## Structure

```
lerna_example/
├── lerna.json              # Lerna configuration
├── package.json            # Root package.json with workspaces
├── packages/               # Shared packages (published)
│   ├── core/              # Core business logic and models
│   ├── utils/             # Shared utility functions
│   └── ui/                # UI components library
└── apps/                  # Applications (private)
    ├── web/               # Web application
    └── api/               # API server
```

## Workspaces

### Packages (Published)
- **core** (`packages/core/`) - Core business logic and TypeScript models
- **utils** (`packages/utils/`) - Shared utility functions, depends on `core`
- **ui** (`packages/ui/`) - React UI components library, depends on `core` and `utils`

### Apps (Private)
- **web** (`apps/web/`) - Main web application using React, depends on all packages
- **api** (`apps/api/`) - Backend API server using Express, depends on `core` and `utils`

## Key Features

- **Independent versioning**: Each package maintains its own version
- **Cross-package dependencies**: Packages depend on each other appropriately
- **Publishing workflow**: Only packages are published, apps remain private
- **Conventional commits**: Automatic changelog and version management
- **Shared tooling**: ESLint, TypeScript, and Jest configurations

## Setup Instructions

1. **Clone this example:**
   ```bash
   cp -r examples/lerna_example/ my-lerna-project
   cd my-lerna-project
   ```

2. **Install Lerna globally (optional):**
   ```bash
   npm install -g lerna
   ```

3. **Install dependencies:**
   ```bash
   npm install
   # or
   lerna bootstrap
   ```

4. **Generate Project Index:**
   ```bash
   python3 ../../scripts/project_index.py
   ```

5. **Verify detection:**
   ```bash
   # Should show lerna.json detected
   jq '.monorepo_info.tool' PROJECT_INDEX.json
   
   # Should show 5 workspaces
   jq '.workspace_registry | keys | length' PROJECT_INDEX.json
   ```

## Expected Output

After running the project indexer, you should see:

```json
{
  "monorepo_info": {
    "detected": true,
    "tool": "lerna",
    "config_file": "lerna.json",
    "workspace_count": 5
  },
  "workspace_registry": {
    "core": {
      "path": "packages/core",
      "version": "1.2.0",
      "private": false
    },
    "utils": {
      "path": "packages/utils",
      "version": "0.8.3",
      "private": false
    },
    "ui": {
      "path": "packages/ui", 
      "version": "2.1.5",
      "private": false
    },
    "web-app": {
      "path": "apps/web",
      "version": "3.0.12",
      "private": true
    },
    "api-server": {
      "path": "apps/api",
      "version": "2.3.7", 
      "private": true
    }
  },
  "cross_workspace_dependencies": {
    "dependencies": {
      "utils": ["core"],
      "ui": ["core", "utils"],
      "web-app": ["core", "utils", "ui"],
      "api-server": ["core", "utils"]
    }
  }
}
```

## Lerna Commands

### Development Workflow

```bash
# Bootstrap all packages
lerna bootstrap

# Build all packages
lerna run build

# Test all packages  
lerna run test

# Run command in specific package
lerna run build --scope=@example/core

# Run command in all packages matching pattern
lerna run test --scope=@example/*
```

### Versioning and Publishing

```bash
# See what packages have changed
lerna changed

# Version packages (interactive)
lerna version

# Version packages (automatic with conventional commits)
lerna version --conventional-commits

# Publish packages
lerna publish

# Publish with version increment
lerna publish minor
```

### Utility Commands

```bash
# List all packages
lerna list

# Execute arbitrary command in all packages
lerna exec -- rm -rf node_modules

# Execute command in specific package
lerna exec --scope=@example/core -- pwd

# Clean all node_modules
lerna clean
```

## Project Index Commands

Once indexed, you can use workspace-specific commands:

```bash
# Index specific workspace
python3 ../../scripts/project_index.py --workspace core

# Index only packages
python3 ../../scripts/project_index.py --workspace-pattern "packages/*"

# View dependencies
python3 ../../scripts/project_index.py --dependencies

# Performance check
time python3 ../../scripts/project_index.py
```

## Performance Expectations

This example should meet these benchmarks:
- **Full indexing**: <3 seconds
- **Workspace updates**: <150ms
- **Memory usage**: <40MB additional

## Dependency Management

### Internal Dependencies

Use exact versions for internal dependencies:
```json
{
  "dependencies": {
    "@example/core": "^1.2.0",
    "@example/utils": "^0.8.3"
  }
}
```

### Version Management

Lerna automatically manages cross-package dependencies:
```bash
# Update all package dependencies
lerna version patch

# Bootstrap to link local dependencies
lerna bootstrap
```

## Publishing Strategy

### Public Packages
- `@example/core` - Published to npm
- `@example/utils` - Published to npm  
- `@example/ui` - Published to npm

### Private Apps
- `@example/web-app` - Not published (`"private": true`)
- `@example/api-server` - Not published (`"private": true`)

## Configuration Customization

The `projectIndexConfig` in `lerna.json` shows advanced configuration:

```json
{
  "projectIndexConfig": {
    "performance_mode": "balanced",
    "cross_workspace_analysis": true,
    "workspace_overrides": {
      "core": {
        "language_hints": ["typescript"],
        "ignore_patterns": ["*.spec.ts", "dist/"]
      },
      "ui": {
        "language_hints": ["typescript", "css", "scss"],
        "ignore_patterns": ["*.stories.tsx", "dist/"]
      }
    }
  }
}
```

## Integration with Claude Code

Add to your `CLAUDE.md`:

```markdown
@PROJECT_INDEX.json

This Lerna monorepo contains 5 workspaces:
- packages/core: Core business logic and models
- packages/utils: Shared utility functions  
- packages/ui: React UI components library
- apps/web: Main web application
- apps/api: Backend API server

Use `/index --workspace <name>` for workspace-specific operations.
Run `lerna changed` to see what packages have changes.
```

## Best Practices Demonstrated

1. **Clear separation**: Packages vs. apps structure
2. **Version independence**: Each package has its own version
3. **Dependency management**: Proper internal dependency handling
4. **Publishing strategy**: Only publish reusable packages
5. **Conventional commits**: Automated changelog generation
6. **Performance optimization**: Workspace-specific ignore patterns

## Troubleshooting

**Lerna not found:**
```bash
npm install -g lerna
# or use npx
npx lerna bootstrap
```

**Bootstrap issues:**
```bash
# Clean and reinstall
lerna clean --yes
rm -rf node_modules package-lock.json
npm install
lerna bootstrap
```

**Version conflicts:**
```bash
# Check for version mismatches
lerna diff
lerna changed
```

**Publishing errors:**
```bash
# Verify npm login
npm whoami

# Check package access
npm access list packages @example
```

## Advanced Usage

### Custom Commands

Add to root `package.json`:
```json
{
  "scripts": {
    "build:packages": "lerna run build --scope=packages/*",
    "test:apps": "lerna run test --scope=apps/*",
    "publish:ci": "lerna publish --conventional-commits --yes"
  }
}
```

### Selective Execution

```bash
# Build only changed packages
lerna run build --since HEAD~1

# Test affected packages
lerna run test --since origin/main
```

### Integration Testing

```bash
# Build all dependencies first
lerna run build --include-dependencies

# Test with built dependencies  
lerna run test --stream
```

This example demonstrates best practices for Lerna monorepo management while showcasing how the Project Index system provides enhanced workspace awareness and cross-package dependency tracking.