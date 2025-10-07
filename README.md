# ddworktree

A Python CLI tool for managing paired Git worktrees with different .gitignore rules.

## Overview

ddworktree simplifies working with paired Git worktrees where you need different .gitignore rules for main and local development. This is particularly useful for:

- Keeping generated files, build artifacts, or local configuration files in your local worktree
- Maintaining clean commits in your main worktree
- Automatically syncing changes between paired worktrees
- Detecting and managing drift between worktrees

## Features

- **Paired Worktree Management**: Create and manage pairs of main and local worktrees
- **Intelligent .gitignore Handling**: Different ignore rules for each worktree
- **Automatic Synchronization**: Sync changes between paired worktrees
- **Drift Detection**: Identify differences between worktrees
- **Git Operations**: Perform Git operations across paired worktrees
- **Configuration Management**: Flexible configuration with TOML/YAML support

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ddworktree

# Install the package
pip install -e .

# Or install dependencies manually
pip install GitPython toml
```

## Quick Start

1. **Initialize ddworktree in your repository**:
   ```bash
   cd your-repo
   ddworktree init
   ```

2. **Add a paired local worktree**:
   ```bash
   ddworktree add
   ```

3. **Work in your local worktree**:
   ```bash
   cd your-repo-local
   # Make changes, add generated files, etc.
   ```

4. **Sync with main worktree**:
   ```bash
   ddworktree sync
   ```

## Commands

### Worktree Management
- `ddworktree add` - Add a paired local worktree
- `ddworktree list` - List all worktrees
- `ddworktree remove` - Remove a worktree

### File Operations
- `ddworktree add <files>` - Add files to staging
- `ddworktree commit <message>` - Commit changes
- `ddworktree reset <files>` - Reset files
- `ddworktree rm <files>` - Remove files
- `ddworktree mv <src> <dest>` - Move files

### Git Operations
- `ddworktree fetch` - Fetch from remote
- `ddworktree pull` - Pull from remote
- `ddworktree push` - Push to remote
- `ddworktree merge` - Merge branches
- `ddworktree rebase` - Rebase branches
- `ddworktree cherry-pick` - Cherry-pick commits

### Sync Operations
- `ddworktree drift` - Show drift between worktrees
- `ddworktree sync` - Sync changes between worktrees

### Status Operations
- `ddworktree status` - Show status of paired worktrees
- `ddworktree diff` - Show differences between worktrees

### Pairing Operations
- `ddworktree pair` - Pair worktrees
- `ddworktree unpair` - Unpair worktrees
- `ddworktree doctor` - Check worktree health
- `ddworktree restore` - Restore missing worktrees

### Advanced Operations
- `ddworktree clone <url>` - Clone with paired worktrees
- `ddworktree logs` - Show commit logs
- `ddworktree config` - Manage configuration

## Configuration

ddworktree uses a flexible configuration system that supports TOML and YAML formats. The configuration file is located at `.ddworktree/config.toml` (or `.ddworktree/config.yaml`).

### Example Configuration

```toml
[pairs]
my-project = "/path/to/main /path/to/local"

[options]
local_suffix = "-local"
auto_sync = "true"
push_local = "false"
default_branch = "main"
sync_on_commit = "true"
verbose = "false"
dry_run_default = "false"
```

### Configuration Options

- `local_suffix`: Suffix for local worktree directories (default: "-local")
- `auto_sync`: Automatically sync changes between worktrees (true/false)
- `push_local`: Include local commits when pushing (true/false)
- `default_branch`: Default branch for new worktrees
- `sync_on_commit`: Automatically sync paired worktree after commit (true/false)
- `verbose`: Enable verbose output by default (true/false)
- `dry_run_default`: Default to dry-run mode for destructive operations (true/false)

## How It Works

### Paired Worktrees

ddworktree creates pairs of worktrees:
- **Main worktree**: Your primary development environment
- **Local worktree**: Contains files you want to keep out of version control

### .gitignore Handling

Each worktree has its own .gitignore rules:
- Main worktree: Uses `.gitignore`
- Local worktree: Uses `.gitignore` + `.gitignore-local`

### Automatic Synchronization

ddworktree automatically syncs:
- Files that exist in both worktrees
- Files that match the main worktree's .gitignore rules
- Files explicitly added to staging

## Use Cases

### Development with Generated Files
- Keep track of your or your agent's ai generated memory files
- Keep generated files, build artifacts, or local configuration in your local worktree
- Maintain clean commits with only source code in your main worktree

### Experimentation
- Try out experimental changes in your local worktree
- Sync only the working changes back to your main worktree
- use a tool like uzi to develop and compare the same feature in parallel with independent environemnts with having to go down a docker hole https://github.com/devflowinc/uzi

### Team Collaboration
- Share your main worktree with the team
- Keep personal development files in your local worktree

## Examples

### Basic Setup
```bash
# Initialize ddworktree
ddworktree init

# Add a paired local worktree
ddworktree add

# Check status
ddworktree status
```

### Working with Paired Worktrees
```bash
# In main worktree
echo "print('Hello')" > main.py
ddworktree add main.py
ddworktree commit "Add main.py"

# In local worktree
cd myproject-local
echo "print('Debug info')" > debug.py
echo "debug.py" >> .gitignore-local

# Sync changes to main worktree
ddworktree sync
```

### Cloning with Paired Worktrees
```bash
# Clone repository with paired worktree
ddworktree clone https://github.com/user/repo.git

# Clone without local worktree
ddworktree clone https://github.com/user/repo.git --no-local
```

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Requirements

- Python 3.7+
- Git
- GitPython
- tomllib (Python 3.11+)

## Support

For issues and questions, please open an issue on the GitHub repository.