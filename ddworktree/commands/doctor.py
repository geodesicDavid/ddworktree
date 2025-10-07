"""
Command for diagnosing and repairing pairing issues in ddworktree.
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from ddworktree.core import DDWorktreeRepo, DDWorktreeError
from ddworktree.utils.diff import detect_drift


def doctor_command(
    repo: DDWorktreeRepo,
    fix: bool = False,
    verbose: bool = False
) -> int:
    """Diagnose and report pairing issues."""
    try:
        if verbose:
            print("🔍 Running ddworktree diagnostics...")

        issues_found = 0
        fixes_applied = 0

        # Check 1: Repository health
        if verbose:
            print("\n📁 Checking repository health...")
        repo_issues = _check_repository_health(repo, verbose)
        issues_found += len(repo_issues)

        # Check 2: Configuration integrity
        if verbose:
            print("\n⚙️  Checking configuration integrity...")
        config_issues = _check_configuration_integrity(repo, verbose)
        issues_found += len(config_issues)

        # Check 3: Worktree existence and validity
        if verbose:
            print("\n🌳 Checking worktree existence and validity...")
        worktree_issues = _check_worktree_health(repo, verbose)
        issues_found += len(worktree_issues)

        # Check 4: Pair synchronization
        if verbose:
            print("\n🔄 Checking pair synchronization...")
        sync_issues = _check_pair_synchronization(repo, verbose)
        issues_found += len(sync_issues)

        # Generate report
        print(f"\n📊 Diagnostic Report:")
        print(f"  Total issues found: {issues_found}")

        if issues_found == 0:
            print("  ✅ All checks passed - your ddworktree setup is healthy!")
            return 0

        # Show issues by category
        all_issues = repo_issues + config_issues + worktree_issues + sync_issues
        print(f"\n📋 Issues found:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")

        # Attempt fixes if requested
        if fix:
            if verbose:
                print(f"\n🔧 Attempting to fix issues...")
            fixes = _attempt_fixes(repo, all_issues, verbose)
            fixes_applied = len(fixes)

            if fixes_applied > 0:
                print(f"\n✅ Applied {fixes_applied} fixes")
            else:
                print(f"\n⚠️  No automatic fixes available")

        # Provide recommendations
        print(f"\n💡 Recommendations:")
        for issue in all_issues:
            recommendation = _get_recommendation(issue)
            if recommendation:
                print(f"  • {recommendation}")

        return issues_found - fixes_applied

    except Exception as e:
        print(f"Error running diagnostics: {e}")
        return 1


def _check_repository_health(repo: DDWorktreeRepo, verbose: bool) -> List[str]:
    """Check the health of the main Git repository."""
    issues = []

    # Check if .git directory exists
    git_dir = repo.repo_path / '.git'
    if not git_dir.exists():
        issues.append("Main repository .git directory missing")
        return issues

    # Check if HEAD exists
    head_file = git_dir / 'HEAD'
    if not head_file.exists():
        issues.append("Repository HEAD file missing")
        return issues

    # Check for common git directories
    required_dirs = ['objects', 'refs', 'hooks']
    for dir_name in required_dirs:
        if not (git_dir / dir_name).exists():
            issues.append(f"Required git directory missing: {dir_name}")

    # Check if repository has any commits
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', '--all'],
            cwd=repo.repo_path,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            commit_count = int(result.stdout.strip())
            if commit_count == 0:
                issues.append("Repository has no commits")
    except Exception:
        issues.append("Cannot check commit count")

    return issues


def _check_configuration_integrity(repo: DDWorktreeRepo, verbose: bool) -> List[str]:
    """Check the integrity of the .ddconfig file."""
    issues = []

    config_file = repo.config_file

    if not config_file.exists():
        issues.append("Configuration file .ddconfig missing")
        return issues

    # Try to parse the configuration
    try:
        config = repo.load_config()

        # Check basic structure
        if 'pairs' not in config:
            issues.append("Configuration missing 'pairs' section")
        elif not isinstance(config['pairs'], dict):
            issues.append("Configuration 'pairs' section is not a dictionary")

        # Check each pair
        if 'pairs' in config and isinstance(config['pairs'], dict):
            for pair_name, pair_value in config['pairs'].items():
                if not isinstance(pair_value, str):
                    issues.append(f"Pair '{pair_name}' value is not a string")
                    continue

                # Parse pair value
                parts = [p.strip() for p in pair_value.split(',')]
                if len(parts) != 2:
                    issues.append(f"Pair '{pair_name}' has invalid format: expected 'main, local'")
                    continue

                main_path, local_path = parts

                # Check if paths are relative or absolute
                if not (Path(main_path).is_absolute() or main_path.startswith('./')):
                    issues.append(f"Pair '{pair_name}' main path should be absolute or start with './'")

                if not (Path(local_path).is_absolute() or local_path.startswith('./')):
                    issues.append(f"Pair '{pair_name}' local path should be absolute or start with './'")

    except Exception as e:
        issues.append(f"Cannot parse configuration file: {e}")

    return issues


def _check_worktree_health(repo: DDWorktreeRepo, verbose: bool) -> List[str]:
    """Check the health of configured worktrees."""
    issues = []

    pairs = repo.get_pairs()

    for pair_name, (main_path, local_path) in pairs.items():
        main_exists = Path(main_path).exists()
        local_exists = Path(local_path).exists()

        if not main_exists:
            issues.append(f"Pair '{pair_name}': main worktree missing: {main_path}")

        if not local_exists:
            issues.append(f"Pair '{pair_name}': local worktree missing: {local_path}")

        # Check if worktrees are valid Git worktrees
        if main_exists and not _is_valid_worktree(Path(main_path)):
            issues.append(f"Pair '{pair_name}': main worktree is not valid: {main_path}")

        if local_exists and not _is_valid_worktree(Path(local_path)):
            issues.append(f"Pair '{pair_name}': local worktree is not valid: {local_path}")

    return issues


def _check_pair_synchronization(repo: DDWorktreeRepo, verbose: bool) -> List[str]:
    """Check synchronization between paired worktrees."""
    issues = []

    pairs = repo.get_pairs()

    for pair_name, (main_path, local_path) in pairs.items():
        main_exists = Path(main_path).exists()
        local_exists = Path(local_path).exists()

        if main_exists and local_exists:
            try:
                drift = detect_drift(Path(main_path), Path(local_path))

                if drift.commit_drift:
                    issues.append(f"Pair '{pair_name}': commit drift detected")

                total_files = len(drift.added_files) + len(drift.deleted_files) + len(drift.modified_files)
                if total_files > 0:
                    issues.append(f"Pair '{pair_name}': {total_files} files differ between worktrees")

            except Exception as e:
                issues.append(f"Pair '{pair_name}': cannot check synchronization: {e}")

    return issues


def _is_valid_worktree(path: Path) -> bool:
    """Check if a path is a valid Git worktree."""
    try:
        git_file = path / '.git'
        git_dir = path / '.git'

        if git_file.exists():
            with open(git_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('gitdir: '):
                    git_dir = Path(content[8:])
                    return (git_dir / 'HEAD').exists()
        elif git_dir.exists():
            return (git_dir / 'HEAD').exists()

        return False

    except Exception:
        return False


def _attempt_fixes(repo: DDWorktreeRepo, issues: List[str], verbose: bool) -> List[str]:
    """Attempt to automatically fix issues."""
    fixes = []

    for issue in issues:
        if "Configuration file .ddconfig missing" in issue:
            # Create empty config file
            repo.save_config({'pairs': {}, 'options': {}})
            fixes.append("Created missing .ddconfig file")

        elif "local worktree missing" in issue and not issue.startswith("Pair"):
            # Try to create missing local worktree
            # This is complex and risky, so skip for now
            continue

        # Add more automatic fixes as needed

    return fixes


def _get_recommendation(issue: str) -> str:
    """Get a recommendation for fixing an issue."""
    if "Configuration file .ddconfig missing" in issue:
        return "Run 'ddworktree config --set pairs {}' to initialize configuration"
    elif "main worktree missing" in issue:
        return "Check if the worktree was moved or deleted, or recreate it with 'ddworktree worktree add'"
    elif "local worktree missing" in issue:
        return "Recreate local worktree with 'ddworktree worktree add' or restore from main with 'ddworktree restore'"
    elif "commit drift detected" in issue:
        return "Run 'ddworktree sync' to synchronize worktrees"
    elif "files differ between worktrees" in issue:
        return "Run 'ddworktree sync' to synchronize files"
    elif "not a valid Git worktree" in issue:
        return "Check if the directory is a proper Git worktree or repository"
    elif "Repository has no commits" in issue:
        return "Make an initial commit in the repository"
    else:
        return "Review the issue and manually fix if necessary"


def main(args: List[str]) -> int:
    """Main entry point for doctor command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree doctor',
        description='Diagnose and repair pairing issues'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix issues automatically'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed output'
    )

    parsed_args = parser.parse_args(args)

    try:
        repo = DDWorktreeRepo()
        return doctor_command(repo, parsed_args.fix, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())