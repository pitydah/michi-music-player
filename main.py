#!/usr/bin/python3
"""Michi Music Player — delegates to michi.app_launcher.launch()."""

import sys
from michi.app_launcher import launch

if __name__ == "__main__":
    sys.exit(launch())
