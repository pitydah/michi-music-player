# QML Async Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      QML Layer                          │
│  Main.qml → Pages → {trackModel, albumModel, ...}      │
└──────────────────────┬──────────────────────────────────┘
                       │ Qt Context Property
┌──────────────────────▼──────────────────────────────────┐
│                   Bridge Layer                           │
│  LibraryBridge  QueueBridge  HistoryBridge               │
│  PlaylistsBridge  RadioBridge  LyricsBridge  MixBridge   │
│  HomeBridge  JobBridge  SmartTaggingBridge               │
│  LibrarySourcesBridge  ActionRegistryBinder              │
└──────────────────────┬──────────────────────────────────┘
                       │ Python method calls
┌──────────────────────▼──────────────────────────────────┐
│                 Service Layer                            │
│  LibraryQueryService  LibrarySourcesService              │
│  TrackActionService  ScannerJobAdapter                   │
│  MetadataBatchAdapter  LibraryDoctorAdapter              │
│  PlayerService  RadioManager  LrclibClient              │
└──────────────────────┬──────────────────────────────────┘
                       │ WorkerManager.run_task()
┌──────────────────────▼──────────────────────────────────┐
│               WorkerManager (QThreadPool)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ TaskWorker  │  │ TaskWorker  │  │ TaskWorker  │     │
│  │ (QRunnable) │  │ (QRunnable) │  │ (QRunnable) │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│  ┌──────▼────────────────▼────────────────▼──────┐     │
│  │           QThreadPool (max 4 threads)         │     │
│  └───────────────────────────────────────────────┘     │
│         │                                                │
│         │ done_callback (via task_done signal)           │
│         ▼                                                │
│  QueryExecutor → success/failure signals                │
│       → BasePagedListModel callbacks (main thread)      │
└──────────────────────────────────────────────────────────┘
```

## Cancellation flow

```
QML → Bridge.cancel()
  → QueryExecutor.cancel(request_id)
    → WorkerManager.cancel_task(task_id)
      → CancellationToken.request_cancel()
        → TaskWorker checks token between operations
          → CancelledError raised → worker exits
            → No callback emitted
```

## Database thread safety

```
LibraryConnectionFactory
  └── threading.local
       └── sqlite3.connect(uri?mode=ro, uri=True)
            └── PRAGMA query_only = 1
                 └── PRAGMA busy_timeout = 5000

Each thread opens its own read-only connection via URI mode.
WAL mode allows concurrent readers.
Main thread connection is read-write for mutations.
```

## Stale result protection

```
1. QueryExecutor.submit(owner, fn, supersede=True)
2. Owner generation incremented
3. Previous request for same owner cancelled
4. Callback checks generation before modifying model
5. If generation mismatch → callback dropped silently
6. Model loading flags reset if stale detected
```
