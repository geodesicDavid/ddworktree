# ddworktree — Design Specification

## Overview

**ddworktree** is a Python CLI tool built on top of Git and GitPython that manages *paired worktrees* — two linked directories that track the same codebase but with different `.gitignore` rules and commit histories.  
This enables parallel tracking of “local” and “global” versions of the same changes, ideal for workflows that isolate environment files, private assets, or sensitive data.

---

## Core Concept

Each ddworktree **pair** consists of:

- A **main** worktree (standard `.gitignore`)
- A **local** worktree (custom `.gitignore-local`)

Example:
```
main/          # global worktree
main-local/    # local variant
```

Pairs are defined in a `.ddconfig` file:
```toml
[pairs]
dev = "dev, dev-local"
story123 = "story123, story123-local"

[options]
auto_sync = true
push_local = false
local_suffix = "-local"
```

---

## Command Specification Table

| **Command** | **Purpose** | **Inputs** | **Outputs** | **Behavior** | **Notes** |
|--------------|--------------|-------------|--------------|---------------|------------|
| `ddworktree worktree add <path> [<commit-ish>]` | Create a new *pair* of linked worktrees (main + local). | `<path>`, optional `<commit-ish>`, flags: `--no-local`, `--track <branch>` | Two directories created, entry in `.ddconfig` | Runs `git worktree add` twice (for `<path>` and `<path>-local`), sets up `.gitignore-local`, records mapping. | Auto-creates local pair unless disabled. Confirms no name collision. |
| `ddworktree worktree list` | Show all ddworktree pairs and their sync status. | None | Table of pairs and drift/sync info | Calls `git worktree list`, cross-references `.ddconfig`, computes drift status. | Adds ✓ or ⚠ indicators for drift. |
| `ddworktree worktree remove <path>` | Remove both worktrees in a pair. | `<path>` or alias name | Confirmation and cleanup logs | Runs `git worktree remove` for both paths, updates `.ddconfig`. | Optional `--keep-local` flag to remove only one. |
| `ddworktree add <files>` | Stage files for commit respecting ignore rules. | `<files>` or `.` | Modified staging area | Reads both `.gitignore` and `.gitignore-local`, stages files appropriately in each worktree. | Auto-detects which tree to add to. |
| `ddworktree commit -m "msg"` | Commit changes to both trees, respecting ignore scopes. | `-m <message>`, optional `--amend`, `--split` | Two commits created (if needed) | Detects shared vs local-only changes, makes separate commits where necessary. | Option to link commits via metadata or `[local]` suffix. |
| `ddworktree reset [--hard|--soft] [<commit-ish>]` | Reset both trees to same commit or HEAD safely. | Optional `<commit-ish>`, flags: `--hard`, `--soft`, `--keep-local` | Both trees reset, status report | Resets each via `git reset`, preserving ignored/local-only files. Warns before hard reset. | Ensures pair remains aligned; optional diff check after. |
| `ddworktree rm <files>` | Remove tracked files across trees. | `<files>` | File removal log | Removes matching tracked files, respecting ignore rules. | May skip ignored or local-only files. |
| `ddworktree mv <src> <dst>` | Move/rename files across paired trees. | `<src>`, `<dst>` | Renamed files | Applies `git mv` in both trees if applicable. | Validates existence in both. |
| `ddworktree fetch` | Fetch remote updates for paired branches. | Optional `--all`, `--prune` | Updated remote refs | Executes fetch once, verifies branch state in both trees. | Typically identical to `git fetch`, scoped to root repo. |
| `ddworktree pull` | Pull updates and sync both trees. | Optional `<remote>`, `<branch>` | Updated local branches | Runs `git pull` in both trees, merges remote changes into each pair branch. | Optional merge conflict resolver for local files. |
| `ddworktree push` | Push commits from main tree (optionally local). | Optional flags: `--include-local` | Push results | Pushes only main worktree branch by default. | Config flag `push_local = false` controls behavior. |
| `ddworktree merge <branch>` | Merge another branch into both trees. | `<branch>` | Merge commit(s) | Runs `git merge` in both trees, applies same branch alignment. | Merge strategy may skip ignored files. |
| `ddworktree rebase <branch>` | Rebase both paired trees on a branch. | `<branch>` | Rebasing logs | Rebases main + local pair sequentially. | Maintains commit linkage. |
| `ddworktree cherry-pick <commit>` | Apply commits to both trees. | `<commit>` | Cherry-pick log | Cherry-picks the same commit into both, respecting ignore scope. | Handles conflicts separately per tree. |
| `ddworktree drift` | Detect unaligned commits or file differences between pair. | Optional `<pair>` | Drift summary | Compares commit hashes and file diffs between main and local trees. | Returns exit code 1 if drift detected (for CI use). |
| `ddworktree sync` | Resynchronize pair to remove drift. | Optional `<pair>`, flags: `--auto-commit`, `--dry-run` | Updated pair | Copies missing files or commits from one to the other, merges diffs, commits results. | Can run interactively or automatic. |
| `ddworktree status` | Combined git status across both worktrees. | `--short`, `--verbose` | Merged status table | Runs `git status --porcelain` for each tree, merges output labeled per tree. | Labels files with `L` or `G` prefix for local/global. |
| `ddworktree diff` | Show diff between paired worktrees (files or commits). | `--name-only`, `--patch`, `<paths>` | Unified diff view | Compares working dirs or HEADs with `git diff --no-index`. | Optional drift summary header. |
| `ddworktree pair <treeA> <treeB>` | Manually link two existing worktrees. | `<treeA>`, `<treeB>` | `.ddconfig` updated | Validates both trees, writes new entry to `.ddconfig`. | Optional `--force` to overwrite. |
| `ddworktree unpair <path>` | Remove a pairing definition. | `<path>` | Confirmation message | Removes pair entry from `.ddconfig`. | Option `--keep-both` keeps directories intact. |
| `ddworktree doctor` | Diagnose and report pairing issues. | `--fix` (optional) | Health report table | Checks existence, HEAD status, commit alignment, config integrity. | Auto-fixes missing local trees if `--fix` used. |
| `ddworktree logs` | Show commit history alignment between pairs. | `--graph`, `--since`, `--until` | Side-by-side log view | Compares `git log --oneline` of each tree, highlights divergent commits. | Optional visualization graph. |
| `ddworktree restore <tree> [--from <pair>]` | Rebuild a missing or broken paired tree. | `<tree>`, optional `--from <pair>` | Restored directory | Runs `git worktree add` at correct commit using partner’s state. | Recreates `.gitignore-local` and config. |
| `ddworktree clone <url> [<dir>]` | Clone main + local trees in one step. | `<url>`, optional `<dir>`, flags: `--branch`, `--no-local` | Two cloned directories | Clones repo, adds paired local tree, initializes `.ddconfig`. | Great for fresh setup or CI automation. |
| `ddworktree config` | Manage ddworktree configuration file. | `--get`, `--set`, `--list` | Config key/value pairs | Reads/writes `.ddconfig` entries. | Can manage suffixes, auto-sync options, and push rules. |

---

## Implementation Architecture

| **Component** | **Description** |
|----------------|----------------|
| `.ddconfig` | TOML or YAML file storing pair mappings and settings. |
| `ddworktree/core.py` | Wrapper around GitPython’s `Repo` and `Worktree` APIs. |
| `ddworktree/commands/` | Each command as its own module (e.g. `reset.py`, `pair.py`). |
| `ddworktree/utils/gitignore.py` | Utility for parsing and comparing `.gitignore` vs `.gitignore-local`. |
| `ddworktree/utils/diff.py` | Drift detection, file/commit comparison helpers. |
| `ddworktree/cli.py` | CLI entrypoint (Click or argparse). |
| `ddworktree/__main__.py` | For `python -m ddworktree` support. |

---

## Example Workflows

### Create Paired Worktrees
```bash
ddworktree worktree add dev main
# creates dev/ and dev-local/
```

### Check Status and Drift
```bash
ddworktree status
ddworktree drift
```

### Sync Pairs
```bash
ddworktree sync --auto-commit
```

### Diagnose and Repair
```bash
ddworktree doctor --fix
```

### Rebuild Local Tree
```bash
ddworktree restore dev-local --from dev
```

---

## Design Notes

- **Safe Defaults:** Operations must always respect `.gitignore` scopes.  
- **Pair Consistency:** Every command that affects one tree should automatically mirror to its pair.  
- **Atomic Commits:** Commits are logically linked across the two trees for consistent history.  
- **Extensible Design:** Each command is modular, allowing new workflows (e.g., `autosync`, `snapshot`, `verify`).  
- **Integration Potential:** Designed to work with `pre-commit`, CI/CD, and dev environments managing environment secrets.  

---

© 2025 ddworktree Design Specification
