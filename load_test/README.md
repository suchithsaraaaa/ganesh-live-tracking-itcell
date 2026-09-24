# High-Concurrency Load Testing Suite
## Hyderabad Police Ganesh Visarjan Live Tracking System

This test suite executes concurrent, multi-user HTTP-level load tests against an **isolated test environment** to verify the capacity, stability, and data integrity of the tracking system.

### Target Concurrency
- **Baseline Acceptance Target (Stage 4)**: 400 Concurrent Authenticated Web Users + 300 Simultaneous Active Tracking Sessions
- **Stress / Saturation Target (Stage 5)**: 500 Concurrent Authenticated Web Users + 300 Simultaneous Active Tracking Sessions

### Strict Data Integrity Rules
- The production database (`ganesh_tracking`) is **NEVER** modified, written to, truncated, or subjected to write-heavy synthetic load.
- All write load (synthetic users, test idols, assignments, tracking sessions, high-frequency GPS telemetry, force-ends) executes exclusively against `ganesh_tracking_isolated_loadtest`.

### Test Architecture
- **Engine**: Python 3 `asyncio` + `aiohttp` concurrent asynchronous HTTP test runner.
- **Workload Mix**:
  - 40%: Dashboard monitoring (`/api/v1/idols/dashboard/`)
  - 20%: Live tracking active markers (`/api/v1/tracking/active/`)
  - 15%: Officer assignment management (`/api/v1/assignments/`)
  - 10%: User management (`/api/v1/users/`)
  - 10%: Reports registry (`/api/v1/reports/`)
  - 5%: Authentication & session checks (`/api/v1/auth/login/`, `/api/v1/auth/me/`)
- **Telemetry Ingestion**:
  - Up to 300 active tracking sessions sending continuous GPS breadcrumbs every 3 seconds to `/api/v1/tracking/location/`
  - Validates zero telemetry loss and duplicate rejection (idempotency)
  - Exercises admin force-end and re-assignment race condition testing under active telemetry load.
