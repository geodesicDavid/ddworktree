"""
Utility modules for ddworktree.
"""

from .gitignore import (
    parse_gitignore,
    get_combined_gitignore_patterns,
    is_ignored_by_pattern,
    get_tracked_files,
    get_git_status
)

from .diff import (
    WorktreeDiff,
    get_commit_hash,
    compare_commits,
    get_file_differences,
    detect_drift,
    sync_files,
    generate_diff_report
)

__all__ = [
    # gitignore utilities
    'parse_gitignore',
    'get_combined_gitignore_patterns',
    'is_ignored_by_pattern',
    'get_tracked_files',
    'get_git_status',

    # diff utilities
    'WorktreeDiff',
    'get_commit_hash',
    'compare_commits',
    'get_file_differences',
    'detect_drift',
    'sync_files',
    'generate_diff_report'
]