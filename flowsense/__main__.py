"""Entry point for `python -m flowsense`."""
import sys

from .runner import main

if __name__ == "__main__":
    sys.exit(main())
