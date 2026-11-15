"""Allow ``python -m trading_scanner`` as a shortcut for the terminal runner."""

import sys

from trading_scanner.cli import main

sys.exit(main())
