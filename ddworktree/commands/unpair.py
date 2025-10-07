"""
Command for removing pairing in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def unpair_worktrees(
    repo: DDWorktreeRepo,
    path: str,
    keep_both: bool = False,
    verbose: bool = False
) -> int:
    """Remove a pairing definition."""
    try:
        if verbose:
            print(f"Unpairing worktree: {path}")

        # Find the pair to remove
        pair_to_remove = None
        pairs = repo.get_pairs()

        # Check if path is a pair name
        if path in pairs:
            pair_to_remove = path
        else:
            # Check if path matches any worktree path
            search_path = Path(path).resolve()
            for pair_name, (main_path, local_path) in pairs.items():
                if search_path == Path(main_path) or search_path == Path(local_path):
                    pair_to_remove = pair_name
                    break

        if not pair_to_remove:
            print(f"Error: No paired worktree found for '{path}'")
            print("Available pairs:")
            for name, (main, local) in pairs.items():
                print(f"  {name}: {main} <-> {local}")
            return 1

        # Get pair details for confirmation
        main_path, local_path = pairs[pair_to_remove]

        if verbose:
            print(f"Found pair '{pair_to_remove}':")
            print(f"  Main:  {main_path}")
            print(f"  Local: {local_path}")

        # Check if worktrees still exist
        main_exists = Path(main_path).exists()
        local_exists = Path(local_path).exists()

        # Warn before removing if worktrees still exist
        if (main_exists or local_exists) and not keep_both:
            print("⚠️  Warning: One or both worktrees still exist:")
            if main_exists:
                print(f"  Main:  {main_path}")
            if local_exists:
                print(f"  Local: {local_path}")

            if not keep_both:
                print("Use --keep-both to keep the worktree directories")
                response = input("Continue with unpairing? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Unpairing cancelled")
                    return 0

        # Remove the pair from configuration
        repo.remove_pair(pair_to_remove)

        print(f"✅ Successfully removed pair '{pair_to_remove}'")

        # Offer to remove worktrees if they exist and --keep-both not specified
        if not keep_both and (main_exists or local_exists):
            print("\nWorktree directories still exist. Remove them?")
            response = input("Remove worktree directories? (y/N): ").strip().lower()

            if response in ['y', 'yes']:
                removed_count = 0
                if main_exists:
                    try:
                        import shutil
                        shutil.rmtree(main_path)
                        print(f"Removed main worktree: {main_path}")
                        removed_count += 1
                    except Exception as e:
                        print(f"Error removing main worktree: {e}")

                if local_exists:
                    try:
                        import shutil
                        shutil.rmtree(local_path)
                        print(f"Removed local worktree: {local_path}")
                        removed_count += 1
                    except Exception as e:
                        print(f"Error removing local worktree: {e}")

                if removed_count > 0:
                    print(f"\n✅ Removed {removed_count} worktree directories")

        return 0

    except Exception as e:
        print(f"Error unpairing worktrees: {e}")
        return 1


def main(args: List[str]) -> int:
    """Main entry point for unpair command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree unpair',
        description='Remove a pairing definition'
    )
    parser.add_argument(
        'path',
        help='Path or alias to unpair'
    )
    parser.add_argument(
        '--keep-both',
        action='store_true',
        help='Keep both worktree directories'
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
        return unpair_worktrees(repo, parsed_args.path, parsed_args.keep_both, parsed_args.verbose)
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())