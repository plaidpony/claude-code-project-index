# Monorepo Setup Guide

This guide provides step-by-step instructions for setting up the Project Index for Claude Code in various monorepo environments.

## Quick Start

For most monorepos, the setup is automatic:

```bash
# Install the project indexer
curl -s https://raw.githubusercontent.com/anthropic/claude-code-project-index/main/install.sh | bash

# Index your monorepo (automatic detection)
python3 scripts/project_index.py
```

The indexer automatically detects and supports:
- **Nx** monorepos (`nx.json`)
- **Lerna** monorepos (`lerna.json`)
- **Yarn Workspaces** (`package.json` with workspaces)
- **PNPM Workspaces** (`pnpm-workspace.yaml`)
- **Rush** monorepos (`rush.json`)
- **Manual Configuration** (`.project-index-config.json`)

## Supported Monorepo Tools

### Nx Monorepo

**Requirements:**
- `nx.json` file in project root
- Nx CLI installed (`npm install -g nx`)

**Setup:**
```bash
# 1. Ensure nx.json exists with project configurations
cat nx.json
# Should contain projects configuration

# 2. Run indexing
python3 scripts/project_index.py

# 3. Verify detection
ls PROJECT_INDEX.json
```

**Example nx.json:**
```json
{
  "version": 2,
  "projects": {
    "api": "packages/api",
    "web": "packages/web",
    "shared": "packages/shared"
  }
}
```

### Lerna Monorepo

**Requirements:**
- `lerna.json` file in project root
- Lerna installed (`npm install -g lerna`)

**Setup:**
```bash
# 1. Ensure lerna.json exists
cat lerna.json
# Should contain packages configuration

# 2. Run indexing
python3 scripts/project_index.py

# 3. Verify workspace detection
grep -A 10 "workspace_registry" PROJECT_INDEX.json
```

**Example lerna.json:**
```json
{
  "version": "0.0.0",
  "npmClient": "npm",
  "packages": [
    "packages/*"
  ]
}
```

### Yarn Workspaces

**Requirements:**
- `package.json` with workspaces field
- Yarn v1.0+ or Yarn v2+

**Setup:**
```bash
# 1. Verify package.json has workspaces
cat package.json | grep -A 5 "workspaces"

# 2. Run indexing
python3 scripts/project_index.py

# 3. Check workspace detection
python3 -c "
import json
with open('PROJECT_INDEX.json') as f:
    data = json.load(f)
    print('Detected workspaces:', list(data.get('workspace_registry', {}).keys()))
"
```

**Example package.json:**
```json
{
  "name": "my-monorepo",
  "workspaces": [
    "packages/*",
    "apps/*"
  ]
}
```

### PNPM Workspaces

**Requirements:**
- `pnpm-workspace.yaml` file in project root
- PNPM installed (`npm install -g pnpm`)

**Setup:**
```bash
# 1. Ensure pnpm-workspace.yaml exists
cat pnpm-workspace.yaml

# 2. Run indexing
python3 scripts/project_index.py

# 3. Verify workspace registry
jq '.workspace_registry | keys' PROJECT_INDEX.json
```

**Example pnpm-workspace.yaml:**
```yaml
packages:
  - 'packages/*'
  - 'services/*'
```

### Rush Monorepo

**Requirements:**
- `rush.json` file in project root
- Rush installed (`npm install -g @microsoft/rush`)

**Setup:**
```bash
# 1. Verify rush.json exists
cat rush.json | jq '.projects'

# 2. Run indexing
python3 scripts/project_index.py

# 3. Check results
ls PROJECT_INDEX.json && echo "Indexing complete"
```

**Example rush.json:**
```json
{
  "rushVersion": "5.82.0",
  "projects": [
    {
      "packageName": "@company/api",
      "projectFolder": "apps/api"
    },
    {
      "packageName": "@company/web",
      "projectFolder": "apps/web"
    }
  ]
}
```

### Manual Configuration

For custom setups or when automatic detection fails:

**Requirements:**
- Create `.project-index-config.json` in project root

**Setup:**
```bash
# 1. Create manual configuration
cat > .project-index-config.json << EOF
{
  "monorepo": true,
  "workspaces": {
    "api": "services/api",
    "web": "apps/web-frontend",
    "shared": "libraries/shared-utils"
  },
  "tool": "manual",
  "ignore_patterns": [
    "*/node_modules/*",
    "*/dist/*",
    "*.log"
  ]
}
EOF

# 2. Run indexing
python3 scripts/project_index.py

# 3. Validate configuration
python3 -c "
import json
with open('PROJECT_INDEX.json') as f:
    data = json.load(f)
    print('Manual config detected:', data.get('monorepo_info', {}).get('tool') == 'manual')
"
```

## Verification

After setup, verify your monorepo is properly indexed:

### Check Basic Detection
```bash
# Should show monorepo information
grep -A 20 "monorepo_info" PROJECT_INDEX.json

# Should list all workspaces
jq '.workspace_registry | keys' PROJECT_INDEX.json
```

### Verify Cross-Workspace Dependencies
```bash
# Should show dependency relationships
jq '.cross_workspace_dependencies' PROJECT_INDEX.json

# Check for circular dependencies (should be empty or minimal)
jq '.cross_workspace_dependencies.circular_dependencies' PROJECT_INDEX.json
```

### Performance Check
```bash
# Time a full reindex (should be <30s for 50+ workspaces)
time python3 scripts/project_index.py

# Test file update performance (should be <2s)
touch packages/api/src/test.ts
time python3 scripts/update_index.py
```

## Claude Code Integration

Once indexed, add to your `CLAUDE.md`:

```markdown
# My Monorepo Project

@PROJECT_INDEX.json

This project uses [monorepo tool] with the following workspaces:
- api: Backend API services
- web: Frontend web application  
- shared: Shared utilities and types

Use `/index --workspace <name>` for workspace-specific operations.
```

## Troubleshooting

### Common Issues

**No monorepo detected:**
- Ensure configuration file exists in project root
- Check file permissions (`chmod +r *.json *.yaml`)
- Verify syntax with `jq . < config-file.json`

**Missing workspaces:**
- Check workspace patterns in configuration
- Verify workspace directories exist
- Review `.gitignore` patterns

**Performance issues:**
- Use `/index --config` to adjust performance mode
- Consider workspace-specific ignore patterns
- Check available memory (`free -h`)

For more troubleshooting guidance, see [troubleshooting.md](troubleshooting.md).

## Next Steps

- [Migration Guide](migration-guide.md) - Migrate from single-repo
- [Configuration Reference](configuration-reference.md) - Advanced configuration
- [Performance Guide](performance-guide.md) - Optimization strategies

## Examples

See the `examples/` directory for complete, working examples of each monorepo tool configuration.