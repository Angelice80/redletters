# GUI Guide

The Red Letters desktop GUI provides a visual interface for translation,
variant analysis, export, and source management.

## Requirements

- Node.js 18+
- Rust toolchain (for Tauri desktop builds)
- Python backend running (`redletters engine start` for modern API, or `redletters serve` for legacy)

## Starting the GUI

### Quick Start (Recommended)

```bash
redletters gui
```

That's it. This starts the backend and opens the GUI in your browser.
Press Ctrl+C to stop everything.

For development with hot reload:

```bash
redletters gui --dev
```

### Manual Mode (Two Terminals)

If you prefer separate control:

```bash
# Terminal 1: Start the Python backend (Engine Spine)
redletters engine start --port 47200

# Terminal 2: Start the GUI
cd gui
npm install  # first time only
npm run dev
```

Open http://localhost:5173 in your browser.

> **Note:** The GUI requires the Engine Spine backend on port 47200. The legacy
> `redletters serve` command (port 8000) does not provide all GUI-required endpoints.

### Desktop Application

```bash
cd gui
npm run tauri:dev    # Development with hot reload
npm run tauri:build  # Build distributable app
```

---

## Screens (v0.14.0 - Task-Shaped Navigation)

### Dashboard

The home screen showing system status:

- **Backend status**: Connection health and version
- **Database health**: Migration status, integrity
- **Quick stats**: Installed packs, built variants, pending gates
- **Recent activity**: Last queries, exports, acknowledgements

### Explore / Passage Workspace (v0.15.0)

The main workspace for passage analysis with a 3-column layout:

**Layout:**
- **Left Panel**: Greek text (SBLGNT) with proper font styling
- **Center Panel**: Rendering cards with interactive tokens
- **Right Panel**: Inspector tabs (Receipts | Variants)

**Workflow:**

1. **Enter a reference** in the toolbar (e.g., "Matthew 5:3-12" or "John 1:1")

2. **Select options**:
   - **Mode**: Readable (flowing text) or Traceable (full evidence)
   - **Translator**: Literal, Fluent, or Traceable

3. **Explore the rendering**:
   - Click any token to see a mini receipt popover
   - View lemma, morphology, gloss, confidence breakdown
   - Click "View Full Ledger" to jump to Receipts tab

4. **Use feature toggles** (top-right toolbar):
   - **Compare**: Highlight differences between renderings (lexical/syntactic/interpretive)
   - **Heatmap**: Show low-confidence zones with subtle color coding

5. **Review variants** in the Variants tab:
   - Dossier panel with witness summaries
   - Acknowledgement status per variant

6. **View the full ledger** in Receipts tab (Traceable mode):
   - Token-by-token analysis with confidence bars
   - Provenance badges showing sources

**Compare Mode Legend:**
- Blue: Lexical changes (different gloss/source)
- Purple: Syntactic changes (structure differences)
- Orange: Interpretive changes (contextual reasoning)

**Heatmap Mode:**
- No highlight: High confidence (>80%)
- Yellow: Medium confidence (60-80%)
- Orange: Low confidence (40-60%)
- Red: Very low confidence (<40%)

### Export (NEW in v0.14.0)

Create verified scholarly exports with gate enforcement:

#### Export Wizard

The Export screen uses a step-by-step wizard:

1. **Step 1: Enter Reference**
   - Specify the passage to export (e.g., "John 1:1-18")
   - Choose mode (Traceable recommended for scholarly work)
   - Select export type (Bundle, Quote, Apparatus, Snapshot)

2. **Step 2: Gate Detection**
   - Wizard automatically checks for pending variant acknowledgements
   - Displays any variants requiring attention
   - Options: Acknowledge variants OR Force export

3. **Step 3: Acknowledge** (if gates detected)
   - Opens variant acknowledgement screen
   - Review side-by-side readings with manuscript evidence
   - Select preferred readings

4. **Step 4: Run Scholarly Export**
   - Confirms settings before execution
   - Triggers full scholarly workflow:
     - Generate/verify lockfile
     - Build apparatus
     - Generate translation
     - Export citations
     - Create snapshot
     - Verify bundle integrity
     - Write run_log.json

#### Scholarly Run Output

A successful scholarly run produces:

| File | Purpose |
|------|---------|
| `lockfile.json` | Reproducible environment specification |
| `apparatus.jsonl` | Textual variant apparatus |
| `translation.jsonl` | Token-level translation data |
| `citations.json` | Source citations with provenance |
| `quote.json` | Quotable translation with gate status |
| `snapshot.json` | Combined export with file hashes |
| `bundle/` | Verified bundle directory |
| `run_log.json` | Deterministic execution log |

#### Force Export (Use with Caution)

If you need to export without acknowledging all gates:

1. Click "Force Export (Not Recommended)"
2. Confirm understanding that responsibility will be recorded
3. The run_log.json will contain a `forced_responsibility` field

### Sources

Manage your data sources:

- **View installed packs**: See which sources are installed and their versions
- **Install new sources**: Click "Install" next to available packs
- **Check for updates**: Compare installed versions against catalog
- **Generate lockfile**: Create reproducible environment specification

**Mode Distinction:**
- Sources screen clearly shows Demo vs Scholarly mode status
- License requirements displayed before installation
- EULA acceptance prompts for restricted sources

### Jobs

Monitor long-running operations:

- View job queue and execution history
- See progress on scholarly runs and variant building
- Check export status
- Cancel running jobs
- Access job receipts with output paths

### Settings

Configure the application:

- **Engine Port**: Backend server port (default: 47200)
- **Integrity Threshold**: Size limit for full file hashing
- **Session ID**: Unique identifier for acknowledgement tracking
- **Reconnect**: Test and re-establish backend connection

---

## Bootstrap Wizard (NEW in v0.16.0)

On first run, a bootstrap wizard guides you through setup:

1. **Welcome** - Introduction to Red Letters
2. **Backend Connection** - Verify engine connectivity and version
3. **Install Spine** - Install required MorphGNT/SBLGNT text source
4. **Test Translation** - Verify setup with John 1:1 translation
5. **Complete** - Ready to explore

The wizard can be skipped and re-triggered from Settings if needed.

---

## Actionable Error Diagnostics (NEW in v0.16.0)

When API calls fail, the GUI now shows structured error panels with:

- **Request details**: Method + URL (e.g., `POST /translate`)
- **Status code**: HTTP status and error code from backend
- **Response snippet**: Relevant portion of the error response
- **Suggested fix**: Actionable guidance based on error type

Error categories with specific guidance:
- **Network Error**: Check if backend is running
- **Authentication Error (401)**: Token may be invalid or expired
- **Not Found (404)**: Endpoint doesn't exist on this backend version
- **Service Unavailable (503)**: Backend not fully initialized

Errors include a "Copy Diagnostics" button for easy bug reporting.

---

## Connection Panel

When the GUI cannot reach the backend, a connection panel appears:

1. **Check the port**: Ensure port matches running backend (default: 47200)
2. **Click "Check Health"**: Test connectivity to backend
3. **Quick Fix Steps**:
   - Start backend: `redletters engine start --port 47200`
   - Verify: `curl http://127.0.0.1:47200/v1/engine/status`
   - Check firewall settings

The GUI auto-detects localhost:47200 and will reconnect automatically
when the backend becomes available.

---

## SSE Connection Badge (NEW in v0.19.0)

The GUI now shows a persistent SSE connection health badge in the header:

### Connection States

| State | Badge Color | Meaning |
|-------|-------------|---------|
| **Connected** | Green | SSE stream active, receiving events |
| **Reconnecting...** | Yellow (pulsing) | Connection lost, attempting to reconnect |
| **Disconnected** | Red | No SSE connection |

### Badge Features

- Click badge to expand diagnostics tooltip
- Tooltip shows: Base URL, Last Event ID, Last Message time
- When reconnecting: Shows reconnect attempt number
- When disconnected: "Reconnect" button available

### Automatic Reconnection

The SSE manager automatically reconnects with exponential backoff:
- Initial delay: 1 second
- Maximum delay: 30 seconds
- Automatic deduplication of events by sequence number

---

## Jobs-Native Export Flow (NEW in v0.19.0)

The Export screen now uses a true async job flow:

### Starting a Scholarly Run

1. Navigate to **Export**
2. Enter reference and configure options
3. Click "Run Scholarly Export"
4. **Immediate response**: Job ID returned, modal appears

### Job Progress Modal

The modal shows live progress through 10 stages:

| Stage | Description |
|-------|-------------|
| Initializing | Setting up job environment |
| Generating lockfile | Creating reproducible environment spec |
| Checking gates | Verifying variant acknowledgements |
| Running translation | Translating passage tokens |
| Exporting apparatus | Writing textual variant apparatus |
| Exporting translation | Writing token-level translation data |
| Exporting citations | Writing source citations |
| Exporting quote | Writing quotable translation |
| Creating snapshot | Writing combined export with hashes |
| Building bundle | Assembling verified bundle |

### Cancel Flow

1. Click "Cancel" button in progress modal
2. Button changes to "Cancel Requested..." (disabled, yellow)
3. Backend signals job to stop at next checkpoint
4. Modal updates to "Export Cancelled" when confirmed

### Terminal States

| State | Styling | Actions |
|-------|---------|---------|
| **Success** | Green box | "View in Jobs", "Close" |
| **Gate Blocked** | Amber box (non-error) | "Resolve Gates", "Close" |
| **Failed** | Red box | Error list, "Close" |
| **Cancelled** | Gray message | "Close" |

Note: Gate-blocked is intentionally NOT styled as an error. It's a valid terminal
state that requires user action (acknowledging variants), not a failure.

---

## Jobs Screen Enhancements (NEW in v0.19.0)

### Cancel Confirmation

When canceling a job:
- Confirmation dialog appears with best-effort warning
- For running jobs: "Cancel may not take effect immediately"
- For queued jobs: Immediate cancellation

### Job Detail Drawer

Click any job row to open the detail drawer:
- Full job result with output paths
- For scholarly jobs: Output directory, bundle path, run log summary
- For gate-blocked jobs: List of pending variants
- For failed jobs: Full error details

### Live Updates

Job list updates automatically via SSE:
- New jobs appear immediately
- Progress updates in real-time
- Status changes without refresh

---

## Connection Status Indicator (NEW in v0.17.0)

The sidebar status indicator now reflects true readiness, not just port reachability:

### What "Connected" Means Now

| Status | Meaning |
|--------|---------|
| **Connected** (green) | Capabilities fetched + version compatible + required endpoints exist |
| **Validating...** (yellow) | Connected to port, validating compatibility |
| **Degraded** (yellow) | Connected but heartbeat stale (>10s) |
| **Disconnected** (red) | Cannot reach backend |

### Compatibility Validation

On connection, the GUI:
1. Fetches `/v1/capabilities` from the backend
2. Validates `min_gui_version` matches current GUI version
3. Checks that required endpoints exist (translate, sources, gates_pending)
4. Shows blocking modal if incompatible

If incompatible, core actions are disabled until resolved. The modal shows:
- Exact version mismatch (if version issue)
- Missing endpoints (if API issue)
- Steps to resolve

---

## Workflow: Scholarly Export from GUI

### Standard Workflow (Recommended)

1. Start everything: `redletters gui`
2. GUI opens automatically in browser
3. Navigate to **Explore**
4. Enter reference, select Traceable mode
5. Review renderings and variants
6. Navigate to **Export**
7. Follow Export Wizard steps
8. Acknowledge any pending gates
9. Run Scholarly Export
10. Find outputs in `~/.greek2english/runs/scholarly-{timestamp}/`

### Quick Export (with Force)

1. Navigate to **Export**
2. Enter reference
3. When gates detected, select "Force Export"
4. Confirm responsibility
5. Run export (warnings recorded in run_log.json)

---

## Gate Enforcement

The GUI enforces the same gate rules as the CLI:

- **Significant variants** block export until acknowledged
- **Side-by-side comparison** shows all readings with witnesses
- **Acknowledgement persists** per session
- **Force option** records responsibility but allows progress

Gates become "export safety checkpoints" - friction at the right moment,
not friction everywhere.

---

## Troubleshooting (Updated v0.17.0)

The GUI now provides structured error panels with specific guidance for each error type.
When you see an error, use the "Copy Diagnostics" button to capture full details for debugging.

### Error Categories and Fixes

| Error | Icon | Likely Cause | Fix |
|-------|------|--------------|-----|
| **Network Error** | ⚡ | Connection refused | Start backend: `redletters engine start` |
| **Authentication (401)** | 🔒 | Token invalid/expired | Refresh auth token |
| **Not Found (404)** | 🔍 | Endpoint missing | Upgrade backend to v0.16.0+ |
| **Gate Blocked (409)** | 🚧 | Variants need acknowledgement | Acknowledge in Gate screen |
| **Service Unavailable (503)** | ⏳ | Engine not initialized | Wait and retry |
| **Server Error (5xx)** | 🔧 | Internal backend error | Check backend logs |

### "Not Connected" panel appears

1. Ensure `redletters engine start --port 47200` is running
2. Check the port in the connection panel (default: 47200)
3. Click "Check Health" to test connectivity
4. Verify no firewall is blocking localhost connections

### "Compatibility Issue" modal appears

1. Check the version mismatch details shown
2. If GUI too old: Update the GUI to the required version
3. If backend too old: Upgrade with `pip install -U redletters`
4. If endpoints missing: Ensure you're running backend v0.16.0+

### GUI loads but shows no data

1. Run `redletters init` to initialize the database
2. Check the backend logs for errors
3. Try `redletters query "Matthew 3:2"` from CLI to verify data exists

### Explore screen shows "Not Connected"

1. Check sidebar indicator - should be green "Connected"
2. If yellow "Validating", wait a moment
3. If sources not installed, click "Run Setup Wizard"

### Export fails with gate error

1. Navigate to **Explore** first
2. Review the passage to see gate details
3. Acknowledge variants via the Gate screen
4. Return to Export and retry

### Desktop build fails

1. Ensure Rust toolchain is installed: `rustc --version`
2. On macOS, ensure Xcode Command Line Tools are installed
3. Check Tauri prerequisites: https://tauri.app/v1/guides/getting-started/prerequisites

---

## Gate Consistency (v0.15.0)

Gate detection now uses a single source of truth:

- **Export Wizard** uses `GET /v1/gates/pending` endpoint
- **ScholarlyRunner** uses the same gate resolver internally
- Both use the same `VariantStore` and `AcknowledgementStore` logic

This ensures that gate detection in the Export Wizard always matches
what `/v1/run/scholarly` will check, eliminating drift.

---

## API Reference

The GUI communicates with the backend via HTTP:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/engine/status` | GET | Engine health and status |
| `/v1/capabilities` | GET | API capabilities handshake (v0.16.0) |
| `/v1/stream` | GET | SSE event stream |
| `/v1/jobs` | GET/POST | Job management |
| `/v1/gates/pending` | GET | Check pending gates (v0.15.0) |
| `/translate` | POST | Translate passage |
| `/acknowledge` | POST | Acknowledge variant |
| `/sources/status` | GET | Source installation status |
| `/v1/run/scholarly` | POST | Scholarly run workflow |

See `docs/API.md` for full endpoint documentation.

---

## Verification Checklist (Sprint 17)

Use this checklist to verify the GUI Intuition + Truthful State features work correctly.

### Fresh Install (No Packs) → Wizard → Translation

- [ ] Start backend: `redletters engine start --port 47200`
- [ ] Open GUI in browser (http://localhost:5173)
- [ ] **Expected**: Bootstrap Wizard appears automatically
- [ ] Click through Welcome → Backend Connection (shows green check)
- [ ] On Install Spine step: Click "Install" → Status shows "Installed!"
- [ ] On Test Translation step: Click "Run Test Translation" → Shows success
- [ ] Click "Start Exploring" → Wizard closes
- [ ] Navigate to Explore → Enter "John 1:1" → Press Enter
- [ ] **Expected**: Translation renders with Greek text and rendering card

### Wrong Port → Precise Fix Shown

- [ ] Stop backend (Ctrl+C)
- [ ] Refresh GUI page
- [ ] **Expected**: "Not Connected" panel appears
- [ ] Change port to 47201 in Settings
- [ ] **Expected**: Connection attempt fails
- [ ] **Verify**: Error panel shows "Network Error" with fix suggestions
- [ ] Change port back to 47200, click "Check Health"
- [ ] **Expected**: Reconnects when backend restarted

### Backend Without Endpoints → Capability Mismatch

- [ ] Start a minimal HTTP server on port 47200 without the required endpoints
- [ ] Refresh GUI
- [ ] **Expected**: Compatibility modal appears
- [ ] **Verify**: Shows "Missing required endpoints" message
- [ ] **Verify**: Modal lists specific missing endpoints
- [ ] **Verify**: Copy Diagnostics works
- [ ] Click "Continue Anyway" to dismiss (or restart real backend)

### Forced Export with Gates → Responsibility UI + Logs

- [ ] Navigate to Explore → Translate a passage with variants
- [ ] Navigate to Export → Enter same reference
- [ ] Click "Check Gates & Continue"
- [ ] **Expected**: Gates Detected step shows pending variants
- [ ] Click "Force Export (Not Recommended)"
- [ ] Check the confirmation checkbox
- [ ] Click "Proceed Anyway"
- [ ] Click "Run Scholarly Export"
- [ ] **Expected**: Export completes with warning about forced gates
- [ ] **Verify**: run_log.json contains `forced_responsibility` field

### Jobs Screen Filters + Failure Display

- [ ] Navigate to Jobs
- [ ] Start a Demo Job
- [ ] **Expected**: Job appears in list, filter buttons show counts
- [ ] Click filter buttons (All/Running/Failed/Completed)
- [ ] **Expected**: List filters correctly
- [ ] If a job fails: **Verify** error summary shows (not raw traceback)
- [ ] Click "Details" → **Expected**: Full traceback appears
- [ ] Click "Copy" → **Expected**: Diagnostics copied to clipboard

### Explore Screen Usability

- [ ] Navigate to Explore
- [ ] **Expected**: Empty state shows example chips and "Explore Greek New Testament"
- [ ] Click an example chip (e.g., "John 1:1")
- [ ] **Expected**: Translation starts automatically
- [ ] Translate another reference
- [ ] Refresh page, focus reference input
- [ ] **Expected**: Recent refs dropdown appears
- [ ] **Verify**: Compare/Heatmap toggles are disabled until result exists
- [ ] After translation: toggles become enabled

### Verification Checklist (Sprint 19) - Jobs-Native GUI

Use this checklist to verify the Jobs-Native GUI features work correctly.

#### SSE Connection Badge

- [ ] Start backend: `redletters engine start --port 47200`
- [ ] Open GUI, look at header (top-right area)
- [ ] **Expected**: ConnectionBadge shows "Connected" with green dot
- [ ] Click badge to show tooltip
- [ ] **Verify**: Tooltip shows Base URL, Last Event ID, Last Message time
- [ ] Stop backend (Ctrl+C)
- [ ] **Expected**: Badge changes to "Reconnecting..." with yellow pulsing dot
- [ ] **Verify**: Tooltip shows reconnect attempt number
- [ ] Wait for max reconnects (badge turns red "Disconnected")
- [ ] Click "Reconnect" in tooltip
- [ ] Start backend again
- [ ] **Expected**: Badge returns to "Connected" green state

#### Export with Job Progress Modal

- [ ] Navigate to **Export**
- [ ] Enter a reference (e.g., "John 1:1-5")
- [ ] Click "Run Scholarly Export"
- [ ] **Expected**: JobProgressModal appears immediately
- [ ] **Verify**: Stage list shows 10 stages, current stage highlighted
- [ ] **Verify**: Progress bar fills as stages complete
- [ ] **Verify**: Percent display updates
- [ ] Wait for completion
- [ ] **Expected**: Success state shows output directory and bundle path
- [ ] Click "View in Jobs" → navigates to Jobs screen
- [ ] Click "Close" → modal closes

#### Cancel Flow

- [ ] Start a new scholarly run
- [ ] While running, click "Cancel" button
- [ ] **Expected**: Button changes to "Cancel Requested..." (disabled, yellow)
- [ ] **Expected**: Title changes to "Cancelling..."
- [ ] Wait for cancellation to complete
- [ ] **Expected**: Modal shows "Export Cancelled" message
- [ ] **Verify**: Message says "This export was cancelled before completion"

#### Gate-Blocked State (Non-Error)

- [ ] Translate a passage with unacknowledged significant variants
- [ ] Run scholarly export without acknowledging
- [ ] **Expected**: Gate-blocked result (amber box, NOT red)
- [ ] **Verify**: Shows "Gates Pending" title
- [ ] **Verify**: Lists pending variant names
- [ ] **Verify**: "Resolve Gates" button appears (if handler provided)

#### Jobs Screen Cancel Confirmation

- [ ] Navigate to **Jobs**
- [ ] Start a new job (or find a running one)
- [ ] Click the cancel button on a job row
- [ ] **Expected**: Confirmation dialog appears
- [ ] **Verify**: Dialog explains best-effort cancellation
- [ ] Click "Cancel Job" in dialog
- [ ] **Expected**: Job status updates to cancelled

#### Jobs Screen Detail Drawer

- [ ] Navigate to **Jobs**
- [ ] Click on a completed job row
- [ ] **Expected**: Detail drawer opens on right side
- [ ] **Verify**: Shows job type, status, timestamps
- [ ] For scholarly jobs: **Verify** output_dir and bundle_path shown
- [ ] For failed jobs: **Verify** error details shown
- [ ] Click outside drawer or X button to close
