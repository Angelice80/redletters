# Sprint 3: Red Letters Desktop GUI MVP

## Overview

This document describes the minimal cross-platform desktop GUI for Red Letters, built with Tauri + React. It provides a functional harness for real socket-level integration with the Engine Spine.

**Platforms**: Windows 10/11, macOS

## Directory Structure

```
gui/
├── src-tauri/                    # Rust/Tauri backend
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.rs
│   │   └── commands/
│   │       ├── mod.rs
│   │       ├── auth.rs           # Keychain access
│   │       └── engine.rs         # Engine process management
├── src/                          # React frontend
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts             # HTTP client with Bearer auth
│   │   └── types.ts              # TypeScript types
│   ├── hooks/
│   │   ├── useEngineStatus.ts
│   │   ├── useEventStream.ts     # fetch() streaming with manual SSE parsing
│   │   └── useJobs.ts
│   ├── store/
│   │   └── index.ts              # Zustand store
│   ├── screens/
│   │   ├── Dashboard.tsx
│   │   ├── Jobs.tsx
│   │   ├── JobDetail.tsx
│   │   ├── Diagnostics.tsx
│   │   └── Settings.tsx
│   └── components/
│       ├── StatusPill.tsx
│       ├── LogViewer.tsx
│       └── ReceiptViewer.tsx
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

## Prerequisites

1. **Node.js 18+** with npm
2. **Rust** with cargo (for Tauri)
3. **Engine Spine running** on port 47200

## Development Setup

### 1. Install Dependencies

```bash
cd gui
npm install
```

### 2. Set Up Auth Token

The GUI retrieves auth tokens from the OS keychain. Set one up:

```bash
# macOS - using security command
security add-generic-password -s "com.redletters.engine" -a "auth_token" -w "rl_your_token_here"

# Or create a file fallback
mkdir -p ~/.greek2english
echo "rl_your_token_here" > ~/.greek2english/.auth_token
chmod 600 ~/.greek2english/.auth_token
```

### 3. Start the Engine

In a separate terminal:

```bash
cd /Users/admin/myprojects/greek2english
redletters engine start --port 47200
```

### 4. Run the GUI in Development Mode

```bash
cd gui
npm run tauri:dev
```

This will:
- Start Vite dev server on port 1420
- Launch the Tauri app with hot-reload

## Build for Production

```bash
cd gui
npm run tauri:build
```

Builds will be output to `gui/src-tauri/target/release/bundle/`.

## API Integration

### Auth Token (ADR-005)

| Constant | Value |
|----------|-------|
| Service name | `com.redletters.engine` |
| Account | `auth_token` |
| Token prefix | `rl_` |
| Fallback path | `~/.greek2english/.auth_token` |

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/engine/status` | GET | Engine status |
| `/v1/stream` | GET | SSE event stream |
| `/v1/jobs` | POST | Create job |
| `/v1/jobs` | GET | List jobs |
| `/v1/jobs/{id}` | GET | Get job detail |
| `/v1/jobs/{id}/receipt` | GET | Get job receipt |
| `/v1/jobs/{id}/cancel` | POST | Cancel job |
| `/v1/diagnostics/export` | POST | Export diagnostics bundle |

### SSE Streaming

**Important**: The GUI uses `fetch()` with `ReadableStream` for SSE instead of `EventSource` because `EventSource` cannot send custom Authorization headers.

Event types:
- `engine.heartbeat` - Every 3 seconds
- `job.state_changed` - Job state transitions
- `job.progress` - Progress updates
- `job.log` - Log entries

Reconnection uses `Last-Event-ID` header for replay support.

## Screens

### Dashboard
- Connection status pill (Connected/Degraded/Disconnected)
- Engine version, mode, uptime
- Active jobs and queue depth
- Health status

### Jobs
- "Start Demo Job" button
- Job list with state, progress
- Click to view job details

### Job Detail
- Progress bar (when running)
- Live log viewer with pause/search
- Receipt viewer (when terminal state)

### Diagnostics
- Export bundle button
- Integrity report summary (OK/Warn/Fail/Skipped)
- Failure details

### Settings
- Engine port configuration
- Safe mode status and restart
- Integrity threshold setting
- Reconnection testing
- Reset engine data (with confirmation)

## Troubleshooting

### Connection Issues

1. **"Disconnected" status**
   - Verify engine is running: `curl http://127.0.0.1:47200/v1/engine/status`
   - Check port setting in Settings screen

2. **"No auth token found"**
   - Set token in keychain or create fallback file
   - Token must start with `rl_` and be at least 24 characters

3. **SSE not connecting**
   - Check browser console for CORS errors
   - Verify CSP allows connections to localhost

### Build Issues

1. **Rust compilation errors**
   - Ensure Rust is up to date: `rustup update`
   - Clean build: `cd src-tauri && cargo clean`

2. **npm dependency issues**
   - Clear cache: `rm -rf node_modules && npm install`

## Architecture Notes

### State Management

The app uses Zustand for state management:
- `connectionState` - SSE connection status
- `lastHeartbeat` - Timestamp of last heartbeat
- `jobs` - Map of job ID to job response
- `jobLogs` - Map of job ID to log entries
- `seenSequences` - Set for SSE deduplication
- `settings` - Persisted user settings

### Connection Health

Connection state is determined by heartbeat staleness:
- **Connected**: Heartbeat within 10 seconds
- **Degraded**: Heartbeat 10-30 seconds old
- **Disconnected**: Heartbeat >30 seconds old or no SSE connection

### Deduplication

SSE events are deduplicated by `sequence_number` using a Set stored in Zustand. This ensures idempotent event processing even during reconnection with replay.

## Sprint 4 TODOs

- [ ] Generate TypeScript types from OpenAPI spec
- [ ] Engine process management via Tauri (spawn, restart)
- [ ] Proper error boundary handling
- [ ] Keyboard shortcuts
- [ ] Dark/light theme toggle
