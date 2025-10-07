"""
CLI interface for ddworktree.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List

from .core import DDWorktreeRepo, DDWorktreeError


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='ddworktree',
        description='Manage paired Git worktrees with different .gitignore rules'
    )

    # Add global options
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 0.1.0'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Worktree commands
    worktree_parser = subparsers.add_parser('worktree', help='Manage worktrees')
    worktree_subparsers = worktree_parser.add_subparsers(dest='worktree_command')

    # worktree add
    add_parser = worktree_subparsers.add_parser('add', help='Add a new paired worktree')
    add_parser.add_argument('path', help='Path for the new worktree')
    add_parser.add_argument('commitish', nargs='?', help='Commit-ish to checkout')
    add_parser.add_argument('--no-local', action='store_true', help='Do not create local pair')
    add_parser.add_argument('--track', help='Track specific branch')

    # worktree list
    list_parser = worktree_subparsers.add_parser('list', help='List all worktree pairs')

    # worktree remove
    remove_parser = worktree_subparsers.add_parser('remove', help='Remove a worktree pair')
    remove_parser.add_argument('path', help='Path or alias of worktree to remove')
    remove_parser.add_argument('--keep-local', action='store_true', help='Keep local worktree')

    # File operations
    add_cmd_parser = subparsers.add_parser('add', help='Stage files for commit')
    add_cmd_parser.add_argument('files', nargs='*', default=['.'], help='Files to stage')

    commit_parser = subparsers.add_parser('commit', help='Commit changes')
    commit_parser.add_argument('-m', '--message', required=True, help='Commit message')
    commit_parser.add_argument('--amend', action='store_true', help='Amend previous commit')
    commit_parser.add_argument('--split', action='store_true', help='Split into separate commits')

    reset_parser = subparsers.add_parser('reset', help='Reset worktrees')
    reset_parser.add_argument('commitish', nargs='?', help='Commit to reset to')
    reset_parser.add_argument('--hard', action='store_true', help='Hard reset')
    reset_parser.add_argument('--soft', action='store_true', help='Soft reset')
    reset_parser.add_argument('--keep-local', action='store_true', help='Keep local changes')

    rm_parser = subparsers.add_parser('rm', help='Remove files')
    rm_parser.add_argument('files', nargs='+', help='Files to remove')

    mv_parser = subparsers.add_parser('mv', help='Move/rename files')
    mv_parser.add_argument('source', help='Source file or directory')
    mv_parser.add_argument('destination', help='Destination file or directory')

    # Git operations
    fetch_parser = subparsers.add_parser('fetch', help='Fetch remote updates')
    fetch_parser.add_argument('--all', action='store_true', help='Fetch all remotes')
    fetch_parser.add_argument('--prune', action='store_true', help='Prune deleted branches')

    pull_parser = subparsers.add_parser('pull', help='Pull updates')
    pull_parser.add_argument('remote', nargs='?', help='Remote to pull from')
    pull_parser.add_argument('branch', nargs='?', help='Branch to pull')

    push_parser = subparsers.add_parser('push', help='Push commits')
    push_parser.add_argument('--include-local', action='store_true', help='Include local commits')

    merge_parser = subparsers.add_parser('merge', help='Merge branch')
    merge_parser.add_argument('branch', help='Branch to merge')

    rebase_parser = subparsers.add_parser('rebase', help='Rebase worktrees')
    rebase_parser.add_argument('branch', help='Branch to rebase onto')

    cherry_pick_parser = subparsers.add_parser('cherry-pick', help='Cherry-pick commits')
    cherry_pick_parser.add_argument('commit', help='Commit to cherry-pick')

    # Sync and drift detection
    drift_parser = subparsers.add_parser('drift', help='Detect drift between worktrees')
    drift_parser.add_argument('pair', nargs='?', help='Specific pair to check')

    sync_parser = subparsers.add_parser('sync', help='Synchronize worktrees')
    sync_parser.add_argument('pair', nargs='?', help='Specific pair to sync')
    sync_parser.add_argument('--auto-commit', action='store_true', help='Auto-commit changes')
    sync_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # Status and diff
    status_parser = subparsers.add_parser('status', help='Show combined status')
    status_parser.add_argument('--short', action='store_true', help='Short format')
    status_parser.add_argument('--verbose', action='store_true', help='Verbose format')

    diff_parser = subparsers.add_parser('diff', help='Show differences between worktrees')
    diff_parser.add_argument('--name-only', action='store_true', help='Show only file names')
    diff_parser.add_argument('--patch', action='store_true', help='Show patch')
    diff_parser.add_argument('paths', nargs='*', help='Paths to diff')

    # Pairing management
    pair_parser = subparsers.add_parser('pair', help='Manually link worktrees')
    pair_parser.add_argument('treeA', help='First worktree')
    pair_parser.add_argument('treeB', help='Second worktree')
    pair_parser.add_argument('--force', action='store_true', help='Force pairing')

    unpair_parser = subparsers.add_parser('unpair', help='Remove pairing')
    unpair_parser.add_argument('path', help='Path or alias to unpair')
    unpair_parser.add_argument('--keep-both', action='store_true', help='Keep both worktrees')

    doctor_parser = subparsers.add_parser('doctor', help='Diagnose issues')
    doctor_parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')

    restore_parser = subparsers.add_parser('restore', help='Restore worktree')
    restore_parser.add_argument('tree', help='Worktree to restore')
    restore_parser.add_argument('--from', dest='from_pair', help='Pair to restore from')

    # Advanced operations
    clone_parser = subparsers.add_parser('clone', help='Clone with paired worktrees')
    clone_parser.add_argument('url', help='Repository URL')
    clone_parser.add_argument('directory', nargs='?', help='Target directory')
    clone_parser.add_argument('--branch', help='Branch to checkout')
    clone_parser.add_argument('--no-local', action='store_true', help='Do not create local pair')

    logs_parser = subparsers.add_parser('logs', help='Show commit logs')
    logs_parser.add_argument('--graph', action='store_true', help='Show graph')
    logs_parser.add_argument('--since', help='Show commits since date')
    logs_parser.add_argument('--until', help='Show commits until date')

    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--get', help='Get configuration value')
    config_parser.add_argument('--set', nargs=2, metavar=('KEY', 'VALUE'), help='Set configuration value')
    config_parser.add_argument('--list', action='store_true', help='List all configuration')

    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    if args is None:
        args = sys.argv[1:]

    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    try:
        repo = DDWorktreeRepo()

        # Dispatch to appropriate command handler
        command_args = sys.argv[2:]  # Skip 'ddworktree'
        if parsed_args.command == 'worktree':
            return handle_worktree_command(repo, parsed_args)
        elif parsed_args.command == 'add':
            from .commands.add import add_files
            # Parse add-specific args
            add_files_list = []
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    add_files_list.append(command_args[i])
                    i += 1
            return add_files(repo, add_files_list if add_files_list else ['.'], verbose_flag)
        elif parsed_args.command == 'commit':
            from .commands.commit import commit_changes
            # Parse commit-specific args
            message = None
            amend_flag = False
            split_flag = False
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] == '-m':
                    if i + 1 < len(command_args):
                        message = command_args[i + 1]
                        i += 2
                    else:
                        i += 1
                elif command_args[i] == '--amend':
                    amend_flag = True
                    i += 1
                elif command_args[i] == '--split':
                    split_flag = True
                    i += 1
                elif command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    i += 1
            if not message:
                print("Error: commit message is required (use -m \"message\")", file=sys.stderr)
                return 1
            return commit_changes(repo, message, amend_flag, split_flag, verbose_flag)
        elif parsed_args.command == 'reset':
            from .commands.reset import reset_worktrees
            # Parse reset-specific args
            commitish = None
            hard_flag = False
            soft_flag = False
            keep_local_flag = False
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] == '--hard':
                    hard_flag = True
                    i += 1
                elif command_args[i] == '--soft':
                    soft_flag = True
                    i += 1
                elif command_args[i] == '--keep-local':
                    keep_local_flag = True
                    i += 1
                elif command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    commitish = command_args[i]
                    i += 1
            return reset_worktrees(repo, commitish, hard_flag, soft_flag, keep_local_flag, verbose_flag)
        elif parsed_args.command == 'rm':
            from .commands.rm import remove_files
            # Parse rm-specific args
            files_list = []
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    files_list.append(command_args[i])
                    i += 1
            if not files_list:
                print("Error: at least one file must be specified", file=sys.stderr)
                return 1
            return remove_files(repo, files_list, verbose_flag)
        elif parsed_args.command == 'mv':
            from .commands.mv import move_files
            # Parse mv-specific args
            source = None
            destination = None
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    if source is None:
                        source = command_args[i]
                    elif destination is None:
                        destination = command_args[i]
                    else:
                        print("Error: too many arguments", file=sys.stderr)
                        return 1
                    i += 1
            if not source or not destination:
                print("Error: source and destination must be specified", file=sys.stderr)
                return 1
            return move_files(repo, source, destination, verbose_flag)
        elif parsed_args.command == 'fetch':
            from .commands.fetch import fetch_updates
            # Parse fetch-specific args
            all_flag = False
            prune_flag = False
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] == '--all':
                    all_flag = True
                    i += 1
                elif command_args[i] == '--prune':
                    prune_flag = True
                    i += 1
                elif command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    i += 1
            return fetch_updates(repo, all_flag, prune_flag, verbose_flag)
        elif parsed_args.command == 'pull':
            from .commands.pull import pull_updates
            # Parse pull-specific args
            remote = None
            branch = None
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    if remote is None:
                        remote = command_args[i]
                    elif branch is None:
                        branch = command_args[i]
                    else:
                        print("Error: too many arguments", file=sys.stderr)
                        return 1
                    i += 1
            return pull_updates(repo, remote, branch, verbose_flag)
        elif parsed_args.command == 'push':
            from .commands.push import push_commits
            # Parse push-specific args
            include_local_flag = False
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] == '--include-local':
                    include_local_flag = True
                    i += 1
                elif command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    i += 1
            return push_commits(repo, include_local_flag, verbose_flag)
        elif parsed_args.command == 'merge':
            from .commands.merge import merge_branch
            # Parse merge-specific args
            branch = None
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    if branch is None:
                        branch = command_args[i]
                    else:
                        print("Error: too many arguments", file=sys.stderr)
                        return 1
                    i += 1
            if not branch:
                print("Error: branch must be specified", file=sys.stderr)
                return 1
            return merge_branch(repo, branch, verbose_flag)
        elif parsed_args.command == 'rebase':
            from .commands.rebase import rebase_worktrees
            # Parse rebase-specific args
            branch = None
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    if branch is None:
                        branch = command_args[i]
                    else:
                        print("Error: too many arguments", file=sys.stderr)
                        return 1
                    i += 1
            if not branch:
                print("Error: branch must be specified", file=sys.stderr)
                return 1
            return rebase_worktrees(repo, branch, verbose_flag)
        elif parsed_args.command == 'cherry-pick':
            from .commands.cherry_pick import cherry_pick_commit
            # Parse cherry-pick-specific args
            commit = None
            verbose_flag = parsed_args.verbose
            i = 0
            while i < len(command_args):
                if command_args[i] in ['-v', '--verbose']:
                    i += 1
                elif command_args[i].startswith('-'):
                    i += 1
                    if i < len(command_args) and not command_args[i].startswith('-'):
                        i += 1
                else:
                    if commit is None:
                        commit = command_args[i]
                    else:
                        print("Error: too many arguments", file=sys.stderr)
                        return 1
                    i += 1
            if not commit:
                print("Error: commit must be specified", file=sys.stderr)
                return 1
            return cherry_pick_commit(repo, commit, verbose_flag)
        else:
            print(f"Command '{parsed_args.command}' not yet implemented")
            return 1

    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def handle_worktree_command(repo: DDWorktreeRepo, args) -> int:
    """Handle worktree subcommands."""
    if args.worktree_command == 'add':
        return handle_worktree_add(repo, args)
    elif args.worktree_command == 'list':
        return handle_worktree_list(repo, args)
    elif args.worktree_command == 'remove':
        return handle_worktree_remove(repo, args)
    else:
        print(f"Worktree command '{args.worktree_command}' not yet implemented")
        return 1


def handle_worktree_add(repo: DDWorktreeRepo, args) -> int:
    """Handle worktree add command."""
    path = Path(args.path).resolve()
    commitish = args.commitish

    # Check if path already exists
    if path.exists():
        print(f"Error: Path {path} already exists")
        return 1

    # Get local suffix
    local_suffix = repo.get_local_suffix()
    local_path = Path(str(path) + local_suffix)

    # Create main worktree
    try:
        print(f"Creating main worktree at {path}")
        repo.create_worktree(str(path), commitish)

        if not args.no_local:
            # Create local worktree
            print(f"Creating local worktree at {local_path}")
            repo.create_worktree(str(local_path), commitish)

            # Create .gitignore-local in local worktree
            repo.create_local_gitignore(str(local_path))

            # Add pair to configuration
            pair_name = path.name
            repo.add_pair(pair_name, str(path), str(local_path))
            print(f"Added pair '{pair_name}': {path} <-> {local_path}")

        print("Worktree(s) created successfully")
        return 0

    except DDWorktreeError as e:
        print(f"Error creating worktree: {e}")
        # Clean up if partially created
        if path.exists():
            repo.remove_worktree(str(path), force=True)
        if local_path.exists():
            repo.remove_worktree(str(local_path), force=True)
        return 1


def handle_worktree_list(repo: DDWorktreeRepo, args) -> int:
    """Handle worktree list command."""
    pairs = repo.get_pairs()
    worktrees = repo.get_worktrees()

    print("ddworktree pairs:")
    print("-" * 60)

    if not pairs:
        print("No paired worktrees found")
        return 0

    for pair_name, (main_path, local_path) in pairs.items():
        main_exists = Path(main_path).exists() and repo.is_valid_worktree(main_path)
        local_exists = Path(local_path).exists() and repo.is_valid_worktree(local_path)

        status = "✅" if main_exists and local_exists else "⚠️"
        print(f"{status} {pair_name}:")
        print(f"   Main:  {main_path} {'✅' if main_exists else '❌'}")
        print(f"   Local: {local_path} {'✅' if local_exists else '❌'}")

        # Check for drift
        if main_exists and local_exists:
            try:
                from ..utils.diff import detect_drift
                drift = detect_drift(Path(main_path), Path(local_path))
                if drift.commit_drift or drift.added_files or drift.deleted_files or drift.modified_files:
                    print(f"   Status: 🔄 Drift detected")
                else:
                    print(f"   Status: ✅ In sync")
            except Exception as e:
                print(f"   Status: ❌ Error checking drift: {e}")

    return 0


def handle_worktree_remove(repo: DDWorktreeRepo, args) -> int:
    """Handle worktree remove command."""
    path = args.path

    # Find the pair
    pairs = repo.get_pairs()
    pair_to_remove = None

    # Check if path is a pair name
    if path in pairs:
        pair_to_remove = path
        main_path, local_path = pairs[path]
    else:
        # Check if path matches any worktree path
        for pair_name, (main, local) in pairs.items():
            if path == main or path == local:
                pair_to_remove = pair_name
                main_path, local_path = main, local
                break

    if not pair_to_remove:
        print(f"Error: No paired worktree found for '{path}'")
        return 1

    # Confirm removal
    print(f"Removing pair '{pair_to_remove}':")
    print(f"  Main:  {main_path}")
    print(f"  Local: {local_path}")

    if not args.dry_run:
        try:
            # Remove worktrees
            if Path(main_path).exists():
                repo.remove_worktree(main_path, force=True)
                print(f"Removed main worktree: {main_path}")

            if not args.keep_local and Path(local_path).exists():
                repo.remove_worktree(local_path, force=True)
                print(f"Removed local worktree: {local_path}")

            # Remove from configuration
            repo.remove_pair(pair_to_remove)
            print(f"Removed pair configuration: {pair_to_remove}")

            print("Worktree pair removed successfully")
            return 0

        except DDWorktreeError as e:
            print(f"Error removing worktree: {e}")
            return 1
    else:
        print("Dry run - no changes made")
        return 0


if __name__ == '__main__':
    sys.exit(main())