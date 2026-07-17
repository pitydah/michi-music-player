"""Sync-specific exceptions."""
class SyncError(Exception): pass
class SyncConnectionError(SyncError): pass
class SyncTransferError(SyncError): pass
