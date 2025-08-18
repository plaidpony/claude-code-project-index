# Migration Guide: Single-Repo to Monorepo

This guide helps you migrate an existing single-repository project index to a monorepo setup while maintaining full backward compatibility.

## Overview

The Project Index for Claude Code automatically maintains **100% backward compatibility** with single-repository setups. However, converting to monorepo provides these benefits:

- **Workspace isolation** - Changes in one workspace don't trigger full reindexing
- **Selective operations** - Target specific workspaces with `/index --workspace`
- **Dependency tracking** - Understand cross-workspace relationships
- **Performance gains** - Up to 44x faster updates in large codebases

## Pre-Migration Checklist

Before starting migration, ensure:

- [ ] Current `PROJECT_INDEX.json` exists and is working
- [ ] Backup your existing index: `cp PROJECT_INDEX.json PROJECT_INDEX.json.backup`
- [ ] Identify your monorepo structure and tool (Nx, Lerna, Yarn, PNPM, Rush)
- [ ] Test the migration in a separate branch
- [ ] Document your current workspace organization

## Migration Scenarios

### Scenario 1: Existing Monorepo, No Index

You have a monorepo but haven't used Project Index yet.

**Steps:**
```bash
# 1. Install Project Index
curl -s https://raw.githubusercontent.com/anthropic/claude-code-project-index/main/install.sh | bash

# 2. Run automatic detection
python3 scripts/project_index.py

# 3. Verify monorepo detection
jq '.monorepo_info' PROJECT_INDEX.json

# 4. Add to CLAUDE.md
echo -e "\n@PROJECT_INDEX.json" >> CLAUDE.md
```

### Scenario 2: Single Repo → Monorepo Conversion

You're converting a single repository into a monorepo structure.

#### Step 1: Backup Current State
```bash
# Backup existing index
cp PROJECT_INDEX.json PROJECT_INDEX.json.single-repo.backup

# Backup CLAUDE.md if it exists
cp CLAUDE.md CLAUDE.md.backup 2>/dev/null || true
```

#### Step 2: Choose and Configure Monorepo Tool

**Option A: Yarn Workspaces**
```bash
# Update package.json
jq '. + {"workspaces": ["packages/*", "apps/*"]}' package.json > package.json.tmp
mv package.json.tmp package.json

# Create workspace structure
mkdir -p packages/core apps/web
mv src packages/core/
mv public apps/web/
```

**Option B: Lerna**
```bash
# Install and initialize Lerna
npm install -g lerna
lerna init

# Configure lerna.json
cat > lerna.json << EOF
{
  "version": "independent",
  "packages": [
    "packages/*",
    "apps/*"
  ],
  "npmClient": "npm"
}
EOF
```

**Option C: Nx**
```bash
# Install Nx
npm install -g nx

# Initialize Nx workspace
npx create-nx-workspace@latest my-workspace --preset=empty

# Configure nx.json
cat > nx.json << EOF
{
  "version": 2,
  "projects": {
    "core": "packages/core",
    "web": "apps/web"
  }
}
EOF
```

#### Step 3: Migrate Content to Workspaces

**Typical structure transformation:**
```bash
# Before (single repo)
/
├── src/
├── tests/
├── package.json
└── PROJECT_INDEX.json

# After (monorepo)
/
├── packages/
│   └── core/
│       ├── src/
│       └── package.json
├── apps/
│   └── web/
│       ├── src/
│       └── package.json
├── package.json (root)
└── PROJECT_INDEX.json (enhanced)
```

**Migration script:**
```bash
#!/bin/bash
# migrate-to-monorepo.sh

echo "Starting monorepo migration..."

# Create workspace structure
mkdir -p packages/core apps/web

# Move source code
if [ -d "src" ]; then
    echo "Moving src/ to packages/core/"
    mv src packages/core/
fi

# Move tests if they exist
if [ -d "tests" ]; then
    echo "Moving tests to packages/core/"
    mv tests packages/core/
fi

# Create workspace package.json files
cat > packages/core/package.json << EOF
{
  "name": "@myorg/core",
  "version": "1.0.0",
  "main": "src/index.js"
}
EOF

cat > apps/web/package.json << EOF
{
  "name": "@myorg/web",
  "version": "1.0.0",
  "dependencies": {
    "@myorg/core": "workspace:*"
  }
}
EOF

echo "Migration structure complete"
```

#### Step 4: Update Root Configuration

**Update root package.json:**
```bash
# Add workspaces configuration
jq '. + {
  "workspaces": ["packages/*", "apps/*"],
  "private": true
}' package.json > package.json.tmp
mv package.json.tmp package.json
```

#### Step 5: Regenerate Index

```bash
# Remove old index
rm PROJECT_INDEX.json

# Generate new monorepo index
python3 scripts/project_index.py

# Verify monorepo detection
jq '.monorepo_info.tool' PROJECT_INDEX.json
jq '.workspace_registry | keys' PROJECT_INDEX.json
```

### Scenario 3: Existing Single Index → Enhanced Monorepo

You have a working single-repo index and want to enhance it for monorepo features.

```bash
# 1. Verify current index is working
python3 -c "
import json
with open('PROJECT_INDEX.json') as f:
    data = json.load(f)
    print('Current index has', len(data.get('files', {})), 'files')
"

# 2. Run migration check
python3 scripts/reindex_if_needed.py --migrate-check

# 3. Force monorepo detection
python3 scripts/project_index.py --detect-monorepo

# 4. Compare old vs new
echo "Files before:" && jq '.files | keys | length' PROJECT_INDEX.json.backup
echo "Files after:" && jq '.files | keys | length' PROJECT_INDEX.json
echo "Workspaces detected:" && jq '.workspace_registry | keys' PROJECT_INDEX.json
```

## Validation Steps

After migration, validate the setup:

### 1. Index Integrity
```bash
# Verify file count hasn't decreased significantly
OLD_COUNT=$(jq '.files | keys | length' PROJECT_INDEX.json.backup)
NEW_COUNT=$(jq '.files | keys | length' PROJECT_INDEX.json)
echo "File count: $OLD_COUNT → $NEW_COUNT"

# Check for required sections
jq -e '.monorepo_info' PROJECT_INDEX.json > /dev/null && echo "✓ Monorepo info present"
jq -e '.workspace_registry' PROJECT_INDEX.json > /dev/null && echo "✓ Workspace registry present"
```

### 2. Workspace Detection
```bash
# List detected workspaces
echo "Detected workspaces:"
jq -r '.workspace_registry | keys[]' PROJECT_INDEX.json

# Verify workspace file counts
jq '.workspace_registry' PROJECT_INDEX.json
```

### 3. Performance Testing
```bash
# Test update performance
echo "Testing file update performance..."
touch packages/core/src/test-migration.js
time python3 scripts/update_index.py
rm packages/core/src/test-migration.js
```

### 4. Claude Code Integration
```bash
# Update CLAUDE.md if needed
if ! grep -q "@PROJECT_INDEX.json" CLAUDE.md 2>/dev/null; then
    echo "" >> CLAUDE.md
    echo "@PROJECT_INDEX.json" >> CLAUDE.md
    echo "✓ Added PROJECT_INDEX.json to CLAUDE.md"
fi
```

## Rollback Procedure

If migration fails or causes issues:

```bash
# 1. Restore backup
cp PROJECT_INDEX.json.backup PROJECT_INDEX.json

# 2. Restore CLAUDE.md if needed
cp CLAUDE.md.backup CLAUDE.md 2>/dev/null || true

# 3. Clean up monorepo artifacts (if needed)
rm -f lerna.json nx.json pnpm-workspace.yaml .project-index-config.json

# 4. Verify single-repo functionality
python3 scripts/reindex_if_needed.py
echo "Rollback complete - single-repo mode restored"
```

## Post-Migration Optimization

### 1. Configure Workspace-Specific Settings

Create workspace-specific ignore patterns:
```bash
# Add to .project-index-config.json
cat > .project-index-config.json << EOF
{
  "workspaces": {
    "core": {
      "ignore_patterns": [
        "*.test.js",
        "coverage/"
      ]
    },
    "web": {
      "ignore_patterns": [
        "build/",
        "dist/"
      ]
    }
  },
  "performance_mode": "balanced"
}
EOF
```

### 2. Set Up Workspace-Specific Commands

Add workspace shortcuts to your shell:
```bash
# Add to ~/.bashrc or ~/.zshrc
alias index-core="python3 scripts/project_index.py --workspace core"
alias index-web="python3 scripts/project_index.py --workspace web"
alias index-all="python3 scripts/project_index.py"
```

### 3. Update Documentation

Update your project README and CLAUDE.md:
```markdown
# My Project (Monorepo)

@PROJECT_INDEX.json

This is a monorepo with the following workspaces:
- `packages/core` - Core business logic
- `apps/web` - Web frontend application

## Workspace Commands
- `/index --workspace core` - Index only core package
- `/index --workspace web` - Index only web app
- `/index --dependencies` - Show cross-workspace dependencies
```

## Troubleshooting Migration

### Common Issues

**Migration not detected:**
```bash
# Force detection
rm PROJECT_INDEX.json
python3 scripts/project_index.py --force

# Check for configuration files
ls -la | grep -E "\.(json|yaml)$"
```

**Missing workspaces:**
```bash
# Verify workspace patterns
jq '.workspaces' package.json  # For Yarn
jq '.packages' lerna.json      # For Lerna
cat pnpm-workspace.yaml        # For PNPM
```

**Performance regression:**
```bash
# Check index size
ls -lh PROJECT_INDEX.json*

# Profile performance
python3 scripts/performance_monitor.py --profile
```

**Cross-workspace dependencies not detected:**
```bash
# Force dependency analysis
python3 scripts/cross_workspace_analyzer.py --rebuild

# Check dependency graph
jq '.cross_workspace_dependencies' PROJECT_INDEX.json
```

## Advanced Migration Scenarios

### Large Repository Migration

For repositories with 50+ packages:
```bash
# Use performance mode
export PROJECT_INDEX_PERFORMANCE=fast

# Migrate in stages
python3 scripts/project_index.py --workspace-pattern "packages/core*"
python3 scripts/project_index.py --workspace-pattern "packages/ui*"
python3 scripts/project_index.py  # Full migration
```

### Multi-Language Monorepo

For mixed-language codebases:
```bash
# Configure language-specific patterns
cat > .project-index-config.json << EOF
{
  "workspaces": {
    "api": {
      "language_hints": ["python"],
      "ignore_patterns": ["__pycache__/", "*.pyc"]
    },
    "web": {
      "language_hints": ["javascript", "typescript"],
      "ignore_patterns": ["node_modules/", "dist/"]
    }
  }
}
EOF
```

## Next Steps

After successful migration:

1. **Read the [Configuration Reference](configuration-reference.md)** for advanced options
2. **Review [Performance Guide](performance-guide.md)** for optimization tips  
3. **Check out [Examples](../examples/)** for real-world configurations
4. **Set up monitoring** with [Troubleshooting Guide](troubleshooting.md)

## Getting Help

If you encounter issues during migration:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [Configuration Reference](configuration-reference.md)
3. Look at similar setups in [Examples](../examples/)
4. Open an issue with your configuration and error output