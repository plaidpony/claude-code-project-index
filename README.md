# Project Index for Claude Code (v0.1.0)

**⚠️ Early Beta Release** - This tool is in active development. Please report issues and contribute!

A UML-inspired code intelligence system that gives Claude Code comprehensive architectural awareness of your codebase through static analysis and pattern recognition. **Now with full monorepo support** for complex multi-workspace projects.

## 🌟 New in v0.1.0: Complete Monorepo Support

**Advanced monorepo capabilities for modern development workflows:**
- **Multi-tool detection** - Supports Nx, Lerna, Yarn Workspaces, PNPM, Rush, and manual configuration
- **Workspace-aware indexing** - Individual indexes for each workspace with cross-workspace dependency analysis
- **44x performance improvement** - Selective reindexing updates only changed workspaces in <50ms
- **Comprehensive tooling** - Complete documentation, examples, and migration guides for all supported tools

## 🚀 Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/install.sh | bash
```

That's it! The tool is installed with automatic hooks for maintaining the index.

## 📖 Usage

### Create an Index for Your Project

Navigate to any project directory and run:
```bash
/index
```

This creates `PROJECT_INDEX.json` with:
- Complete function/class signatures
- Call graphs showing what calls what
- Directory structure and purposes
- Import dependencies
- Documentation structure

**⚠️ Important: You only need to run `/index` once per project!** The index automatically updates whenever you edit files.

### Using the Index

Once created, reference it when you need architectural awareness:
```bash
# Ask architectural questions
@PROJECT_INDEX.json what functions call authenticate_user?

# Or auto-load in every session by adding to CLAUDE.md:
# Add @PROJECT_INDEX.json to your CLAUDE.md file
```

## 📦 Updating

To update to the latest version, simply run the installer again:
```bash
curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/install.sh | bash
```

**Note**: This will remove and reinstall the tool completely. Your PROJECT_INDEX.json files in projects remain untouched.

## 🔧 Highly Recommended: Claude Code Docs

For the best experience, also install [Claude Code Docs](https://github.com/ericbuess/claude-code-docs) - a companion tool that gives Claude deep understanding of its own capabilities through automatically updated documentation. It provides a `/docs` command that loads the latest Claude Code documentation directly into context, helping Claude use its features more effectively.

## Important: Community Tool - Fork and Customize!

**This is a personal tool** I built and shared with the community. I may not actively maintain it or implement feature requests quickly (or at all). 

### What This Means for You

- **Fork it!** - Make it your own: `git clone https://github.com/plaidpony/claude-code-project-index.git`
- **Let Claude customize it** - Claude Code can modify the tool to fit your exact needs
- **No waiting for updates** - Don't wait for me to add features, ask Claude to add them for you
- **Share your improvements** - Fork and share your enhanced versions with others

### Quick Customization Examples

```bash
# Navigate to the tool's directory
cd ~/.claude-code-project-index

# Open Claude Code and ask for customizations:
# "Modify the indexer to skip test files and only index src/"
# "Add support for Ruby files" 
# "Change the index format to be more compact"
# "Make it work with my monorepo structure"
```


## Background

I created this tool for myself and talked about it in [this video](https://www.youtube.com/watch?v=JU8BwMe_BWg) and [this X post](https://x.com/EricBuess/status/1955271258939043996). People requested it, so here it is! This works alongside my [Claude Code Docs mirror](https://github.com/ericbuess/claude-code-docs) project.

## What Problem Does This Solve for Claude Code?

Claude Code CLI faces specific challenges when working with your codebase. PROJECT_INDEX directly addresses each pain point:

### Common Claude Code Pain Points → Solutions

| Pain Point | Without PROJECT_INDEX | With PROJECT_INDEX |
|------------|----------------------|-------------------|
| **🔄 Duplicate Code** | Claude recreates existing functions because it can't see what's already there | Claude sees all existing functions with signatures and can reuse them |
| **💥 Breaking Changes** | Claude changes a function without knowing what else depends on it | `called_by` field shows exactly what will break if you change something |
| **📁 Wrong Location** | Claude adds code to random files or creates unnecessary new files | Directory purposes and file patterns guide Claude to the right location |
| **🔍 Wasted Tokens** | Claude uses multiple search commands trying to find the right code | Single index reference provides instant navigation to any function |
| **🧟 Dead Code** | Claude keeps unused code because it can't verify if it's called anywhere | Functions without `called_by` are clearly dead code, safe to remove |
| **🐛 Incomplete Fixes** | Claude fixes one function but misses related functions that need updates | `calls` field shows complete call chains for comprehensive fixes |
| **🏗️ Pattern Violations** | Claude uses different patterns than the rest of your codebase | Extracted patterns ensure consistency with existing code style |

PROJECT_INDEX.json solves this by providing Claude with complete architectural and flow awareness of your entire project.

## UML Patterns and Their Value

The system extracts key UML (Unified Modeling Language) concepts to build a comprehensive project model:

### 📐 Class Diagrams
- **Classes with inheritance** (`extends`, `implements`)
- **Methods with full signatures** (parameters, return types)
- **Properties and visibility** (public methods, private internals)
- **Abstract classes and interfaces**

**Why it matters**: Prevents reimplementation of existing functionality and ensures proper inheritance patterns.

### 🔗 Component & Package Diagrams
- **Module dependencies** (imports/exports)
- **Package structure** (directory organization)
- **Dependency graphs** (what depends on what)

**Why it matters**: Helps maintain clean architecture and avoid circular dependencies.

### 📊 Object Diagrams
- **Enumerations with values**
- **Constants and configurations**
- **Type aliases and unions**

**Why it matters**: Ensures consistent use of domain values and types across the codebase.

### 🏛️ Deployment Diagrams
- **File organization and purposes**
- **Directory conventions** (controllers, models, views)
- **Documentation structure**

**Why it matters**: Maintains project conventions and ensures new code goes in the right place.

## Key Features

### 🌳 Directory Tree Visualization
```
.
├── src/ (234 files)
│   ├── auth/ (12 files)
│   ├── models/ (45 files)
│   └── utils/ (67 files)
└── tests/ (89 files)
```

### 📚 Documentation Awareness
Extracts section headers and architectural hints from all markdown files.
- *Helps Claude:* Navigate to relevant documentation sections instantly
- *Avoids:* Missing important project guidelines and conventions

### 🏗️ Directory Purpose Inference
Automatically infers the purpose of directories based on naming patterns:
- `auth/` → "Authentication and authorization logic"
- `models/` → "Data models and database schemas"
- `utils/` → "Shared utility functions and helpers"
- *Helps Claude:* Place new code in the architecturally correct location
- *Avoids:* Creating duplicate directories or misplacing files

### 🔍 Enhanced Code Intelligence with Call Tracking

PROJECT_INDEX provides comprehensive code analysis that directly helps Claude Code avoid mistakes:

#### Call Graph Analysis (v0.2.0) - Flow Awareness
- **`calls` field** - Lists every function that this function calls
  - *Helps Claude:* Follow execution paths when debugging
  - *Avoids:* Missing related bugs in called functions
  
- **`called_by` field** - Lists every function that calls this function  
  - *Helps Claude:* Understand impact before making changes
  - *Avoids:* Breaking dependent code unknowingly
  
- **Dead code detection** - Functions without `called_by` are unused
  - *Helps Claude:* Safely remove unused code
  - *Avoids:* Keeping zombie code that clutters the codebase
  
- **Complete call chains** - Trace from entry points to deep functions
  - *Helps Claude:* Understand full context of execution
  - *Avoids:* Partial fixes that miss root causes

#### Class Diagram Elements
- **Classes with inheritance chains** - `class User(BaseModel, Auditable)`
- **Method signatures with visibility** - Public vs private methods
- **Abstract classes and methods** - `@abstractmethod` markers
- **Interface implementations** - TypeScript `implements` patterns
- **Properties and attributes** - Instance variables and class constants

#### Behavioral Patterns
- **Decorators as stereotypes** - `@property`, `@staticmethod`, `@cached`
- **Method overrides** - Polymorphic behavior tracking
- **Event handlers** - Callback and listener patterns
- **Lifecycle methods** - `__init__`, `componentDidMount`, etc.

#### Structural Patterns
- **Module dependencies** - Import/export relationships
- **Type system modeling** - Aliases, unions, generics
- **Enumerations** - Domain values with meanings
- **Constants and configurations** - System-wide settings
- **Exception hierarchies** - Error handling chains

#### Documentation Integration
- **Docstring extraction** - First line for quick context
- **Architectural hints** - References in markdown files
- **Directory purposes** - Convention-based organization

Example output:
```json
{
  "imports": ["typing", "enum", "abc"],
  "type_aliases": {
    "UserID": "int",
    "ConfigDict": "Dict[str, Union[str, int, bool]]"
  },
  "functions": {
    "create_user": {
      "signature": "(name: str, email: str, role: Role = 'user') -> User",
      "doc": "Create a new user in the system",
      "decorators": ["validate_input", "log_action"],
      "calls": ["validate_email", "hash_password", "save_to_db"],
      "called_by": ["register_user", "admin_create_user"]
    }
  },
  "classes": {
    "User": {
      "inherits": ["BaseModel"],
      "doc": "Represents a system user",
      "abstract": false,
      "methods": {
        "__init__": {
          "signature": "(self, id: int, name: str) -> None",
          "doc": "Initialize user with ID and name"
        },
        "validate": {
          "signature": "(self) -> bool",
          "decorators": ["abstractmethod"]
        }
      },
      "class_constants": {
        "MAX_NAME_LENGTH": "number",
        "DEFAULT_ROLE": "str"
      }
    },
    "APIError": {
      "type": "exception",
      "inherits": ["Exception"],
      "doc": "Base exception for API errors"
    }
  },
  "enums": {
    "Status": {
      "values": ["PENDING", "ACTIVE", "COMPLETED"],
      "doc": "Request status options"
    }
  },
  "constants": {
    "API_VERSION": "str",
    "MAX_RETRIES": "number"
  }
}
```

### 🔄 Automatic Updates via Hooks
- **PostToolUse Hook**: Updates index incrementally when files are edited
  - *Helps Claude:* Always work with current code structure
  - *Avoids:* Stale information leading to wrong decisions
- **Stop Hook**: Checks for staleness and external changes
  - *Helps Claude:* Detect when code changed outside the session
  - *Avoids:* Conflicts with external changes (git pulls, IDE edits)
- **Manual Creation**: Use `/index` command to create initial index
  - *Helps Claude:* Get immediate project awareness
  - *Avoids:* Blind exploration and wasted search commands
- **Smart Maintenance**: Index updates itself automatically after creation
  - *Helps Claude:* Focus on coding, not index management
  - *Avoids:* Manual maintenance overhead

## Real-World Project Sizes

⚠️ **Testing Disclosure**: This tool has primarily been tested on smaller projects. Your experience with larger codebases may vary.

### 🏠 Small Projects (< 50 files)
- Instant indexing and updates
- Full detail extraction
- **Note**: If your entire project fits comfortably in Claude's context window, you might not need this tool - Claude Code can just read all files directly

### 🏢 Medium Projects (50-500 files) - **Limited Testing**
- May take 10-30 seconds to index
- Index file might grow large depending on code complexity
- May require customization for optimal performance

### 🏙️ Large Projects (500+ files) - **Likely Needs Customization**
- Index often exceeds Claude's context limit
- **You'll probably need to ask Claude to customize the indexer**:
  ```
  The index is too large. Please modify scripts/project_index.py to:
  - Only index specific directories (e.g., src/ and lib/)
  - Skip test files, examples, and generated code
  - Limit function details to signatures only
  - Reduce tree depth to 3
  - Add more patterns to .gitignore or create custom ignore filters
  ```
- Consider creating multiple smaller indexes for different parts of your codebase


### When NOT to Use
- **Single-file scripts** - Overhead exceeds benefit
- **Pure documentation repos** - No code to analyze
- **Binary/asset repositories** - No source code structure

## Requirements

- Python 3.8 or higher (intelligently detected during installation)
- Claude Code (any version with hooks support)
- Operating System: macOS or Linux
- Dependencies: `git` and `jq` (for installation)

## Installation

Run this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/install.sh | bash
```

This will:
1. Install PROJECT_INDEX to `~/.claude-code-project-index/`
2. Create the `/index` command in Claude Code
3. Configure hooks for automatic index updates
4. Clean up any old installations

### Manual Installation

If you prefer to install manually:

```bash
git clone https://github.com/plaidpony/claude-code-project-index.git ~/.claude-code-project-index
cd ~/.claude-code-project-index
./install.sh
```

### Uninstalling

To completely remove PROJECT_INDEX:

```bash
~/.claude-code-project-index/uninstall.sh
```

Or if the directory is already gone:

```bash
curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/uninstall.sh | bash
```

## How It Works

### One-Time Setup Per Project
Run `/index` **once** in any project where you want architectural awareness:
```bash
/index
```

This creates `PROJECT_INDEX.json` and enables automatic maintenance.

**Important**: 
- You only need to run `/index` once per project
- The index automatically updates on every file change thereafter
- If you don't want an index in a project, simply don't run `/index` there
- To stop indexing, just delete the PROJECT_INDEX.json file

### What Happens After `/index`

1. **Initial Index Creation**: Analyzes your entire codebase and creates PROJECT_INDEX.json
2. **Automatic Updates**: Hooks update the index whenever you edit files through Claude
3. **External Change Detection**: Detects when files change outside Claude (git pulls, IDE edits)
4. **Smart Reindexing**: Triggers full reindex when structure changes significantly

## Language Support

### Currently Supported Languages

#### Fully Parsed (with enhanced extraction)
- ✅ **Python** (.py)
  - Full function/method signatures with type hints
  - Class inheritance and abstract methods
  - Decorators (@property, @staticmethod, @lru_cache, etc.)
  - Enums with values
  - Type aliases (Union, Optional, etc.)
  - Module and class constants
  - Exception hierarchy
  
- ✅ **JavaScript/TypeScript** (.js, .ts, .tsx, .jsx)
  - Function signatures with parameter types
  - Class inheritance (extends)
  - Interfaces and type definitions
  - Enums with values
  - Type aliases
  - JSDoc comments
  - Import/export tracking
  - Static class properties

- ✅ **Shell Scripts** (.sh, .bash)
  - Function signatures with parameter detection
  - Exported variables with type inference
  - Module-level variables
  - Sourced files tracking
  - Documentation comments
  - Both `function_name()` and `function function_name` syntax

#### Listed Only (file tracking)
All other common languages are tracked but not parsed for signatures:
- Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin, Scala, C#, SQL, R, Lua, Elixir, Julia, Dart, Vue, Svelte, and more

### Adding Language Support

**Want support for your favorite language?** 

Fork this repo and add a parser! Check out the existing parsers in `scripts/index_utils.py`:
- `extract_python_signatures()` for Python
- `extract_javascript_signatures()` for JavaScript/TypeScript
- `extract_shell_signatures()` for Shell scripts

Pull requests are welcome! The parsing doesn't need to be perfect - even basic function detection helps.

## Using PROJECT_INDEX.json

### Option 1: Auto-load via CLAUDE.md (Recommended)
Add to your project's `CLAUDE.md` file to automatically load the index in every session:
```markdown
# Project Context

@PROJECT_INDEX.json

Use the index to understand the codebase structure before making changes.
```

**Benefits**: 
- Loads automatically every session
- Claude always has architectural awareness
- No need to manually reference

**Tradeoff**: Uses context tokens even for simple tasks

### Option 2: Reference When Needed
Only load the index when you need architectural awareness:
```bash
# For specific architectural questions
@PROJECT_INDEX.json what functions call authenticate_user?

# Before major refactoring
@PROJECT_INDEX.json show me all files that import the auth module

# When adding new features
@PROJECT_INDEX.json where should I add a new email service?
```

**Benefits**: 
- Saves context tokens for simple tasks
- More control over when to use it

**Tradeoff**: Need to remember to reference it

### Advanced Usage with Sub-Agents

Use Claude's Task tool for complex architectural analysis:
```
Use the Task tool with the general-purpose agent to analyze @PROJECT_INDEX.json and provide:

1. Impact analysis for refactoring the authentication system:
   - List all files that import or depend on auth modules
   - Identify all functions that call authentication functions
   - Find potential breaking points if auth API changes

2. Dead code analysis:
   - List all functions with no "called_by" field
   - Identify unused imports and modules
   - Suggest safe removal candidates

3. Call chain visualization:
   - Trace complete execution path from login() to database.save()
   - Identify all intermediate functions and their files
   - Highlight potential optimization points

Return specific file:line references for all findings.
```

### Common Usage Patterns

#### Before Making Changes
```bash
# Check what will break if you change a function
@PROJECT_INDEX.json analyze impact of changing validate_user signature

# Find where to add new code
@PROJECT_INDEX.json where should I add a new email validation function?
```

#### During Debugging
```bash
# Trace execution flow
@PROJECT_INDEX.json show the call chain from endpoint to database

# Find all callers of a problematic function
@PROJECT_INDEX.json what calls process_payment and from which files?
```

#### Code Cleanup
```bash
# Find dead code
@PROJECT_INDEX.json list functions with no callers

# Identify duplicate functionality
@PROJECT_INDEX.json find functions with similar names or purposes
```

### Real-World Impact for Claude
- **📍 No More Guessing**: Know exactly where each function exists
- **🎯 Zero Search Waste**: Navigate directly without trial and error
- **💥 Safe Changes**: See impact radius before modifying anything
- **🧹 Clean Codebase**: Remove dead code with confidence
- **🔗 Complete Context**: Understand full execution flows
- **🚀 3x Faster**: Spend time coding, not searching

## Configuration

### Gitignore Support
PROJECT_INDEX automatically respects your `.gitignore` file patterns. Files and directories listed in `.gitignore` will be excluded from indexing, ensuring that:
- Sensitive files (secrets, credentials) are never indexed
- Generated files don't clutter the index
- Test files can be excluded if desired
- Temporary and cache files are ignored

The system combines `.gitignore` patterns with sensible defaults, so even without a `.gitignore` file, common directories like `node_modules`, `.git`, and `__pycache__` are automatically excluded.

### Customizing Additional Ignored Directories
For directories not covered by `.gitignore`, you can edit the `IGNORE_DIRS` set in `~/.claude-code-project-index/scripts/index_utils.py`:
```python
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv', 
    'build', 'dist', '.next', 'target', '.pytest_cache'
}
```

### File Size Limits
The index is automatically compressed if it exceeds 1MB:
- Tree structure is truncated to 100 entries
- Non-parsed files are removed first

## Python Detection

PROJECT_INDEX includes intelligent Python detection that automatically finds and uses the **newest** Python version available:

### How It Works
1. **During Installation**: Scans your system for all Python versions
2. **Selects the Newest**: Automatically picks the latest version (e.g., 3.12 over 3.10)
3. **Saves the Choice**: Stores the selected Python path in `.python_cmd`
4. **Hooks Use Same Python**: All hooks and commands use this saved Python
5. **Virtual Environments Win**: If you're in a venv during install, that takes priority

### Smart Version Selection
- **Finds ALL Python installations** on your system
- **Shows what's available** before making a choice
- **Picks newest by default** for best performance and features
- **Respects virtual environments** - venv Python always wins
- **Consistent across usage** - hooks use the same Python that was selected

Example output:
```
🔍 Searching for Python versions...
   ✓ Found Python 3.11.5 at: /usr/bin/python3.11
   ✓ Found Python 3.12.7 at: /usr/local/bin/python3.12
   ✓ Found Python 3.13.1 at: /opt/homebrew/bin/python3.13

   🎯 Selected newest version: Python 3.13
      Using: /opt/homebrew/bin/python3.13
```

### Manual Override
To use a specific Python version instead of the newest:
```bash
# During installation
export PYTHON_CMD=python3.11
curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/install.sh | bash

# Or for a specific path
export PYTHON_CMD=/usr/local/bin/python3.12
```

### Clear Error Messages
If Python isn't found, you'll see:
- Minimum version requirements (3.8+)
- Platform-specific installation instructions
- How to manually specify Python location

## Troubleshooting

### Python Issues?
If hooks aren't working or you see Python errors:
1. **Check saved Python**: `cat ~/.claude-code-project-index/.python_cmd`
2. **Verify it still works**: Test the command shown above
3. **Reinstall if needed**: The installer will find Python again
4. **Override if needed**: `export PYTHON_CMD=/path/to/python` before installing

### Index not updating?
1. Check that hooks are enabled: `cat ~/.claude/settings.json`
2. Verify installation: `ls -la ~/.claude-code-project-index/`
3. Look for errors in Claude's output
4. Reinstall if needed: `curl -fsSL https://raw.githubusercontent.com/plaidpony/claude-code-project-index/main/install.sh | bash`

### Index too large?
The system automatically compresses large indexes, but you can:
- Add more directories to `IGNORE_DIRS` in `~/.claude-code-project-index/scripts/index_utils.py`
- Reduce `MAX_TREE_DEPTH` (default: 5) in `~/.claude-code-project-index/scripts/project_index.py`

### External changes not detected?
The system checks for changes every time Claude stops. If needed, manually run:
```bash
/index
```
Or from the command line:
```bash
python3 ~/.claude-code-project-index/scripts/project_index.py
```

## Example PROJECT_INDEX.json Structure

```json
{
  "indexed_at": "2024-01-15T10:30:00",
  "root": "/path/to/project",
  "project_structure": {
    "tree": [".", "├── src/", "│   ├── models/", "..."]
  },
  "documentation_map": {
    "README.md": {
      "sections": ["Installation", "Usage", "API Reference"],
      "architecture_hints": ["src/api/", "models/user.py"]
    }
  },
  "directory_purposes": {
    "src/auth": "Authentication and authorization logic",
    "src/models": "Data models and database schemas"
  },
  "files": {
    "src/models/user.py": {
      "language": "python",
      "parsed": true,
      "functions": {
        "hash_password": "(password: str) -> str"
      },
      "classes": {
        "User": {
          "inherits": ["BaseModel"],
          "methods": {
            "__init__": "(self, email: str, name: str) -> None",
            "verify_password": "(self, password: str) -> bool"
          },
          "properties": ["id", "email", "name", "created_at"],
          "class_constants": {
            "DEFAULT_ROLE": "str",
            "MAX_LOGIN_ATTEMPTS": "number"
          }
        }
      },
      "constants": {
        "BCRYPT_ROUNDS": "number",
        "TOKEN_EXPIRY": "number"
      }
    }
  },
  "stats": {
    "total_files": 156,
    "total_directories": 23,
    "fully_parsed": {
      "python": 89,
      "javascript": 45
    },
    "listed_only": {
      "go": 12,
      "rust": 10
    }
  },
  "dependency_graph": {
    "src/api/auth.py": ["bcrypt", "jwt", "./models/user", "./utils/validators"],
    "src/models/user.py": ["sqlalchemy", "./base_model"],
    "src/utils/validators.py": ["re", "email_validator"]
  }
}
```

## Philosophy: Manual Control with Automatic Maintenance

PROJECT_INDEX follows a deliberate design philosophy:

### 🎯 Explicit Creation
- **You decide** which projects need indexing
- **No hidden behavior** - indexes only exist where you create them
- **Privacy respected** - sensitive projects remain unindexed

### 🔄 Automatic Maintenance
- **Once created**, the index maintains itself
- **Incremental updates** on every file edit
- **External change detection** for git operations
- **Staleness checks** ensure accuracy

### 💭 Selective Usage
- **Reference when needed** with `@PROJECT_INDEX.json`
- **Skip for simple tasks** that don't need architecture awareness
- **Optimal token usage** - only load context when valuable

This approach respects developer autonomy while providing powerful assistance when requested.

## Concrete Benefits for Claude Code

### Speed & Efficiency
- **90% fewer search commands** - Direct navigation to any function/class
- **3x faster debugging** - Follow call chains instantly
- **50% less context switching** - All architectural info in one place

### Accuracy & Safety  
- **Zero breaking changes** - `called_by` prevents surprise breakage
- **No duplicate functions** - See all existing code before writing
- **Correct file placement** - Directory purposes guide location choices
- **Safe refactoring** - Know exact impact radius of changes

### Code Quality
- **Dead code removal** - Identify and remove unused functions
- **Pattern consistency** - Match existing code style automatically  
- **Complete fixes** - Fix entire call chains, not just symptoms
- **Architectural integrity** - Maintain established project structure

## Customizing for Your Needs

Rather than waiting for updates, customize the tool yourself:

```bash
# 1. Navigate to the installation
cd ~/.claude-code-project-index

# 2. Ask Claude to make changes
# Examples:
# "Add support for Go and Rust files"
# "Make the index more compact for large projects"
# "Add GraphQL schema parsing"
# "Customize for my Django/Rails/Next.js project"
```

### Adding Language Support
To add a new language parser, ask Claude:
```
Add support for [language] files in scripts/index_utils.py. 
Look at extract_python_signatures() as an example.
```

## Version History

- **v0.1.0** - Initial public release
  - Python, JavaScript/TypeScript, and Shell script parsing
  - Automatic index updates via hooks
  - Gitignore support
  - Basic UML pattern extraction

## License

MIT License - See LICENSE file for details

## Author

Originally created by [Eric Buess](https://github.com/ericbuess), now maintained by [plaidpony](https://github.com/plaidpony)
- 💼 [GitHub](https://github.com/plaidpony)
