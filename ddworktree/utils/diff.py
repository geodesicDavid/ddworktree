"""
Utilities for detecting drift and comparing worktrees.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class WorktreeDiff:
    """Represents differences between two worktrees."""
    added_files: List[str]
    deleted_files: List[str]
    modified_files: List[str]
    commit_drift: bool
    main_commit: Optional[str]
    local_commit: Optional[str]


def get_commit_hash(directory: Path) -> Optional[str]:
    """Get the current commit hash for a directory."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=directory,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def compare_commits(main_dir: Path, local_dir: Path) -> Tuple[bool, Optional[str], Optional[str]]:
    """Compare commit hashes between two worktrees."""
    main_commit = get_commit_hash(main_dir)
    local_commit = get_commit_hash(local_dir)

    has_drift = main_commit != local_commit
    return has_drift, main_commit, local_commit


def get_file_differences(main_dir: Path, local_dir: Path) -> Tuple[List[str], List[str], List[str]]:
    """Get file differences between two directories."""
    import os

    def get_files_recursive(directory: Path) -> Dict[str, str]:
        files = {}
        for root, dirs, filenames in os.walk(directory):
            if '.git' in dirs:
                dirs.remove('.git')
            for filename in filenames:
                filepath = Path(root) / filename
                relative_path = filepath.relative_to(directory)
                files[str(relative_path)] = str(filepath)
        return files

    main_files = get_files_recursive(main_dir)
    local_files = get_files_recursive(local_dir)

    main_set = set(main_files.keys())
    local_set = set(local_files.keys())

    added_files = list(local_set - main_set)
    deleted_files = list(main_set - local_set)
    common_files = main_set & local_set

    modified_files = []
    for file_path in common_files:
        # Compare file contents
        try:
            with open(main_files[file_path], 'r') as f1, open(local_files[file_path], 'r') as f2:
                if f1.read() != f2.read():
                    modified_files.append(file_path)
        except (OSError, UnicodeDecodeError):
            # Binary files or read errors - consider them different
            modified_files.append(file_path)

    return added_files, deleted_files, modified_files


def detect_drift(main_dir: Path, local_dir: Path) -> WorktreeDiff:
    """Detect drift between two worktrees."""
    # Check commit alignment
    has_commit_drift, main_commit, local_commit = compare_commits(main_dir, local_dir)

    # Check file differences
    added_files, deleted_files, modified_files = get_file_differences(main_dir, local_dir)

    return WorktreeDiff(
        added_files=added_files,
        deleted_files=deleted_files,
        modified_files=modified_files,
        commit_drift=has_commit_drift,
        main_commit=main_commit,
        local_commit=local_commit
    )


def sync_files(source_dir: Path, target_dir: Path, files_to_sync: List[str], dry_run: bool = False) -> List[str]:
    """Sync files from source to target directory."""
    import shutil

    synced_files = []

    for file_path in files_to_sync:
        source_file = source_dir / file_path
        target_file = target_dir / file_path

        if not source_file.exists():
            continue

        # Create target directory if it doesn't exist
        target_file.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            synced_files.append(f"Would copy: {file_path}")
        else:
            try:
                shutil.copy2(source_file, target_file)
                synced_files.append(f"Copied: {file_path}")
            except (OSError, shutil.Error) as e:
                synced_files.append(f"Failed to copy {file_path}: {e}")

    return synced_files


def generate_diff_report(drift: WorktreeDiff) -> str:
    """Generate a human-readable diff report."""
    report = []

    if drift.commit_drift:
        report.append("🔄 Commit drift detected:")
        if drift.main_commit:
            report.append(f"  Main: {drift.main_commit[:8]}")
        if drift.local_commit:
            report.append(f"  Local: {drift.local_commit[:8]}")
        report.append("")

    if drift.added_files:
        report.append("➕ Files added in local:")
        for file in sorted(drift.added_files):
            report.append(f"  {file}")
        report.append("")

    if drift.deleted_files:
        report.append("➖ Files deleted in local:")
        for file in sorted(drift.deleted_files):
            report.append(f"  {file}")
        report.append("")

    if drift.modified_files:
        report.append("✏️  Files modified:")
        for file in sorted(drift.modified_files):
            report.append(f"  {file}")
        report.append("")

    if not any([drift.commit_drift, drift.added_files, drift.deleted_files, drift.modified_files]):
        report.append("✅ No drift detected - worktrees are in sync")

    return '\n'.join(report)