"""
Command for managing configuration in ddworktree.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from ddworktree.core import DDWorktreeRepo, DDWorktreeError


def manage_config(
    repo: DDWorktreeRepo,
    get_key: Optional[str] = None,
    set_value: Optional[List[str]] = None,
    list_config: bool = False,
    verbose: bool = False
) -> int:
    """Manage configuration options."""
    try:
        if verbose:
            print("Managing ddworktree configuration...")

        config = repo.load_config()

        if get_key:
            # Get a specific configuration value
            if get_key in config.get('options', {}):
                value = config['options'][get_key]
                print(f"{get_key} = {value}")
                return 0
            else:
                print(f"Configuration key '{get_key}' not found")
                return 1

        elif set_value:
            # Set a configuration value
            if len(set_value) != 2:
                print("Error: --set requires KEY and VALUE")
                return 1

            key, value = set_value

            # Convert string values to appropriate types
            converted_value = _convert_config_value(value)

            repo.set_option(key, converted_value)
            print(f"Set {key} = {converted_value}")
            return 0

        elif list_config:
            # List all configuration
            print("ddworktree configuration:")
            print("-" * 40)

            if not config.get('pairs') and not config.get('options'):
                print("  No configuration found")
                return 0

            # Show pairs
            if config.get('pairs'):
                print("\n[pairs]")
                for name, pair_value in config['pairs'].items():
                    print(f"{name} = {pair_value}")

            # Show options
            if config.get('options'):
                print("\n[options]")
                for key, value in config['options'].items():
                    print(f"{key} = {value}")

            # Show available configuration keys and descriptions
            print("\nAvailable configuration keys:")
            for key, desc in _get_config_descriptions().items():
                current_value = config.get('options', {}).get(key, 'not set')
                print(f"  {key} ({desc}) = {current_value}")

            return 0

        else:
            # Default behavior - show configuration summary
            print("ddworktree configuration summary:")
            print("-" * 40)

            pairs_count = len(config.get('pairs', {}))
            options_count = len(config.get('options', {}))

            print(f"  Configured pairs: {pairs_count}")
            print(f"  Configuration options: {options_count}")

            if pairs_count > 0:
                print(f"\nConfigured pairs:")
                for name in config['pairs'].keys():
                    print(f"  • {name}")

            if options_count > 0:
                print(f"\nConfiguration options:")
                for key, value in config['options'].items():
                    print(f"  • {key} = {value}")

            return 0

    except Exception as e:
        print(f"Error managing configuration: {e}")
        return 1


def _convert_config_value(value: str) -> Any:
    """Convert a string value to the appropriate type."""
    # Try boolean first
    if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
        return value.lower() in ['true', 'yes', '1']

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Keep as string
    return value


def _get_config_descriptions() -> Dict[str, str]:
    """Get descriptions for available configuration keys."""
    return {
        'local_suffix': 'Suffix for local worktree directories (default: "-local")',
        'auto_sync': 'Automatically sync changes between worktrees (true/false)',
        'push_local': 'Include local commits when pushing (true/false)',
        'default_branch': 'Default branch for new worktrees',
        'sync_on_commit': 'Automatically sync paired worktree after commit (true/false)',
        'verbose': 'Enable verbose output by default (true/false)',
        'dry_run_default': 'Default to dry-run mode for destructive operations (true/false)',
    }


def main(args: List[str]) -> int:
    """Main entry point for config command."""
    parser = argparse.ArgumentParser(
        prog='ddworktree config',
        description='Manage configuration'
    )
    parser.add_argument(
        '--get',
        help='Get configuration value'
    )
    parser.add_argument(
        '--set',
        nargs=2,
        metavar=('KEY', 'VALUE'),
        help='Set configuration value'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all configuration'
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
        return manage_config(
            repo,
            parsed_args.get,
            parsed_args.set,
            parsed_args.list,
            parsed_args.verbose
        )
    except DDWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())