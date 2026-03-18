"""Root launcher for Phoring backend.

Allows running `python run.py` from repository root without failing.
"""

from backend.run import main


if __name__ == "__main__":
    main()
