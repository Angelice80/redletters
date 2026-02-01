# Greek2English Desktop Application — Full UX & Architecture Specification

> **Version**: 1.0.0
> **Date**: 2026-01-27
> **Status**: Draft — Awaiting Implementation
> **Supersedes**: Phase 5 UI roadmap item in BMAD-SPEC.md
> **Related ADRs**: ADR-001 (Core Architecture), ADR-002 (Provenance-First Data Model)

---

## Executive Summary

This specification defines a cross-platform desktop application (Windows 10/11 + macOS) that provides a professional GUI "cockpit" for the Greek2English translation engine. The engine runs as a long-running local background service, enabling streaming logs, real-time progress, job queueing, cancellation, and receipt-grade reporting.

**Key Differentiator**: Every translation job produces a complete provenance receipt — inputs, configuration, source pins, delimiter decisions, versions, timestamps, and output hashes — aligned with the project's Epistemic Constitution.

---

# PART 1: UI/UX SPECIFICATION

## A) Information Architecture

### Navigation Structure (Left Sidebar)

```
┌─────────────────────────────────────────────────────────┐
│ [Engine Status Pill]  Greek2English v1.2.0              │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  Dashboard   │                                          │
│              │                                          │
│  Jobs [3]    │         MAIN CONTENT AREA                │
│              │                                          │
│  Sources     │                                          │
│              │                                          │
│  Settings    │                                          │
│              │                                          │
│  Diagnostics │                                          │
│              │                                          │
│  About       │                                          │
│              │                                          │
├──────────────┴──────────────────────────────────────────┤
│ [Stream: ●] 42 events/sec │ Last heartbeat: <1s ago     │
└─────────────────────────────────────────────────────────┘
```

### Section Definitions

| Section | Purpose | Primary Actions | Success Criteria |
|---------|---------|-----------------|------------------|
| **Dashboard** | At-a-glance system health + recent activity | Quick-start job, view active jobs, check engine health | User knows system state in <3 seconds |
| **Jobs** | Job queue management, history browsing | Create job, filter/search history, bulk actions | Find any job in <5 seconds, start job in <30 seconds |
| **Job Detail** | Deep inspection of single job | View logs, download artifacts, export receipt, retry | All job data accessible without scrolling between panels |
| **Sources** | Manage input catalogs, source files, pins | Add/remove sources, verify integrity, view pins | User trusts source state matches expectations |
| **Settings** | Configure defaults, profiles, engine behavior | Edit profiles, set defaults, manage paths | Changes persist and apply to next job |
| **Diagnostics** | Troubleshoot engine issues, export bundles | Export diagnostic zip, view system info, test connectivity | Generate support bundle in <10 seconds |
| **About** | Version info, licenses, update check | Check for updates, view licenses, copy version info | User can report exact version instantly |

---

## B) Key User Journeys

### Journey 1: First Launch / Onboarding

```
SCREEN 1: Welcome
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              Welcome to Greek2English                   │
│                                                         │
│     This tool requires a background service (engine)    │
│     to process your files.                              │
│                                                         │
│     [Checking engine status...]                         │
│                                                         │
└─────────────────────────────────────────────────────────┘

→ Engine check runs automatically (GET /v1/engine/status)

SCREEN 2A: Engine Found & Compatible
┌─────────────────────────────────────────────────────────┐
│  ✓ Engine detected                                      │
│    Version: 1.2.0 (compatible)                          │
│    Status: Running                                      │
│                                                         │
│  Let's configure your workspace:                        │
│                                                         │
│  Default output folder:                                 │
│  [/Users/admin/Documents/Greek2English] [Browse]        │
│                                                         │
│  [ ] Start engine automatically on login                │
│                                                         │
│           [Continue to Dashboard →]                     │
└─────────────────────────────────────────────────────────┘

SCREEN 2B: Engine Not Running
┌─────────────────────────────────────────────────────────┐
│  ⚠ Engine installed but not running                     │
│                                                         │
│  The engine service needs to be started.                │
│                                                         │
│           [Start Engine]                                │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  Troubleshooting:                                       │
│  • Check if another instance is running                 │
│  • Verify port 47200 is available                       │
│  • View logs at ~/.greek2english/logs/                  │
└─────────────────────────────────────────────────────────┘

SCREEN 2C: Engine Version Mismatch
┌─────────────────────────────────────────────────────────┐
│  ✗ Engine version incompatible                          │
│                                                         │
│    GUI requires: 1.x                                    │
│    Engine found: 0.9.3                                  │
│                                                         │
│  The engine must be updated to continue.                │
│                                                         │
│           [Update Engine]  [View Details]               │
│                                                         │
│  This will restart the engine. Running jobs will        │
│  be cancelled.                                          │
└─────────────────────────────────────────────────────────┘

SCREEN 2D: Engine Not Installed
┌─────────────────────────────────────────────────────────┐
│  ✗ Engine not found                                     │
│                                                         │
│  The Greek2English engine is not installed or           │
│  cannot be located.                                     │
│                                                         │
│  Expected location:                                     │
│  /Applications/Greek2English/engine                     │
│                                                         │
│           [Install Engine]  [Locate Manually]           │
│                                                         │
│  If you installed to a custom location, click           │
│  "Locate Manually" to specify the path.                 │
└─────────────────────────────────────────────────────────┘
```

**Flow Logic:**
1. Launch → Check engine status (timeout: 5s)
2. If connected + compatible → Show workspace config
3. If connected + incompatible → Show version mismatch (BLOCKS further action)
4. If not running → Offer start button
5. If not installed → Offer install/locate
6. After successful setup → Redirect to Dashboard

---

### Journey 2: Create a Job

```
SCREEN: Jobs List (with "New Job" action)
┌─────────────────────────────────────────────────────────┐
│ Jobs                                    [+ New Job]     │
├─────────────────────────────────────────────────────────┤
│ Filter: [All States ▼] [All Sources ▼] [Search...]      │
├─────────────────────────────────────────────────────────┤
│ JOB-2024-001 │ Running  │ matthew.xml │ 45% │ 2m ago    │
│ JOB-2024-002 │ Completed│ mark.xml    │ 100%│ 1h ago    │
│ ...                                                     │
└─────────────────────────────────────────────────────────┘

→ User clicks [+ New Job]

SCREEN: New Job — Step 1: Select Inputs
┌─────────────────────────────────────────────────────────┐
│ New Job                                    Step 1 of 3  │
├─────────────────────────────────────────────────────────┤
│ SELECT INPUT FILES                                      │
│                                                         │
│ ┌─ Available Sources ─────────────────────────────────┐ │
│ │ □ matthew.xml     (Catalog: NT Greek, v2.1)         │ │
│ │ □ mark.xml        (Catalog: NT Greek, v2.1)         │ │
│ │ ☑ luke.xml        (Catalog: NT Greek, v2.1)         │ │
│ │ □ john.xml        (Catalog: NT Greek, v2.1)         │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [Add External File...]                                  │
│                                                         │
│ Selected: 1 file (luke.xml)                             │
│                                                         │
│                        [Cancel]  [Next: Configure →]    │
└─────────────────────────────────────────────────────────┘

→ User selects file(s), clicks Next

SCREEN: New Job — Step 2: Configure
┌─────────────────────────────────────────────────────────┐
│ New Job                                    Step 2 of 3  │
├─────────────────────────────────────────────────────────┤
│ CONFIGURATION                                           │
│                                                         │
│ Profile: [Default ▼]  [Edit Profile]                    │
│                                                         │
│ ┌─ Output Settings ───────────────────────────────────┐ │
│ │ Format:    [○ JSON  ● XML  ○ CSV]                   │ │
│ │ Encoding:  [UTF-8 ▼]                                │ │
│ │ Output to: [~/Documents/Greek2English/out] [Browse] │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ Rendering Options ─────────────────────────────────┐ │
│ │ ☑ Include ultra-literal rendering                   │ │
│ │ ☑ Include natural rendering                         │ │
│ │ ☑ Include meaning-first rendering                   │ │
│ │ ☑ Include jewish-context rendering                  │ │
│ │ ☑ Include receipts with full provenance             │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│                        [← Back]  [Next: Review →]       │
└─────────────────────────────────────────────────────────┘

→ User configures, clicks Next

SCREEN: New Job — Step 3: Review & Start
┌─────────────────────────────────────────────────────────┐
│ New Job                                    Step 3 of 3  │
├─────────────────────────────────────────────────────────┤
│ REVIEW                                                  │
│                                                         │
│ Input:  luke.xml (1.2 MB)                               │
│ Source: NT Greek Catalog v2.1 @ commit a3f8c21          │
│ Output: ~/Documents/Greek2English/out/luke.xml          │
│ Profile: Default                                        │
│                                                         │
│ ┌─ Validation ────────────────────────────────────────┐ │
│ │ ✓ Input file accessible                             │ │
│ │ ✓ Output path writable                              │ │
│ │ ✓ Configuration valid                               │ │
│ │ ⚠ Output file exists (will be overwritten)          │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ □ Add to queue (start when resources available)         │
│ ● Start immediately                                     │
│                                                         │
│                        [← Back]  [Start Job]            │
└─────────────────────────────────────────────────────────┘

→ User clicks [Start Job]
→ POST /v1/jobs with config
→ Redirect to Job Detail (running state)
```

**Validation Rules (Step 3):**
- All inputs must be accessible (engine validates via API)
- Output path must be writable
- Config must pass schema validation
- Warnings shown but don't block (user can proceed)
- Errors block start (button disabled with tooltip)

---

### Journey 3: Monitor Running Job

```
SCREEN: Job Detail (Running)
┌─────────────────────────────────────────────────────────┐
│ ← Jobs    JOB-2024-003                        [Cancel]  │
├─────────────────────────────────────────────────────────┤
│ STATUS: ● Running                                       │
│ ████████████░░░░░░░░░░░░░░░░░░ 42%                      │
│ Phase: Parsing verses (1,247 / 2,973)                   │
│ Elapsed: 00:02:34  |  ETA: ~00:03:30                    │
├─────────────────────────────────────────────────────────┤
│ LIVE LOG                          [Pause] [Levels ▼]   │
├─────────────────────────────────────────────────────────┤
│ 14:23:01.234 INFO  parser    Processing chapter 12     │
│ 14:23:01.456 INFO  parser    Processing chapter 13     │
│ 14:23:01.678 WARN  encoding  Non-standard char at 13:5 │ ←[Jump to Error]
│ 14:23:01.890 INFO  parser    Processing chapter 14     │
│ 14:23:02.012 INFO  parser    Processing chapter 15     │
│ ▼ (streaming...)                                        │
├─────────────────────────────────────────────────────────┤
│ [Copy Line] [Copy as JSON] [Export Logs] [Search]      │
└─────────────────────────────────────────────────────────┘

RIGHT PANEL (Inspector):
┌───────────────────────────────┐
│ JOB DETAILS                   │
├───────────────────────────────┤
│ Job ID:   JOB-2024-003        │
│ Created:  2024-01-15 14:20:27 │
│ Input:    luke.xml            │
│ Profile:  Default             │
│                               │
│ ─── Config Snapshot ───       │
│ format: xml                   │
│ encoding: utf-8               │
│ styles: all                   │
│ receipts: true                │
│                               │
│ [View Full Config]            │
└───────────────────────────────┘
```

**Log Viewer Features:**
- **Pause/Resume**: Stops auto-scroll, keeps buffering
- **Level Filter**: Dropdown with checkboxes for TRACE/DEBUG/INFO/WARN/ERROR
- **Subsystem Filter**: Filter by parser/encoder/validator/etc.
- **Search**: Cmd/Ctrl+F opens inline search bar
- **Jump to Error**: Button appears when warnings/errors exist
- **Copy Line**: Right-click or button copies plain text
- **Copy as JSON**: Copies structured log entry
- **Export**: Downloads all logs as .jsonl file

**Progress Display Rules:**
- Show percentage when deterministic (known total items)
- Show "Processing..." with spinner when indeterminate
- ETA shown only when >30 seconds of data available; shows "~" prefix
- Phase name always visible (what engine is doing NOW)

---

### Journey 4: Investigate Failure

```
SCREEN: Job Detail (Failed)
┌─────────────────────────────────────────────────────────┐
│ ← Jobs    JOB-2024-004                                  │
├─────────────────────────────────────────────────────────┤
│ STATUS: ✗ Failed                                        │
│ Failed after 00:01:23 at phase: Validation              │
├─────────────────────────────────────────────────────────┤
│ ERROR SUMMARY                                           │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✗ E_PARSE_INVALID_STRUCTURE                         │ │
│ │                                                     │ │
│ │ The input file contains malformed XML at line 1,247 │ │
│ │                                                     │ │
│ │ Details:                                            │ │
│ │ • Expected closing tag </verse>                     │ │
│ │ • Found </chapter> instead                          │ │
│ │ • Context: "...και ειπεν</chapter>..."              │ │
│ │                                                     │ │
│ │ Suggested Actions:                                  │ │
│ │ 1. Check line 1,247 in the source file              │ │
│ │ 2. Validate XML structure before retrying           │ │
│ │ 3. If using auto-generated input, report upstream   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [Expand Full Stack Trace]  [Export Error Bundle]        │
├─────────────────────────────────────────────────────────┤
│ LOGS (frozen at failure)                [Search]        │
├─────────────────────────────────────────────────────────┤
│ 14:25:01.234 INFO  parser    Processing line 1,245     │
│ 14:25:01.456 INFO  parser    Processing line 1,246     │
│ 14:25:01.678 ERROR parser    Parse error at line 1,247 │ ← ERROR
│ 14:25:01.680 INFO  engine    Job failed, cleaning up   │
│ 14:25:01.890 INFO  engine    Partial outputs preserved │
└─────────────────────────────────────────────────────────┘

│ [Copy Error]  [Export Error Bundle]  [Retry Job]        │
└─────────────────────────────────────────────────────────┘
```

**Error Bundle Contents (ZIP):**
- `error_summary.json` — Structured error with all fields
- `full_logs.jsonl` — Complete log history
- `config_snapshot.json` — Exact config used
- `receipt_partial.json` — Partial receipt
- `system_info.json` — OS, versions, environment
- `input_sample.txt` — First/last 1KB of input (if safe)

---

### Journey 5: Review Completed Job

```
SCREEN: Job Detail (Completed)
┌─────────────────────────────────────────────────────────┐
│ ← Jobs    JOB-2024-002                                  │
├─────────────────────────────────────────────────────────┤
│ STATUS: ✓ Completed                                     │
│ Finished in 00:04:12                                    │
├─────────────────────────────────────────────────────────┤
│ [Summary] [Logs] [Artifacts] [Receipt]    ← TAB BAR     │
├─────────────────────────────────────────────────────────┤
│ SUMMARY                                                 │
│                                                         │
│ Input:     luke.xml (1.2 MB, 2,973 verses)              │
│ Output:    luke_rendered.json (1.8 MB)                  │
│ Duration:  4 minutes, 12 seconds                        │
│                                                         │
│ Statistics:                                             │
│ • Verses processed: 2,973                               │
│ • Red-letter sections: 847                              │
│ • Renderings generated: 4 per verse                     │
│ • Warnings: 3 (non-critical)                            │
│ • Errors: 0                                             │
│                                                         │
│ [Open Output Folder]  [View Receipt]  [Export All]      │
├─────────────────────────────────────────────────────────┤
│ ARTIFACTS                                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✓ luke_rendered.json   1.8 MB   [Open] [Reveal]     │ │
│ │ ✓ luke_receipts.jsonl  245 KB   [Open] [Reveal]     │ │
│ │ ✓ receipt.json         12 KB    [Open] [Reveal]     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ WARNINGS (3)                          [Show in Logs]    │
│ • Verse 12:47: Non-standard character normalized        │
│ • Verse 21:05: Lemma not in lexicon, used fallback      │
│ • Verse 28:91: Empty verse marker preserved             │
└─────────────────────────────────────────────────────────┘
```

**Receipt Tab Content:**
```
RECEIPT                                     [Export JSON]
┌─────────────────────────────────────────────────────────┐
│ Run ID:     run_a3f8c21e9b4d                            │
│ Job ID:     JOB-2024-002                                │
│                                                         │
│ ─── Timing ───                                          │
│ Started:    2024-01-15T14:20:27.123Z                    │
│ Completed:  2024-01-15T14:24:39.456Z                    │
│ Duration:   252.333 seconds                             │
│                                                         │
│ ─── Environment ───                                     │
│ Engine:     1.2.0 (build a3f8c21)                       │
│ OS:         macOS 14.2.1 (Darwin 23.2.0)                │
│ Platform:   arm64                                       │
│                                                         │
│ ─── Inputs ───                                          │
│ luke.xml                                                │
│   Path:     /Users/admin/sources/luke.xml               │
│   Size:     1,258,291 bytes                             │
│   SHA-256:  e3b0c44298fc1c149afbf4c8996fb92427ae41e4... │
│   Modified: 2024-01-10T09:15:00Z                        │
│                                                         │
│ ─── Source Pins ───                                     │
│ MorphGNT-SBLGNT: v6.12 @ commit a3f8c21                 │
│ UBS Dictionary: v1.0                                    │
│                                                         │
│ ─── Configuration ───                                   │
│ {                                                       │
│   "format": "json",                                     │
│   "encoding": "utf-8",                                  │
│   "styles": ["ultra-literal", "natural",                │
│              "meaning-first", "jewish-context"],        │
│   "include_receipts": true,                             │
│   "ranking_weights": {                                  │
│     "morph_fit": 0.40,                                  │
│     "sense_weight": 0.35,                               │
│     "collocation_bonus": 0.15,                          │
│     "uncommon_penalty": 0.10                            │
│   }                                                     │
│ }                                                       │
│                                                         │
│ ─── Outputs ───                                         │
│ luke_rendered.json                                      │
│   Size:     1,892,443 bytes                             │
│   SHA-256:  d7a8fbb307d7809469ca9abcb0082e4f8d5651e4... │
│                                                         │
│ ─── Summary ───                                         │
│ Verses: 2,973  |  Warnings: 3  |  Errors: 0             │
└─────────────────────────────────────────────────────────┘
```

---

### Journey 6: Disconnect/Reconnect

```
SCENARIO: GUI closes while job running

STEP 1: User closes GUI
→ Job continues in engine (no interruption)
→ Engine keeps logging, emitting events

STEP 2: User reopens GUI
→ GUI attempts connection to engine
→ GET /v1/engine/status succeeds

SCREEN: Reconnection Notice (brief toast, 3 seconds)
┌─────────────────────────────────────────────────────────┐
│ ✓ Reconnected to engine                                 │
│   1 job still running                        [View →]   │
└─────────────────────────────────────────────────────────┘

STEP 3: User clicks [View →] or navigates to Jobs
→ GUI fetches job list: GET /v1/jobs?state=running
→ GUI reattaches to event stream with resume_from_sequence

SCREEN: Job Detail (Reattached)
┌─────────────────────────────────────────────────────────┐
│ ← Jobs    JOB-2024-003                        [Cancel]  │
├─────────────────────────────────────────────────────────┤
│ STATUS: ● Running (reconnected)                         │
│ ████████████████████░░░░░░░░░░ 67%                      │
│ Phase: Generating output (1,992 / 2,973)                │
├─────────────────────────────────────────────────────────┤
│ LOG HISTORY                                             │
│ ─── Replayed from storage (missed while disconnected) ──│
│ 14:23:05.000 INFO  parser    Processing chapter 16     │
│ 14:23:06.000 INFO  parser    Processing chapter 17     │
│ ... (247 entries)                                       │
│ ─── Live stream resumed ────────────────────────────────│
│ 14:28:01.234 INFO  output    Writing verse 1,992       │
│ ▼ (streaming...)                                        │
└─────────────────────────────────────────────────────────┘
```

**Reconnection Logic:**
1. On GUI launch, attempt engine connection
2. If connected, fetch running jobs
3. Show toast if jobs were running during disconnect
4. When viewing job, request log replay from last known sequence
5. Merge replayed logs with live stream seamlessly

---

## C) State Models

### Engine Connection State Machine

```
                    ┌─────────────┐
                    │ DISCONNECTED│
                    └──────┬──────┘
                           │ attempt connect
                           ▼
                    ┌─────────────┐
         ┌─────────│ CONNECTING  │─────────┐
         │         └──────┬──────┘         │
         │ timeout        │ success        │ version mismatch
         │                ▼                ▼
         │         ┌─────────────┐  ┌──────────────┐
         │         │  CONNECTED  │  │ INCOMPATIBLE │
         │         └──────┬──────┘  └──────────────┘
         │                │
         │    ┌───────────┼───────────┐
         │    │ heartbeat │ heartbeat │ connection
         │    │ healthy   │ delayed   │ lost
         │    ▼           ▼           ▼
         │  (stay)  ┌──────────┐  ┌─────────────┐
         │          │ DEGRADED │  │DISCONNECTED │
         │          └──────────┘  └─────────────┘
         │                │
         └────────────────┘
```

| State | UI Display | Allowed Actions |
|-------|------------|-----------------|
| `DISCONNECTED` | Red pill: "Engine offline" | Start engine, Reconnect, View cached data |
| `CONNECTING` | Yellow pill: "Connecting..." | Cancel connection attempt |
| `CONNECTED` | Green pill: "Connected" | All actions |
| `DEGRADED` | Orange pill: "Connection unstable" | All actions (with warnings) |
| `INCOMPATIBLE` | Red pill: "Version mismatch" | Update engine, View version info |

### Job Lifecycle State Machine

```
                         ┌───────┐
                         │ DRAFT │ (config being edited)
                         └───┬───┘
                             │ submit
                             ▼
                         ┌────────┐
                    ┌────│ QUEUED │────┐
                    │    └───┬────┘    │
                    │        │ start   │ cancel
                    │        ▼         ▼
                    │    ┌─────────┐ ┌────────────┐
                    │    │ RUNNING │ │ CANCELLED  │
                    │    └────┬────┘ └────────────┘
                    │         │
          ┌─────────┼─────────┼─────────┐
          │         │         │         │
          │ cancel  │ success │ error   │
          ▼         ▼         ▼         │
    ┌────────────┐ ┌───────────┐ ┌──────┴──┐
    │ CANCELLING │ │ COMPLETED │ │ FAILED  │
    └─────┬──────┘ └───────────┘ └─────────┘
          │
          │ confirmed
          ▼
    ┌────────────┐
    │ CANCELLED  │
    └────────────┘

    (Any terminal state) ──archive──▶ ARCHIVED
```

| State | UI Display | Allowed Actions | Badge Color |
|-------|------------|-----------------|-------------|
| `DRAFT` | "Draft" | Edit, Delete, Submit | Gray |
| `QUEUED` | "Queued" | Cancel, View config | Blue |
| `RUNNING` | "Running" + progress | Cancel, View logs, View config | Blue (animated) |
| `CANCELLING` | "Cancelling..." | View logs | Yellow |
| `CANCELLED` | "Cancelled" | View logs, View partial receipt, Retry | Gray |
| `COMPLETED` | "Completed" | View all, Export, Archive, Retry | Green |
| `FAILED` | "Failed" | View error, Export bundle, Retry | Red |
| `ARCHIVED` | "Archived" | View (read-only), Unarchive | Gray (dimmed) |

### Log Viewer State Machine

```
                    ┌──────┐
           ┌────────│ LIVE │◄───────┐
           │        └──┬───┘        │
           │           │            │
      user pauses   user filters    │ user resumes
           │           │            │
           ▼           ▼            │
       ┌────────┐  ┌──────────┐     │
       │ PAUSED │  │ FILTERED │─────┤
       └────────┘  └──────────┘     │
           │           │            │
           │      user searches     │
           │           │            │
           │           ▼            │
           │       ┌────────┐       │
           └──────▶│ SEARCH │───────┘
                   └────────┘
```

| State | Behavior | Visual Indicator |
|-------|----------|------------------|
| `LIVE` | Auto-scroll, append new logs | "● LIVE" green indicator |
| `PAUSED` | Buffer new logs, no auto-scroll | "⏸ PAUSED" yellow indicator + count |
| `FILTERED` | Show subset matching filter | Filter badge + count hidden |
| `SEARCH` | Highlight matches, jump-to-match | Search bar visible + match count |

### Artifacts State Machine

| State | UI Display | Actions Available |
|-------|------------|-------------------|
| `NONE` | "No artifacts" (gray) | None |
| `PARTIAL` | "Partial (job incomplete)" | View, Reveal in Finder (with warning) |
| `COMPLETE` | "✓" + file list | Open, Reveal, Export, Verify |
| `CORRUPTED` | "⚠ Verification failed" | View details, Re-download if possible |
| `QUARANTINED` | "⚠ Quarantined" | View reason, Delete, Attempt recovery |

---

## D) Layout Wireframe Descriptions

### Global Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER (48px)                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ [Logo] Greek2English        [Engine: ● Connected v1.2.0]  [⚙] [?]     │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│ BODY                                                                        │
│ ┌──────────────┬───────────────────────────────────────┬───────────────┐   │
│ │ LEFT NAV     │ MAIN CONTENT                          │ INSPECTOR     │   │
│ │ (200px)      │ (flex)                                │ (300px, opt.) │   │
│ │              │                                       │               │   │
│ │  Dashboard   │                                       │               │   │
│ │              │                                       │               │   │
│ │  Jobs [2]    │       (varies by section)             │  (context-    │   │
│ │              │                                       │   sensitive)  │   │
│ │  Sources     │                                       │               │   │
│ │              │                                       │               │   │
│ │  Settings    │                                       │               │   │
│ │              │                                       │               │   │
│ │  Diagnostics │                                       │               │   │
│ │              │                                       │               │   │
│ │  About       │                                       │               │   │
│ │              │                                       │               │   │
│ └──────────────┴───────────────────────────────────────┴───────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│ FOOTER (24px)                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ [Stream: ●] 42 events/sec │ Heartbeat: <1s │ Jobs: 1 running         │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Dashboard                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─ QUICK ACTIONS ─────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  [+ New Job]      [Open Recent ▼]      [Import Config]                  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─ SYSTEM STATUS ──────────────────┐ ┌─ ACTIVE JOBS ─────────────────────┐ │
│ │                                  │ │                                   │ │
│ │  Engine     ● Running            │ │  JOB-001  ████████░░ 78%  [View]  │ │
│ │  Version    1.2.0                │ │  JOB-002  Queued (pos 1)  [View]  │ │
│ │  Uptime     2h 34m               │ │                                   │ │
│ │  Jobs today 12                   │ │  No other active jobs             │ │
│ │                                  │ │                                   │ │
│ │  [View Diagnostics]              │ │  [View All Jobs →]                │ │
│ └──────────────────────────────────┘ └───────────────────────────────────┘ │
│                                                                             │
│ ┌─ RECENT COMPLETED ────────────────────────────────────────────────────────┐│
│ │                                                                           ││
│ │  JOB-2024-010  │ ✓ Completed │ matthew.xml │ 5 min ago    [View]          ││
│ │  JOB-2024-009  │ ✓ Completed │ mark.xml    │ 1 hour ago   [View]          ││
│ │  JOB-2024-008  │ ✗ Failed    │ luke.xml    │ 2 hours ago  [View]          ││
│ │                                                                           ││
│ └───────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## E) "Badass" Interaction Details

### Keyboard Shortcuts

| Action | macOS | Windows | Context |
|--------|-------|---------|---------|
| New Job | ⌘N | Ctrl+N | Global |
| Start/Submit Job | ⌘↵ | Ctrl+Enter | Job create/edit |
| Cancel Job | ⌘. | Ctrl+. | Job running |
| Search Logs | ⌘F | Ctrl+F | Log viewer |
| Filter Logs | ⌘⇧F | Ctrl+Shift+F | Log viewer |
| Copy Selection | ⌘C | Ctrl+C | Log viewer |
| Copy as JSON | ⌘⇧C | Ctrl+Shift+C | Log viewer |
| Export Logs | ⌘E | Ctrl+E | Job detail |
| Export Receipt | ⌘⇧E | Ctrl+Shift+E | Job detail |
| Toggle Inspector | ⌘I | Ctrl+I | Job detail |
| Pause/Resume Logs | Space | Space | Log viewer (focused) |
| Jump to Error | ⌘J | Ctrl+J | Log viewer |
| Previous Job | ⌘[ | Ctrl+[ | Job detail |
| Next Job | ⌘] | Ctrl+] | Job detail |
| Settings | ⌘, | Ctrl+, | Global |
| Quick Open | ⌘K | Ctrl+K | Global (command palette) |

### Microinteractions

**Toasts (non-blocking notifications):**
- Position: Bottom-right, stacked
- Duration: 4 seconds (info), 6 seconds (warning), persistent until dismissed (error)
- Actions: Optional action button, dismiss X

```
Toast Examples:
┌────────────────────────────────────────┐
│ ✓ Job JOB-2024-003 completed    [View] │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ ⚠ Engine connection unstable      [×]  │
│   Reconnecting...                      │
└────────────────────────────────────────┘
```

**Confirmations (blocking but minimal):**
- Use inline confirmation for destructive actions, not modal dialogs
- Pattern: Button transforms to confirm state

```
Before: [Cancel Job]
After click: [Cancel Job?  Yes / No]  (reverts after 3 seconds)
```

**Progress feedback:**
- Button shows loading state: `[Starting...]` with spinner
- Long operations show progress inline where possible
- Never freeze UI; always show something is happening

### Log Viewer Features

| Feature | Behavior | Shortcut |
|---------|----------|----------|
| Level filter | Checkboxes: TRACE, DEBUG, INFO, WARN, ERROR | Click column header |
| Subsystem filter | Dropdown with active subsystems | Click subsystem badge |
| Time display | Toggle: relative ("2s ago") / absolute ("14:30:01.234") | Click time column |
| Copy line | Copies plain text message | Right-click → Copy |
| Copy JSON | Copies full structured entry | Right-click → Copy as JSON |
| Copy range | Select multiple lines, copy all | Shift+click + ⌘C |
| Jump to error | Scrolls to first ERROR, selects line | ⌘J |
| Pin marker | Bookmark a line for quick return | Click line number |
| Search | Regex-capable, highlights matches | ⌘F |
| Wrap lines | Toggle long line wrapping | View menu |

### Receipt Features

- **Run ID**: `run_<timestamp>_<random>` format, copy-able with single click
- **Config snapshot**: Collapsible JSON view with syntax highlighting
- **Hash verification**: Click any hash to copy; "Verify" button recomputes
- **Export**: JSON (machine), Markdown (human-readable), PDF (formal)
- **Diff view**: Compare two receipts side-by-side (for retry jobs)

### Progress Semantics

| Scenario | Display |
|----------|---------|
| Known total (e.g., 2973 verses) | `████████░░░░ 67%  (1,992 / 2,973 verses)` |
| Phase-based | `Phase 2 of 4: Parsing` with phase progress bar |
| Indeterminate | `Processing... ◐` (animated spinner, no percentage) |
| Mixed | Show phase name + item progress when entering determinate phase |
| ETA | Show only after 30s of data; prefix with `~`; update every 5s max |
| Stalled | After 30s no progress: `⚠ Stalled - no progress for 30 seconds` |

---

## F) Visual System Guidance

### Density Modes

| Mode | Row height | Font size | Padding | Use case |
|------|------------|-----------|---------|----------|
| Compact | 28px | 12px | 4px | Power users, lots of data |
| Comfortable | 36px | 14px | 8px | Default |
| Spacious | 44px | 14px | 12px | Accessibility, presentations |

### Typography Hierarchy

```
Font family: System default (SF Pro on macOS, Segoe UI on Windows)
Monospace: SF Mono / Consolas (for logs, code, hashes)

Heading 1:    20px / 600 weight / 24px line-height  (Page titles)
Heading 2:    16px / 600 weight / 20px line-height  (Section headers)
Heading 3:    14px / 600 weight / 18px line-height  (Subsections)
Body:         14px / 400 weight / 20px line-height  (Default text)
Small:        12px / 400 weight / 16px line-height  (Captions, metadata)
Monospace:    13px / 400 weight / 18px line-height  (Logs, code)
```

### Color Usage Rules

**Status Colors:**
| Status | Light mode | Dark mode | Usage |
|--------|------------|-----------|-------|
| Success | `#16a34a` | `#22c55e` | Completed, valid, connected |
| Warning | `#ca8a04` | `#eab308` | Warnings, degraded, attention |
| Error | `#dc2626` | `#ef4444` | Failed, errors, disconnected |
| Info | `#2563eb` | `#3b82f6` | Running, queued, links |
| Neutral | `#6b7280` | `#9ca3af` | Archived, disabled, secondary |

**Log Level Colors:**
| Level | Color | Background (optional) |
|-------|-------|----------------------|
| TRACE | Gray (`#9ca3af`) | None |
| DEBUG | Gray (`#6b7280`) | None |
| INFO | Default text | None |
| WARN | Yellow (`#ca8a04`) | Light yellow bg |
| ERROR | Red (`#dc2626`) | Light red bg |

**General Rules:**
- Never use color alone to convey meaning (pair with icons/text)
- Maintain 4.5:1 contrast ratio minimum for text
- Use color consistently: green always means success, red always means error
- Muted backgrounds for log levels; bold colors for status badges only

### Dark Mode Requirement

- Default to system preference; allow manual override
- All colors defined with light/dark variants
- Ensure sufficient contrast in both modes
- Test all states in both modes before shipping

### Accessibility Basics

| Requirement | Implementation |
|-------------|----------------|
| Focus rings | 2px solid blue outline on all focusable elements |
| Contrast | 4.5:1 minimum for normal text, 3:1 for large text |
| Motion | Respect `prefers-reduced-motion`; disable animations |
| Screen reader | All interactive elements have aria-labels |
| Keyboard nav | Full functionality without mouse |
| Font scaling | Respect system font size; test at 200% |

---

## G) Implementation Notes (UI-to-Engine Contract)

### Minimum Required Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/engine/status` | GET | Version, health, capabilities |
| `/v1/engine/diagnostics` | GET | Debug bundle generation |
| `/v1/jobs` | GET | List jobs (with filters) |
| `/v1/jobs` | POST | Create and start job |
| `/v1/jobs/{id}` | GET | Job detail |
| `/v1/jobs/{id}/cancel` | POST | Cancel job |
| `/v1/jobs/{id}/receipt` | GET | Get receipt |
| `/v1/jobs/{id}/artifacts` | GET | List artifacts |
| `/v1/jobs/{id}/logs` | GET | Historical logs |
| `/v1/stream` | GET (SSE) | Event stream |

### Event Schema (Minimum)

```typescript
interface BaseEvent {
  event_type: string;
  timestamp_utc: string;      // ISO 8601
  sequence_number: number;    // Monotonic per stream
  job_id?: string;            // null for engine-level events
}

interface JobProgressEvent extends BaseEvent {
  event_type: "job.progress";
  phase: string;
  progress_percent?: number;  // 0-100, null if indeterminate
  items_completed?: number;
  items_total?: number;
  eta_seconds?: number;       // null if unknown
}

interface JobLogEvent extends BaseEvent {
  event_type: "job.log";
  level: "trace" | "debug" | "info" | "warn" | "error";
  subsystem: string;
  message: string;
  payload?: Record<string, unknown>;
  correlation_id?: string;
}

interface EngineHeartbeatEvent extends BaseEvent {
  event_type: "engine.heartbeat";
  uptime_ms: number;
  health: "healthy" | "degraded";
  active_jobs: number;
}
```

---

## H) Edge Cases and Anti-Footguns

### UI Traps and Mitigations

| Trap | Problem | Mitigation |
|------|---------|------------|
| Ambiguous config | User starts job without realizing key settings | Show review step with explicit config summary; highlight non-defaults |
| Instant cancel illusion | User thinks cancel is instant; job still processing | Show "Cancelling..." state; explain cooperative cancellation in UI |
| Lost logs from filter | User filters logs, misses important error | Show "X hidden by filter" badge; "Jump to Error" ignores filter |
| Mixed output confusion | User confuses job output files with engine logs | Separate "Job Logs" from "Artifacts" tabs; different icons |
| Version mismatch block | Incompatible version prevents all work | Show clear upgrade path; allow viewing history read-only |
| Double-click creates duplicates | User clicks "Start" twice, creates two jobs | Idempotency key; disable button immediately; show inline loading |
| Stale job list | User sees outdated status after reconnect | Auto-refresh on reconnect; timestamp "Last updated: X" |
| Partial results misread | User treats partial output as complete | Mark artifacts as "Partial"; require acknowledge to open |
| Overwrite without warning | Job output overwrites existing file | Validation step warns "File exists"; require confirmation |
| Path confusion | Relative paths resolve unexpectedly | Always show absolute paths; normalize and display |

### Explicit UI States (10 Required)

1. **Engine: Not Installed** — Show install button, expected path, locate option
2. **Engine: Starting** — Show spinner, "Starting engine...", timeout after 30s
3. **Engine: Version Mismatch** — Show versions, block actions, offer upgrade
4. **Engine: Degraded** — Show warning badge, allow actions with caution toast
5. **Job: Queued (Position X)** — Show queue position, estimated wait, cancel option
6. **Job: Stalled** — Show warning after 30s no progress, offer cancel
7. **Job: Cancelling (Timeout)** — Show force-cancel option after 10s
8. **Log: Paused with Buffer** — Show buffered count, "Resume to see X new logs"
9. **Artifacts: Verification Failed** — Show which artifact, hash mismatch details
10. **Receipt: Partial (Job Failed)** — Show receipt with "Partial" badge, missing sections marked

### Explicit Error Messages (10 Required)

```
1. ENGINE_NOT_FOUND
   "Greek2English engine not found at /Applications/Greek2English/engine.
    Click 'Install' to set up the engine or 'Locate' to specify a custom path."

2. ENGINE_VERSION_INCOMPATIBLE
   "Engine version 0.9.3 is not compatible with this application (requires 1.x).
    Please update the engine to continue. Running jobs will be cancelled."

3. ENGINE_CONNECTION_LOST
   "Lost connection to engine. Attempting to reconnect...
    Your running jobs are still processing. Check engine logs if this persists."

4. JOB_INPUT_NOT_FOUND
   "Input file not found: /path/to/file.xml
    Verify the file exists and you have read permission."

5. JOB_OUTPUT_PERMISSION_DENIED
   "Cannot write to output folder: /path/to/output
    Check folder permissions or choose a different location."

6. JOB_CONFIG_INVALID
   "Invalid configuration: 'delimiter_mode' must be one of: auto, greek, latin.
    Edit the job configuration and try again."

7. JOB_CANCELLED_PARTIAL
   "Job cancelled. Partial output saved to quarantine folder.
    Review partial results at ~/.greek2english/quarantine/JOB-2024-003/"

8. JOB_FAILED_PARSE_ERROR
   "Failed to parse input at line 1,247: unexpected closing tag.
    Check the input file structure. See error details for context."

9. ARTIFACT_WRITE_FAILED
   "Could not write output file: disk full.
    Free up space and retry the job. Partial results preserved."

10. DATABASE_LOCKED
    "Engine database is locked by another process.
     Ensure only one engine instance is running. Restart engine if needed."
```

---

## Design Risks

| Risk | Consequence if Wrong | Mitigation |
|------|---------------------|------------|
| Event ordering not strict | Logs appear out of order; user loses trust | Enforce sequence numbers; reject/reorder on client |
| "Cancel" lies about state | User thinks job stopped; it didn't | Always show actual state from engine; never fake it |
| Receipt not immutable | Users can't trust evidence | Generate once at job end; store read-only; hash receipt itself |
| Log filtering hides errors | User misses critical failure info | Always show error count badge; "Jump to Error" bypasses filter |
| Version mismatch UX too harsh | Users blocked from reading old job history | Allow read-only access to history; block only new jobs |
| Progress ETA overpromised | User plans around wrong time; frustration | Show ETA only with `~` prefix; hide if variance too high |
| Partial results unlabeled | User ships incomplete data | Mark all partial artifacts explicitly; require acknowledgment |
| Inspector panel distracts | User overwhelmed by information | Collapsible by default; keyboard toggle; remember preference |

---

# PART 2: BACKEND/API ARCHITECTURE

## A) Service Lifecycle Model

### Startup Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **GUI-Launched** | GUI opens, engine not running | GUI spawns engine process; engine detaches after startup |
| **Auto-Start** | System login (if enabled) | OS service/launchd/Task Scheduler starts engine |
| **Manual** | User runs CLI command | `redletters engine start` |
| **On-Demand** | First API request | Socket activation (advanced; optional) |

**Recommended Default**: GUI-Launched with optional Auto-Start preference.

### Process Model

```
┌─────────────────────────────────────────────────────────────────┐
│ GUI Process (Tauri)                                             │
│ - Spawns engine if not running                                  │
│ - Connects via HTTP + SSE to localhost:47200                    │
│ - Can close/reopen without affecting engine                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/SSE (localhost only)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Engine Process (Python/FastAPI daemon)                          │
│ - Binds to 127.0.0.1:47200                                      │
│ - Writes state to ~/.greek2english/                             │
│ - Persists jobs/logs to SQLite                                  │
│ - Runs until explicit shutdown or system shutdown               │
└─────────────────────────────────────────────────────────────────┘
```

### Heartbeat & Health

- Engine emits `engine.heartbeat` every **3 seconds** via SSE
- Heartbeat includes: `uptime_ms`, `health`, `active_jobs`, `queue_depth`
- GUI marks engine "degraded" after **10 seconds** without heartbeat
- GUI marks engine "disconnected" after **30 seconds** without heartbeat

### Shutdown Semantics

| Trigger | Behavior |
|---------|----------|
| `POST /v1/engine/shutdown` | Graceful: finish current job phase, emit `engine.shutting_down`, close connections |
| GUI sends shutdown | Same as above; GUI waits for confirmation or timeout |
| SIGTERM | Graceful shutdown with 30-second timeout |
| SIGKILL / crash | Jobs marked `failed` on next startup; partial outputs quarantined |
| System shutdown | OS sends SIGTERM; engine attempts graceful shutdown |

### Single Instance Enforcement

1. On startup, engine attempts to bind to port 47200
2. If port in use, check if existing engine is healthy via `/v1/engine/status`
3. If healthy, new instance exits with "Engine already running" message
4. If unhealthy/no response, attempt to kill stale process (with user confirmation in GUI)
5. Additionally, write PID to `~/.greek2english/engine.pid` as backup check

---

## B) API Design (Contract-First)

### Base URL & Transport

- **Base**: `http://127.0.0.1:47200/v1`
- **Transport**: HTTP/1.1 (SSE for streaming)
- **Auth**: Bearer token in `Authorization` header
- **Content-Type**: `application/json` for all request/response bodies

### Endpoints

#### GET /v1/engine/status

**Response** (200 OK):
```json
{
  "engine_version": "1.2.0",
  "api_version": "1.0",
  "build_hash": "a3f8c21e9b4d",
  "build_time": "2024-01-10T09:00:00Z",
  "health": "healthy",
  "uptime_ms": 9234567,
  "started_at": "2024-01-15T12:00:00Z",
  "capabilities": ["streaming", "cancel", "resume_partial"],
  "os": "darwin",
  "platform": "arm64",
  "data_dir": "/Users/admin/.greek2english",
  "active_jobs": 1,
  "queue_depth": 2
}
```

#### POST /v1/jobs

**Request**:
```json
{
  "idempotency_key": "user-session-12345-create-1",
  "inputs": [
    {
      "type": "reference",
      "reference": "Luke 1-24"
    }
  ],
  "config": {
    "profile": "default",
    "format": "json",
    "styles": ["ultra-literal", "natural", "meaning-first", "jewish-context"],
    "include_receipts": true,
    "output_dir": "/Users/admin/Documents/Greek2English/out"
  },
  "options": {
    "start_immediately": true,
    "keep_partial_on_cancel": false,
    "priority": "normal"
  }
}
```

**Response** (201 Created):
```json
{
  "job_id": "job_20240115_143000_a3f8",
  "state": "queued",
  "created_at": "2024-01-15T14:30:00Z",
  "queue_position": 1,
  "config_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb924"
}
```

#### GET /v1/stream (SSE)

**Purpose**: Real-time event stream.

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

event: engine.heartbeat
id: 1
data: {"event_type":"engine.heartbeat","timestamp_utc":"2024-01-15T14:30:00Z","sequence_number":1,"uptime_ms":9234567,"health":"healthy","active_jobs":1}

event: job.progress
id: 2
data: {"event_type":"job.progress","timestamp_utc":"2024-01-15T14:30:01Z","sequence_number":2,"job_id":"job_20240115_143000_a3f8","phase":"parsing","progress_percent":67,"items_completed":1992,"items_total":2973}

event: job.log
id: 3
data: {"event_type":"job.log","timestamp_utc":"2024-01-15T14:30:01Z","sequence_number":3,"job_id":"job_20240115_143000_a3f8","level":"info","subsystem":"parser","message":"Processing chapter 15"}
```

---

## C) Job System and Persistence

### SQLite Schema Additions

```sql
-- Extend existing schema for job management

CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY,
  state TEXT NOT NULL DEFAULT 'draft',
  priority TEXT NOT NULL DEFAULT 'normal',
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL,
  config_json TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  input_spec_json TEXT NOT NULL,
  output_dir TEXT,
  progress_percent INTEGER,
  progress_phase TEXT,
  error_code TEXT,
  error_message TEXT,
  receipt_json TEXT,
  idempotency_key TEXT,
  idempotency_expires_at TEXT
);

CREATE TABLE job_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  sequence_number INTEGER NOT NULL,
  timestamp_utc TEXT NOT NULL,
  event_type TEXT NOT NULL,
  level TEXT,
  subsystem TEXT,
  message TEXT,
  payload_json TEXT,
  FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE TABLE artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  size_bytes INTEGER,
  hash TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
```

---

## D) Receipt-Grade Reporting

Aligned with existing ADR-001 receipt structure, extended for job context:

```json
{
  "receipt_version": "1.0",
  "receipt_status": "final",
  "run_id": "run_20240115_143000_a3f8",
  "job_id": "job_20240115_143000_a3f8",
  "timestamps": {
    "created": "2024-01-15T14:30:00.000Z",
    "started": "2024-01-15T14:30:01.234Z",
    "completed": "2024-01-15T14:34:39.456Z"
  },
  "environment": {
    "engine_version": "1.2.0",
    "build_hash": "a3f8c21e9b4d",
    "os": "darwin",
    "platform": "arm64"
  },
  "source_pins": [
    {"source": "MorphGNT-SBLGNT", "version": "6.12", "sha256": "..."},
    {"source": "UBS-Dictionary", "version": "1.0", "sha256": "..."}
  ],
  "config_snapshot": {
    "styles": ["ultra-literal", "natural", "meaning-first", "jewish-context"],
    "ranking_weights": {
      "morph_fit": 0.40,
      "sense_weight": 0.35,
      "collocation_bonus": 0.15,
      "uncommon_penalty": 0.10
    }
  },
  "summary": {
    "status": "success",
    "verses_total": 2973,
    "verses_processed": 2973,
    "renderings_per_verse": 4,
    "warnings_count": 3,
    "errors_count": 0
  },
  "receipt_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b"
}
```

---

## E) Failure Modes (12 Error Scenarios)

| # | Error Code | HTTP | User Message |
|---|-----------|------|--------------|
| 1 | `E_VERSION_INCOMPATIBLE` | 409 | Engine version X.X is not compatible with this application |
| 2 | `E_ENGINE_BUSY` | 429 | Engine at capacity. Job queued at position N. |
| 3 | `E_INPUT_NOT_FOUND` | 422 | Reference not found in database: "Mark 99:1" |
| 4 | `E_INPUT_PERMISSION` | 403 | Cannot read input file: permission denied |
| 5 | `E_OUTPUT_PERMISSION` | 403 | Cannot write to output directory |
| 6 | `E_CONFIG_INVALID` | 422 | Invalid style: "unknown-style" |
| 7 | `E_LEMMA_NOT_FOUND` | 500 | Lemma not in lexicon (fallback used) |
| 8 | `E_JOB_CANCELLED` | 200 | Job cancelled by user request |
| 9 | `E_JOB_TIMEOUT` | 500 | Job exceeded maximum execution time |
| 10 | `E_DATABASE_LOCKED` | 503 | Database locked by another process |
| 11 | `E_DISK_FULL` | 507 | Cannot write output: disk full |
| 12 | `E_INTERNAL_ERROR` | 500 | Unexpected error. Export diagnostics for support. |

---

# PART 3: UI ↔ ENGINE CONTRACT CHARTER

## Compatibility Policy

```
Semantic Versioning: MAJOR.MINOR.PATCH

Rules:
- MAJOR mismatch → GUI MUST block with upgrade prompt
- GUI.MINOR > Engine.MINOR → GUI MUST warn, allow read-only
- Engine.MINOR > GUI.MINOR → Compatible
- PATCH differences → Always compatible
```

## Transport Rules

- API: HTTP/1.1 on `127.0.0.1:47200`
- Streaming: SSE (simpler, reliable for one-way)
- Event ordering: `sequence_number` (monotonic per job, global for engine)
- Resume: `?resume_from=<seq>` parameter
- Heartbeat: Every 3 seconds; GUI marks degraded after 10s

## Security

- Bind to `127.0.0.1` only
- Bearer token stored in OS keychain
- No external network access required

---

# Implementation Roadmap

This specification enables the following implementation phases:

| Phase | Focus | Stories |
|-------|-------|---------|
| **Phase 1** | Engine as Service | Lifecycle, API server, SQLite persistence |
| **Phase 2** | Job System | Queue, execution, cancellation, receipts |
| **Phase 3** | GUI Shell | Tauri scaffold, engine connection, layout |
| **Phase 4** | Core Screens | Dashboard, jobs list, job detail |
| **Phase 5** | Polish | Log viewer, settings, diagnostics |
| **Phase 6** | Integration | End-to-end testing, cross-platform validation |

---

*Document generated for BMAD workflow implementation. Reference this spec in all ADRs and stories.*
