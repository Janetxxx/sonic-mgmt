# Test Plan for High Frequency Telemetry

- [Overview](#overview)
  - [Scope](#scope)
  - [Testbed](#testbed)
  - [Supported Counters](#supported-counters)
- [Setup Configuration](#setup-configuration)
  - [Prerequisites](#prerequisites)
  - [Platform Support](#platform-support)
  - [Test Fixtures](#test-fixtures)
  - [Test Utilities](#test-utilities)
- [Test Cases](#test-cases)
  - [Basic Functionality Tests](#basic-functionality-tests)
    - [Test HFT Port Counters](#test-case-test-hft-port-counters)
    - [Test HFT Full Queue Counters](#test-case-test-hft-full-queue-counters)
    - [Test HFT Full Ingress Priority Group Counters](#test-case-test-hft-full-ingress-priority-group-counters)
    - [Test HFT Full Buffer Pool Counters](#test-case-test-hft-full-buffer-pool-counters)
    - [Test HFT Full Counters](#test-case-test-hft-full-counters)
    - [Test HFT Full Port Counters](#test-case-test-hft-full-port-counters)
  - [State Transition Tests](#state-transition-tests)
    - [Test HFT Disabled Stream](#test-case-test-hft-disabled-stream)
    - [Test HFT Config Deletion Stream](#test-case-test-hft-config-deletion-stream)
    - [Test HFT Poll Interval Validation](#test-case-test-hft-poll-interval-validation)
    - [Test HFT Port Shutdown Stream](#test-case-test-hft-port-shutdown-stream)
- [Open/Action Items](#openaction-items)

---

## Overview

This test plan outlines the approach for validating the [High Frequency Telemetry (HFT)](https://github.com/sonic-net/SONiC/blob/master/doc/high-frequency-telemetry/high-frequency-telemetry-hld.md) feature in SONiC.

HFT enables microsecond-level polling and streaming of network statistics (port counters, queue counters, ingress priority group counters, buffer pool counters) via the `countersyncd` daemon running inside the `swss` container. The tests verify that the system can accurately collect and report real-time telemetry data, respond correctly to dynamic configuration changes, and handle port state transitions gracefully.

### Scope

The test suite covers:
- **Counter data collection**: Verifying that HFT correctly polls and reports PORT, QUEUE, INGRESS_PRIORITY_GROUP, and BUFFER_POOL counters.
- **Platform-aware counter support**: Ensuring tests dynamically select supported counters per platform using the `counter_profiles` module.
- **Stream state management**: Testing dynamic enable/disable of HFT streams and verifying that `countersyncd` output (Msg/s) responds accordingly.
- **Configuration lifecycle**: Validating create → delete → recreate of HFT profiles/groups while `countersyncd` runs continuously.
- **Poll interval accuracy**: Verifying the measured message rate matches expected rate based on configured poll interval.
- **Port state interaction**: Confirming counter behavior (increasing vs. stable) when monitored ports are shut down/started up under traffic.
- **Test infrastructure**: Validation of fixtures (`ensure_swss_ready`, `cleanup_high_frequency_telemetry`, `disable_flex_counters`) and utility functions for HFT config management.

### Testbed

The test will run on the following testbeds:
- `any` topology (marked with `pytest.mark.topology('any')`)

Supported testbed topologies verified on:
- t0-isolated-d32u32s2
- t1-isolated-d56u2

### Supported Counters

HFT Phase 1 supports key AI data center statistics across four object types:

| Object Type | Counters |
|---|---|
| **PORT** | `SAI_PORT_STAT_IF_IN_OCTETS`, `SAI_PORT_STAT_IF_IN_UCAST_PKTS`, `SAI_PORT_STAT_IF_IN_DISCARDS`, `SAI_PORT_STAT_IF_IN_ERRORS`, `SAI_PORT_STAT_IN_CURR_OCCUPANCY_BYTES`, `SAI_PORT_STAT_IF_OUT_OCTETS`, `SAI_PORT_STAT_IF_OUT_DISCARDS`, `SAI_PORT_STAT_IF_OUT_ERRORS`, `SAI_PORT_STAT_IF_OUT_UCAST_PKTS`, `SAI_PORT_STAT_OUT_CURR_OCCUPANCY_BYTES`, `SAI_PORT_STAT_TRIM_PACKETS` |
| **QUEUE** | `SAI_QUEUE_STAT_PACKETS`, `SAI_QUEUE_STAT_BYTES`, `SAI_QUEUE_STAT_DROPPED_PACKETS`, `SAI_QUEUE_STAT_CURR_OCCUPANCY_BYTES`, `SAI_QUEUE_STAT_WATERMARK_BYTES`, `SAI_QUEUE_STAT_WRED_ECN_MARKED_PACKETS`, `SAI_QUEUE_STAT_TRIM_PACKETS` |
| **BUFFER_POOL** | `SAI_BUFFER_POOL_STAT_DROPPED_PACKETS`, `SAI_BUFFER_POOL_STAT_CURR_OCCUPANCY_BYTES`, `SAI_BUFFER_POOL_STAT_WATERMARK_BYTES`, `SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES` |
| **INGRESS_PRIORITY_GROUP** | `SAI_INGRESS_PRIORITY_GROUP_STAT_PACKETS`, `SAI_INGRESS_PRIORITY_GROUP_STAT_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_CURR_OCCUPANCY_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_WATERMARK_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_CURR_OCCUPANCY_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES`, `SAI_INGRESS_PRIORITY_GROUP_STAT_DROPPED_PACKETS` |

> **Note**: Not all counters are supported on all platforms. The `counter_profiles.py` module provides per-platform counter definitions. Tests dynamically query supported counters and skip when none are available.

---

## Setup Configuration

### Prerequisites
- DUT must have the `swss` container running and stable (uptime ≥ 10 seconds).
- The `countersyncd` daemon must be functional inside the `swss` container.
- HFT CLI commands (`config hft add/del/enable/disable`) must be available on the DUT.
- CONFIG_DB (database 4) must be accessible for HFT table management.
- COUNTERS_DB (database 2) must be accessible for queue/buffer object discovery.
- For port shutdown tests: PTF adapter must be available for traffic injection.

### Platform Support

HFT tests are conditionally skipped via `tests_mark_conditions.yaml` on unsupported platforms:

| Platform | Status |
|---|---|
| `x86_64-nvidia_sn5600-r0` | Supported |
| `x86_64-nvidia_sn5640-r0` | Supported (partial counter support) |
| `x86_64-arista_7060x6_64pe_b` | Supported (limited) |
| All other platforms | Skipped |

Per-platform supported counters are defined in `tests/high_frequency_telemetry/counter_profiles.py`. Tests call `get_support_counter_list(duthost, counter_type)` to get the counters available on the current DUT and skip if none are returned.

### Test Fixtures

All fixtures are defined in `tests/high_frequency_telemetry/conftest.py` and run at function scope:

| Fixture | Purpose |
|---|---|
| `ensure_swss_ready` | Verifies the `swss` container is running with ≥ 10s uptime. Restarts `swss` via `systemctl restart swss` if needed and waits up to 40s for stabilization. |
| `cleanup_high_frequency_telemetry` | Removes stale `HIGH_FREQUENCY_TELEMETRY_PROFILE` and `HIGH_FREQUENCY_TELEMETRY_GROUP` keys from CONFIG_DB before each test. Depends on `ensure_swss_ready`. |
| `disable_flex_counters` | Disables all `FLEX_COUNTER_TABLE` entries in CONFIG_DB to prevent interference with HFT counter polling. Restores original states after each test. Depends on `cleanup_high_frequency_telemetry`. |

Fixture dependency chain: `ensure_swss_ready` → `cleanup_high_frequency_telemetry` → `disable_flex_counters`

### Test Utilities

Key utility functions in `tests/high_frequency_telemetry/utilities.py`:

| Function | Purpose |
|---|---|
| `get_available_ports(duthost, tbinfo, desired_ports, min_ports)` | Returns admin-up ports from topology, excluding port-channel members. Skips test if fewer than `min_ports` available. |
| `get_configured_queue_objects(duthost)` | Returns queue objects from `COUNTERS_QUEUE_NAME_MAP` in COUNTERS_DB as `port\|queue_id` strings. |
| `get_configured_buffer_queue_objects(duthost)` | Returns buffer queue objects from `COUNTERS_PG_NAME_MAP` in COUNTERS_DB. |
| `get_configured_buffer_pools(duthost)` | Returns buffer pool names from CONFIG_DB `BUFFER_POOL` table. |
| `setup_hft_profile(...)` | Creates an HFT profile via `config hft add profile` with poll interval and stream state. |
| `setup_hft_group(...)` | Creates an HFT group via `config hft add group` with object type, names, and counters. |
| `setup_hft_stream_state(...)` | Enables/disables an HFT stream via `config hft enable/disable`. |
| `cleanup_hft_config(...)` | Removes HFT groups and profile via `config hft del group/profile`. |
| `run_countersyncd_and_capture_output(...)` | Runs `countersyncd -e` inside `swss` container with timeout and captures output. |
| `CountersyncdMonitor` | Background monitor class that runs `countersyncd` with file-based output capture for continuous state transition tests. |
| `validate_counter_output(...)` | Validates countersyncd output: parses `[Report #N]` blocks, checks counter values, Msg/s rates, `LastTime` timestamps, and per-object counters. |
| `validate_stream_state_transitions(...)` | Validates Msg/s behavior across enabled/disabled phases. |
| `validate_config_state_transitions(...)` | Validates Msg/s behavior across create/delete/recreate phases. |
| `validate_port_state_transitions(...)` | Validates counter trend (increasing/stable) across port up/down phases. |
| `analyze_counter_trend(output)` | Determines counter trend from sampled values: `increasing`, `stable`, `decreasing`, or `no_pattern`. |

---

## Test Cases

All test cases are in `tests/high_frequency_telemetry/test_high_frequency_telemetry.py`.

### Basic Functionality Tests

#### Test Case: Test HFT Port Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_port_counters` |
| **Objective** | Verify basic HFT functionality for port counters with a single counter type (`IF_IN_OCTETS`). |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |

**Test Steps**
1. Get available ports from topology (desired: 2, minimum: 1).
2. Create an HFT profile (`port_profile`) with poll interval 10ms (10,000 μs) and stream state `enabled`.
3. Create a PORT group with the selected ports monitoring `IF_IN_OCTETS`.
4. Run `countersyncd -e` for 360 seconds with stats interval 60 seconds.
5. Validate counter output: all counter values ≥ 0, Msg/s within ±15% of expected rate (100 Msg/s), LastTime timestamps within 60 minutes of current UTC.
6. Verify `countersyncd` is still running under `swss` supervisor after capture.
7. Clean up HFT profile and group.

**Expected Results**
- All monitored counters report values ≥ 0.
- Msg/s rate is within ±15% of expected 100 Msg/s (for 10ms poll interval).
- `countersyncd` remains running in `swss` after test.

---

#### Test Case: Test HFT Full Queue Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_full_queue_counters` |
| **Objective** | Verify HFT for all configured queue objects with platform-supported queue counters. |
| **Fixtures** | `disable_flex_counters` |
| **Topology** | `any` |

**Test Steps**
1. Query all queue objects from `COUNTERS_QUEUE_NAME_MAP` in COUNTERS_DB. Skip if none found.
2. Get supported queue counters for the current platform. Skip if none supported.
3. Create an HFT profile (`queue_profile`) with poll interval 10ms and stream state `enabled`.
4. Create a QUEUE group with all discovered queue objects and supported counters.
5. Run `countersyncd -e` for 360 seconds and capture output.
6. Validate counter values ≥ 0.
7. Clean up HFT configuration.

**Expected Results**
- Counter values ≥ 0 are reported for queue objects.

---

#### Test Case: Test HFT Full Ingress Priority Group Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_full_ingress_priority_group_counters` |
| **Objective** | Verify HFT for all configured ingress priority groups (buffer queues) with platform-supported counters. |
| **Fixtures** | `disable_flex_counters` |
| **Topology** | `any` |

**Test Steps**
1. Query all buffer queue objects from `COUNTERS_PG_NAME_MAP` in COUNTERS_DB. Skip if none found.
2. Get supported ingress priority group counters for the current platform. Skip if none supported.
3. Create an HFT profile (`ingress_pg_profile`) with poll interval 10ms and stream state `enabled`.
4. Create an INGRESS_PRIORITY_GROUP group with all discovered objects and supported counters.
5. Run `countersyncd -e` for 360 seconds and capture output.
6. Validate counter values ≥ 0.
7. Clean up HFT configuration.

**Expected Results**
- Counter values ≥ 0 are reported for ingress priority group objects.

---

#### Test Case: Test HFT Full Buffer Pool Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_full_buffer_pool_counters` |
| **Objective** | Verify HFT for all configured buffer pools with platform-supported counters. |
| **Fixtures** | `disable_flex_counters` |
| **Topology** | `any` |

**Test Steps**
1. Query all buffer pool names from CONFIG_DB `BUFFER_POOL` table. Skip if none found.
2. Get supported buffer pool counters for the current platform. Skip if none supported.
3. Create an HFT profile (`buffer_pool_profile`) with poll interval 10ms and stream state `enabled`.
4. Create a BUFFER_POOL group with all discovered pools and supported counters.
5. Run `countersyncd -e` for 360 seconds and capture output.
6. Validate counter values ≥ 0.
7. Clean up HFT configuration.

**Expected Results**
- Counter values ≥ 0 are reported for buffer pool objects.

---

#### Test Case: Test HFT Full Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_full_counters` |
| **Objective** | Verify HFT when monitoring all supported object types (PORT, QUEUE, INGRESS_PRIORITY_GROUP, BUFFER_POOL) under a single profile. |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |
| **Status** | **Skipped** — Full counters HFT isn't supported. On SN5640, multiple types in one session are not supported. On 7060X6, HFT tests are not yet supported. |

**Test Steps**
1. Collect all available objects and supported counters for each type (PORT, QUEUE, INGRESS_PRIORITY_GROUP, BUFFER_POOL).
2. Create a single HFT profile (`full_hft_profile`) with poll interval 10ms and stream state `enabled`.
3. Create one group per object type under the same profile.
4. Run `countersyncd -e` for 360 seconds and capture output.
5. Validate counter values ≥ 0 across all groups.
6. Clean up HFT configuration.

**Expected Results**
- All configured counter groups produce valid output under a single profile.

---

#### Test Case: Test HFT Full Port Counters

| Item | Description |
|---|---|
| **Test Name** | `test_hft_full_port_counters` |
| **Objective** | Verify HFT when monitoring all available ports with all supported port counters simultaneously. |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |

**Test Steps**
1. Get all available ports from topology (minimum 1 required).
2. Get all supported port counters for the current platform. Skip if none supported.
3. Create an HFT profile (`full_port_counter_profile`) with poll interval 10ms and stream state `enabled`.
4. Create a PORT group with all available ports and all supported counters.
5. Run `countersyncd -e` for 360 seconds and capture output.
6. Validate counter output: at least one counter per port reported.
7. Log counter coverage percentage (actual vs. maximum expected).
8. Clean up HFT configuration.

**Expected Results**
- At least `num_ports` counters are reported (≥ 1 per port).
- Counter coverage percentage is logged for diagnostic purposes.

---

### State Transition Tests

#### Test Case: Test HFT Disabled Stream

| Item | Description |
|---|---|
| **Test Name** | `test_hft_disabled_stream` |
| **Objective** | Verify that dynamically enabling/disabling an HFT stream correctly starts/stops telemetry output. |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |

**Test Steps**
1. Get available ports from topology (desired: 2, minimum: 1).
2. Create an HFT profile (`state_transition_profile`) with poll interval 10ms and stream state `disabled`.
3. Create a PORT group monitoring `IF_IN_OCTETS`.
4. Start continuous `countersyncd` monitoring via `CountersyncdMonitor`.
5. Execute three phases (240 seconds each):
   - **Phase 1 (enabled)**: Enable stream → expect Msg/s > 0.
   - **Phase 2 (disabled)**: Disable stream → expect Msg/s = 0.
   - **Phase 3 (enabled)**: Re-enable stream → expect Msg/s > 0.
6. Validate each phase using `validate_stream_state_transitions()`.
7. Clean up HFT configuration.

**Expected Results**
- Phase 1: Msg/s > 0 (stream active).
- Phase 2: Msg/s = 0 (stream stopped).
- Phase 3: Msg/s > 0 (stream resumed).

---

#### Test Case: Test HFT Config Deletion Stream

| Item | Description |
|---|---|
| **Test Name** | `test_hft_config_deletion_stream` |
| **Objective** | Verify that `countersyncd` correctly responds to dynamic HFT configuration lifecycle changes (create → delete → recreate) without requiring process restart. |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |

**Test Steps**
1. Get available ports from topology (desired: 2, minimum: 1).
2. Start continuous `countersyncd` monitoring via `CountersyncdMonitor`.
3. Execute three phases (240 seconds each):
   - **Phase 1 (create)**: Create HFT profile (`config_deletion_profile`, 10ms, enabled) and PORT group with `IF_IN_OCTETS` → expect Msg/s > 0.
   - **Phase 2 (delete)**: Delete HFT configuration → expect Msg/s = 0.
   - **Phase 3 (create)**: Re-create the same profile and group → expect Msg/s > 0.
4. Validate each phase using `validate_config_state_transitions()`.
5. Clean up any remaining HFT configuration.

**Expected Results**
- Phase 1: Msg/s > 0 (config active).
- Phase 2: Msg/s = 0 (config deleted, telemetry halted).
- Phase 3: Msg/s > 0 (config re-created, telemetry resumed).

---

#### Test Case: Test HFT Poll Interval Validation

| Item | Description |
|---|---|
| **Test Name** | `test_hft_poll_interval_validation` |
| **Objective** | Verify that the measured Msg/s rate matches the expected rate derived from the configured poll interval. |
| **Fixtures** | `disable_flex_counters`, `tbinfo` |
| **Topology** | `any` |
| **Status** | **Skipped** — Some poll intervals may not be supported on all DUTs. |

**Parametrized Inputs**

| Poll Interval (μs) | Expected Msg/s |
|---|---|
| 1,000 (1ms) | 1000 |
| 10,000 (10ms) | 100 |
| 100,000 (100ms) | 10 |
| 1,000,000 (1s) | 1 |
| 10,000,000 (10s) | 0.1 |

**Test Steps**
1. Get available ports from topology (desired: 2, minimum: 1).
2. Create an HFT profile with the parametrized poll interval and stream state `enabled`.
3. Create a PORT group monitoring `IF_IN_OCTETS`.
4. Verify HFT profile and group are present in Redis (CONFIG_DB).
5. Wait 10 seconds for configuration to take effect.
6. Run `countersyncd -e` for 360 seconds and capture output.
7. Extract Msg/s values from the last 3 stable reports.
8. Calculate average Msg/s and compare against expected rate with tolerance bands:
   - ≥ 10 Msg/s: ±20% tolerance
   - 1–10 Msg/s: ±30% tolerance
   - < 1 Msg/s: ±50% tolerance
9. Clean up HFT configuration.

**Expected Results**
- Average measured Msg/s falls within the acceptable tolerance range of the expected rate.

---

#### Test Case: Test HFT Port Shutdown Stream

| Item | Description |
|---|---|
| **Test Name** | `test_hft_port_shutdown_stream` |
| **Objective** | Verify correct HFT counter behavior when a monitored port is shut down and restarted while PTF test traffic is continuously injected. |
| **Fixtures** | `disable_flex_counters`, `tbinfo`, `ptfadapter` |
| **Topology** | `any` |

**Test Steps**
1. Get one available port from topology.
2. Resolve PTF port index and router MAC for traffic injection.
3. Create an HFT profile (`port_shutdown_profile`) with poll interval 10ms and stream state `enabled`.
4. Create a PORT group monitoring `IF_IN_OCTETS` on the test port.
5. Start continuous `countersyncd` monitoring and PTF traffic injection (100 packets/s, simple IP packets).
6. Execute three phases (240 seconds each):
   - **Phase 1 (port up)**: Port up + traffic → expect counters **increasing**.
   - **Phase 2 (port down)**: Shut down port via `config interface shutdown` + traffic continues → expect counters **stable** (no increase).
   - **Phase 3 (port up)**: Start up port via `config interface startup` + traffic continues → expect counters **increasing** again.
7. Validate counter trends per phase using `validate_port_state_transitions()` and `analyze_counter_trend()`.
8. Ensure port is brought back up before cleanup.
9. Clean up HFT configuration.

**Expected Results**
- Phase 1: Counter trend is `increasing` (port up, receiving traffic).
- Phase 2: Counter trend is `stable` (port down, no packets received).
- Phase 3: Counter trend is `increasing` (port back up, receiving traffic again).

---

## Open/Action Items

| Item | Notes |
|---|---|
| `test_hft_full_counters` | Currently skipped. Enable once platforms support multiple object types in a single HFT session. |
| `test_hft_poll_interval_validation` | Currently skipped. Enable once all parametrized intervals are confirmed supported on target DUTs. |
| Arista 7060X6 support | Platform is listed in conditional marks but has empty counter definitions — HFT tests not yet functional. |
| Buffer pool counters on SN5640 | Currently empty in `counter_profiles.py` — `test_hft_full_buffer_pool_counters` will skip on this platform. |
| OpenTelemetry integration | `setup_hft_profile()` accepts `otel_endpoint`/`otel_certs` parameters but they are not yet supported by the `config hft` CLI. |
