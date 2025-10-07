"""
Entry point for running ddworktree as a module.
"""

from .cli import main

if __name__ == '__main__':
    import sys
    sys.exit(main())