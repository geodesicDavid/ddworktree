# ddworktree Implementation Tasks

This document tracks the implementation of ddworktree based on the design specification.

## Task Status Legend
- ✅ Completed
- 🔄 In Progress
- ⏳ Pending
- ❌ Failed

## Core Tasks

### 1. Project Setup and Core Infrastructure
- [ ] **1.1** Create project structure
  - [ ] Create `ddworktree/` main package directory
  - [ ] Create `ddworktree/commands/` for command modules
  - [ ] Create `ddworktree/utils/` for utility modules
  - [ ] Create `ddworktree/core.py` for core functionality
  - [ ] Create `ddworktree/cli.py` for CLI interface
  - [ ] Create `ddworktree/__main__.py` for module execution
  - [ ] Create `tests/` directory
  - [ ] Create `setup.py` or `pyproject.toml`
  - [ ] Create `.gitignore`
  - [ ] Create `README.md`

- [ ] **1.2** Set up core configuration system
  - [ ] Implement `.ddconfig` file handling (TOML/YAML)
  - [ ] Create configuration parser and validator
  - [ ] Implement default configuration values
  - [ ] Create configuration file management utilities

- [ ] **1.3** Implement core GitPython integration
  - [ ] Create Git repository wrapper class
  - [ ] Implement worktree detection and management
  - [ ] Create gitignore parsing utilities
  - [ ] Implement commit tracking and linking

### 2. Core Worktree Management Commands

#### 2.1 worktree add
- [ ] **2.1.1** Create `worktree_add.py` command module
- [ ] **2.1.2** Implement paired worktree creation
  - [ ] Validate path and commit-ish parameters
  - [ ] Handle `--no-local` flag
  - [ ] Handle `--track <branch>` flag
  - [ ] Create main worktree
  - [ ] Create local worktree with `.gitignore-local`
  - [ ] Update `.ddconfig` with new pair
  - [ ] Test collision detection
  - [ ] **2.1.3** Write tests for `worktree add`

#### 2.2 worktree list
- [ ] **2.2.1** Create `worktree_list.py` command module
- [ ] **2.2.2** Implement worktree listing functionality
  - [ ] Call `git worktree list`
  - [ ] Cross-reference with `.ddconfig`
  - [ ] Compute drift/sync status
  - [ ] Display formatted table with indicators
  - [ ] **2.2.3** Write tests for `worktree list`

#### 2.3 worktree remove
- [ ] **2.3.1** Create `worktree_remove.py` command module
- [ ] **2.3.2** Implement worktree removal
  - [ ] Validate path/alias parameter
  - [ ] Handle `--keep-local` flag
  - [ ] Remove both worktrees or just one
  - [ ] Update `.ddconfig`
  - [ ] Provide confirmation and cleanup
  - [ ] **2.3.3** Write tests for `worktree remove`

### 3. File Operations

#### 3.1 add
- [ ] **3.1.1** Create `add.py` command module
- [ ] **3.1.2** Implement file staging with ignore rules
  - [ ] Parse both `.gitignore` and `.gitignore-local`
  - [ ] Auto-detect appropriate worktree
  - [ ] Stage files respecting ignore scopes
  - [ ] **3.1.3** Write tests for `add`

#### 3.2 commit
- [ ] **3.2.1** Create `commit.py` command module
- [ ] **3.2.2** Implement paired commits
  - [ ] Handle `-m <message>` parameter
  - [ ] Handle `--amend` flag
  - [ ] Handle `--split` flag
  - [ ] Detect shared vs local-only changes
  - [ ] Link commits via metadata or suffix
  - [ ] **3.2.3** Write tests for `commit`

#### 3.3 reset
- [ ] **3.3.1** Create `reset.py` command module
- [ ] **3.3.2** Implement paired reset functionality
  - [ ] Handle optional `<commit-ish>` parameter
  - [ ] Handle `--hard`, `--soft`, `--keep-local` flags
  - [ ] Reset both trees safely
  - [ ] Preserve ignored/local-only files
  - [ ] Warn before hard reset
  - [ ] **3.3.3** Write tests for `reset`

#### 3.4 rm
- [ ] **3.4.1** Create `rm.py` command module
- [ ] **3.4.2** Implement file removal across trees
  - [ ] Remove tracked files respecting ignore rules
  - [ ] Skip ignored or local-only files appropriately
  - [ ] **3.4.3** Write tests for `rm`

#### 3.5 mv
- [ ] **3.5.1** Create `mv.py` command module
- [ ] **3.5.2** Implement file renaming across trees
  - [ ] Validate source and destination paths
  - [ ] Apply `git mv` in both applicable trees
  - [ ] **3.5.3** Write tests for `mv`

### 4. Git Operations

#### 4.1 fetch
- [ ] **4.1.1** Create `fetch.py` command module
- [ ] **4.1.2** Implement fetch functionality
  - [ ] Handle `--all` and `--prune` flags
  - [ ] Fetch remote updates for paired branches
  - [ ] Verify branch state in both trees
  - [ ] **4.1.3** Write tests for `fetch`

#### 4.2 pull
- [ ] **4.2.1** Create `pull.py` command module
- [ ] **4.2.2** Implement pull functionality
  - [ ] Handle optional `<remote>` and `<branch>` parameters
  - [ ] Run `git pull` in both trees
  - [ ] Handle merge conflicts for local files
  - [ ] **4.2.3** Write tests for `pull`

#### 4.3 push
- [ ] **4.3.1** Create `push.py` command module
- [ ] **4.3.2** Implement push functionality
  - [ ] Handle `--include-local` flag
  - [ ] Respect `push_local` config setting
  - [ ] Push main worktree branch by default
  - [ ] **4.3.3** Write tests for `push`

#### 4.4 merge
- [ ] **4.4.1** Create `merge.py` command module
- [ ] **4.4.2** Implement merge functionality
  - [ ] Handle `<branch>` parameter
  - [ ] Run `git merge` in both trees
  - [ ] Apply branch alignment
  - [ ] Handle merge strategy for ignored files
  - [ ] **4.4.3** Write tests for `merge`

#### 4.5 rebase
- [ ] **4.5.1** Create `rebase.py` command module
- [ ] **4.5.2** Implement rebase functionality
  - [ ] Handle `<branch>` parameter
  - [ ] Rebase main + local pair sequentially
  - [ ] Maintain commit linkage
  - [ ] **4.5.3** Write tests for `rebase`

#### 4.6 cherry-pick
- [ ] **4.6.1** Create `cherry_pick.py` command module
- [ ] **4.6.2** Implement cherry-pick functionality
  - [ ] Handle `<commit>` parameter
  - [ ] Apply commits to both trees
  - [ ] Respect ignore scope
  - [ ] Handle conflicts separately per tree
  - [ ] **4.6.3** Write tests for `cherry-pick`

### 5. Sync and Drift Detection

#### 5.1 drift
- [ ] **5.1.1** Create `drift.py` command module
- [ ] **5.1.2** Implement drift detection
  - [ ] Handle optional `<pair>` parameter
  - [ ] Compare commit hashes between trees
  - [ ] Compare file differences
  - [ ] Return exit code 1 if drift detected
  - [ ] **5.1.3** Write tests for `drift`

#### 5.2 sync
- [ ] **5.2.1** Create `sync.py` command module
- [ ] **5.2.2** Implement synchronization
  - [ ] Handle optional `<pair>` parameter
  - [ ] Handle `--auto-commit` and `--dry-run` flags
  - [ ] Copy missing files or commits
  - [ ] Merge differences and commit results
  - [ ] Support interactive and automatic modes
  - [ ] **5.2.3** Write tests for `sync`

### 6. Status and Diff Operations

#### 6.1 status
- [ ] **6.1.1** Create `status.py` command module
- [ ] **6.1.2** Implement combined status
  - [ ] Handle `--short` and `--verbose` flags
  - [ ] Run `git status --porcelain` for each tree
  - [ ] Merge output with tree labels
  - [ ] Label files with `L` or `G` prefixes
  - [ ] **6.1.3** Write tests for `status`

#### 6.2 diff
- [ ] **6.2.1** Create `diff.py` command module
- [ ] **6.2.2** Implement diff between worktrees
  - [ ] Handle `--name-only` and `--patch` flags
  - [ ] Handle optional `<paths>` parameter
  - [ ] Compare working dirs or HEADs
  - [ ] Use `git diff --no-index`
  - [ ] Include drift summary header
  - [ ] **6.2.3** Write tests for `diff`

### 7. Pairing Management

#### 7.1 pair
- [ ] **7.1.1** Create `pair.py` command module
- [ ] **7.1.2** Implement manual pairing
  - [ ] Handle `<treeA>` and `<treeB>` parameters
  - [ ] Validate both trees exist
  - [ ] Update `.ddconfig` with new entry
  - [ ] Handle `--force` flag
  - [ ] **7.1.3** Write tests for `pair`

#### 7.2 unpair
- [ ] **7.2.1** Create `unpair.py` command module
- [ ] **7.2.2** Implement unpairing
  - [ ] Handle `<path>` parameter
  - [ ] Remove pair entry from `.ddconfig`
  - [ ] Handle `--keep-both` flag
  - [ ] **7.2.3** Write tests for `unpair`

#### 7.3 doctor
- [ ] **7.3.1** Create `doctor.py` command module
- [ ] **7.3.2** Implement diagnostics
  - [ ] Handle `--fix` flag
  - [ ] Check tree existence and HEAD status
  - [ ] Check commit alignment and config integrity
  - [ ] Auto-fix missing local trees
  - [ ] Generate health report
  - [ ] **7.3.3** Write tests for `doctor`

#### 7.4 restore
- [ ] **7.4.1** Create `restore.py` command module
- [ ] **7.4.2** Implement tree restoration
  - [ ] Handle `<tree>` parameter
  - [ ] Handle `--from <pair>` option
  - [ ] Rebuild missing/broken tree using partner's state
  - [ ] Recreate `.gitignore-local` and config
  - [ ] **7.4.3** Write tests for `restore`

### 8. Advanced Operations

#### 8.1 clone
- [ ] **8.1.1** Create `clone.py` command module
- [ ] **8.1.2** Implement paired cloning
  - [ ] Handle `<url>` and optional `<dir>` parameters
  - [ ] Handle `--branch` and `--no-local` flags
  - [ ] Clone main repository
  - [ ] Add paired local tree
  - [ ] Initialize `.ddconfig`
  - [ ] **8.1.3** Write tests for `clone`

#### 8.2 logs
- [ ] **8.2.1** Create `logs.py` command module
- [ ] **8.2.2** Implement log comparison
  - [ ] Handle `--graph`, `--since`, `--until` flags
  - [ ] Compare `git log --oneline` of each tree
  - [ ] Highlight divergent commits
  - [ ] Optional visualization graph
  - [ ] **8.2.3** Write tests for `logs`

#### 8.3 config
- [ ] **8.3.1** Create `config.py` command module
- [ ] **8.3.2** Implement configuration management
  - [ ] Handle `--get`, `--set`, `--list` operations
  - [ ] Read/write `.ddconfig` entries
  - [ ] Manage suffixes, auto-sync options, push rules
  - [ ] **8.3.3** Write tests for `config`

### 9. CLI Integration

#### 9.1 CLI Framework
- [ ] **9.1.1** Create CLI interface using Click or argparse
- [ ] **9.1.2** Implement command routing
- [ ] **9.1.3** Add help system and usage information
- [ ] **9.1.4** Implement command validation and error handling
- [ ] **9.1.5** Write tests for CLI integration

#### 9.2 Entry Points
- [ ] **9.2.1** Create `__main__.py` for `python -m ddworktree`
- [ ] **9.2.2** Create console script entry point
- [ ] **9.2.3** Test both entry methods work correctly

### 10. Testing and Quality Assurance

#### 10.1 Unit Tests
- [ ] **10.1.1** Create unit tests for all command modules
- [ ] **10.1.2** Create unit tests for utility functions
- [ ] **10.1.3** Create unit tests for core functionality
- [ ] **10.1.4** Mock Git operations for isolated testing

#### 10.2 Integration Tests
- [ ] **10.2.1** Create integration tests for command workflows
- [ ] **10.2.2** Test with real Git repositories
- [ ] **10.2.3** Test paired worktree operations
- [ ] **10.2.4** Test drift detection and sync operations

#### 10.3 End-to-End Tests
- [ ] **10.3.1** Create end-to-end test scenarios
- [ ] **10.3.2** Test complete workflows (create → modify → sync → commit)
- [ ] **10.3.3** Test error handling and edge cases
- [ ] **10.3.4** Test with different Git configurations

#### 10.4 Test Coverage
- [ ] **10.4.1** Ensure 80%+ test coverage
- [ ] **10.4.2** Generate coverage reports
- [ ] **10.4.3** Address any uncovered code paths

### 11. Documentation and Examples

#### 11.1 User Documentation
- [ ] **11.1.1** Create comprehensive README
- [ ] **11.1.2** Document all commands with examples
- [ ] **11.1.3** Create quick start guide
- [ ] **11.1.4** Document configuration options

#### 11.2 Developer Documentation
- [ ] **11.2.1** Create API documentation
- [ ] **11.2.2** Document architecture and design decisions
- [ ] **11.2.3** Create contribution guidelines

### 12. Final Testing and Release

#### 12.1 Comprehensive Testing
- [ ] **12.1.1** Run all tests successfully
- [ ] **12.1.2** Test with different Python versions
- [ ] **12.1.3** Test with different Git versions
- [ ] **12.1.4** Performance testing with large repositories

#### 12.2 Final Polish
- [ ] **12.2.1** Review and refactor code
- [ ] **12.2.2** Optimize performance bottlenecks
- [ ] **12.2.3** Add final error handling improvements
- [ ] **12.2.4** Create release artifacts

## Implementation Notes

### Dependencies
- GitPython for Git operations
- Click or argparse for CLI
- TOML or YAML parser for configuration
- pytest for testing

### Key Design Principles
- **Safe Defaults**: Always respect `.gitignore` scopes
- **Pair Consistency**: Commands should mirror to pairs automatically
- **Atomic Commits**: Logically link commits across trees
- **Extensible Design**: Modular command structure
- **Integration Ready**: Works with pre-commit, CI/CD

### Testing Strategy
- Test each command immediately after implementation
- Use mock Git operations for unit tests
- Use real Git repositories for integration tests
- Ensure comprehensive coverage of edge cases
- Verify that all tests pass at each milestone

---

*Last Updated: 2025-10-07*
*Total Tasks: 12 main categories, 80+ specific subtasks*