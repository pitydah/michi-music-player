# Core Services Convergence Architecture

## Overview

Four previously independent service cores (Radio, Lyrics, Metadata, Michi AI) converged onto a single QML runtime architecture. Each service exposes typed contracts consumed by thin bridges.

## Architecture

```
QML runtime (qml_main.py)
  → BridgeFactory
    → MetadataBridge (thin)
    → LyricsBridge (thin)
    → RadioBridge (thin)
    → MichiAIBridge (thin)
  → ServiceContainer
    → MetadataService
    → LyricsService
    → RadioService
    → AssistantCoreService
    → ConfirmationService
    → JobService
```

## Service Registration

| Service | Priority | Status |
|---------|----------|--------|
| metadata_service | REQUIRED | Active |
| lyrics_service | OPTIONAL | Active |
| radio_service | OPTIONAL | Active |
| assistant_core_service | OPTIONAL | Active |
| confirmation_service | OPTIONAL | Active |

## Source Branches

| Service | Branch | SHA |
|---------|--------|-----|
| Radio Core V2 | feature/radio-core-v2 | c73c76a |
| Lyrics Core V2 | feature/lyrics-core-v2 | 2b2f2bc |
| Metadata Core V2 | integration/metadata-core-v2 | 004a189 |
| Michi AI Core V2 | feature/michi-ai-core-v2 | 0f2a095 |
| Michi AI Integration | integration/michi-ai-core-v2 | 033d9cb |
