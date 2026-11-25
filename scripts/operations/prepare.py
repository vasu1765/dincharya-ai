"""Owner-local prepare entry point. Run as a module from the exact checkout."""
import sys
from scripts.operations.session import main

if __name__ == "__main__":
    try:
        main(["prepare", *sys.argv[1:]])
    except Exception as exc:
        raise SystemExit("Private session check failed ("+type(exc).__name__+")") from None
