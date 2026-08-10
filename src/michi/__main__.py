"""Entry point: python -m michi"""

import sys
from michi.bootstrap import ApplicationContainer


def main() -> int:
    container = ApplicationContainer()
    container.initialize()
    exit_code = container.run()
    container.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
