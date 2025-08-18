# Nx Monorepo Example

This is a complete working example of an Nx monorepo configuration for the Project Index system.

## Structure

```
nx_example/
├── nx.json                 # Nx workspace configuration
├── package.json            # Root package.json with workspaces
├── packages/               # Shared libraries
│   ├── api/               # Backend API package
│   ├── web/               # Web components library
│   └── shared/            # Shared utilities and types
└── apps/                  # Applications
    ├── mobile/            # Mobile application
    └── admin/             # Admin dashboard
```

## Workspaces

- **api** (`packages/api/`) - Backend API services using Express
- **web** (`packages/web/`) - Web frontend components with React
- **shared** (`packages/shared/`) - Shared utilities and TypeScript types
- **mobile** (`apps/mobile/`) - React Native mobile application
- **admin** (`apps/admin/`) - Admin dashboard using Material-UI

## Dependencies

The workspace demonstrates cross-workspace dependencies:
- `api` depends on `shared`
- `web` depends on `shared`
- `mobile` depends on `shared`
- `admin` depends on both `shared` and `web`

## Setup Instructions

1. **Clone this example:**
   ```bash
   cp -r examples/nx_example/ my-nx-project
   cd my-nx-project
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
   # Should show nx.json detected
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
    "tool": "nx",
    "config_file": "nx.json",
    "workspace_count": 5
  },
  "workspace_registry": {
    "api": {
      "path": "packages/api",
      "package_manager": "npm",
      "language_hints": ["typescript", "javascript"]
    },
    "web": {
      "path": "packages/web", 
      "package_manager": "npm",
      "language_hints": ["typescript", "javascript", "css"]
    },
    "shared": {
      "path": "packages/shared",
      "package_manager": "npm",
      "language_hints": ["typescript"]
    },
    "mobile": {
      "path": "apps/mobile",
      "package_manager": "npm"
    },
    "admin": {
      "path": "apps/admin",
      "package_manager": "npm"
    }
  },
  "cross_workspace_dependencies": {
    "dependencies": {
      "api": ["shared"],
      "web": ["shared"], 
      "mobile": ["shared"],
      "admin": ["shared", "web"]
    }
  }
}
```

## Commands

Once indexed, you can use workspace-specific commands:

```bash
# Index specific workspace
python3 ../../scripts/project_index.py --workspace api

# View dependencies
python3 ../../scripts/project_index.py --dependencies

# Performance check
time python3 ../../scripts/project_index.py
```

## Performance Expectations

This example should meet these benchmarks:
- **Full indexing**: <5 seconds
- **Workspace updates**: <200ms
- **Memory usage**: <50MB additional

## Nx Commands

Standard Nx commands work as expected:
```bash
# Build all projects
nx run-many --target=build

# Test affected projects
nx affected --target=test

# View dependency graph
nx dep-graph
```

## Customization

The `projectIndexConfig` section in `nx.json` shows how to customize the Project Index behavior:

```json
{
  "projectIndexConfig": {
    "performance_mode": "balanced",
    "cross_workspace_analysis": true,
    "workspace_overrides": {
      "api": {
        "language_hints": ["typescript", "javascript"],
        "ignore_patterns": ["*.spec.ts", "coverage/"]
      }
    }
  }
}
```

## Integration with Claude Code

Add to your `CLAUDE.md`:

```markdown
@PROJECT_INDEX.json

This Nx monorepo contains 5 workspaces:
- packages/api: Backend API services  
- packages/web: Web frontend components
- packages/shared: Shared utilities and types
- apps/mobile: React Native mobile app
- apps/admin: Admin dashboard

Use `/index --workspace <name>` for workspace-specific operations.
```

## Troubleshooting

**Workspace not detected:**
- Ensure `nx.json` has valid JSON syntax
- Check that workspace directories exist
- Verify `package.json` files exist in each workspace

**Performance issues:**
- Reduce `indexing_depth` in workspace overrides
- Add more ignore patterns for build artifacts
- Use `performance_mode: "fast"` for large projects

**Cross-workspace dependencies missing:**
- Ensure workspace package names use `workspace:*` protocol
- Check that `cross_workspace_analysis` is enabled
- Verify imports use proper package names (e.g., `@example/shared`)

## Best Practices

1. **Use consistent naming**: Scope all packages with organization name
2. **Workspace protocol**: Use `workspace:*` for internal dependencies  
3. **Ignore patterns**: Configure appropriate ignore patterns per workspace type
4. **Language hints**: Specify language hints for better analysis
5. **Performance tuning**: Adjust performance mode based on project size