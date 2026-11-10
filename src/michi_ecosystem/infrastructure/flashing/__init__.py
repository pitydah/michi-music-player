"""Flashing adapters: serial, esptool, manifests, preflight, provisioning.

All blocking work runs off the GUI thread; credentials never touch shell
arguments or logs (master plan §135–§142).
"""
