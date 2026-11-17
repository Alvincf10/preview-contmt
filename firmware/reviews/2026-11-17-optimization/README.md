# Implementation continuation from0e45cb1

Status: production target still fails capacity. This review supersedes the current-state figures in the previous handoff; historical reports remain unchanged.

## Implemented and measured

| Stage | Commit | Flash | Static SRAM |
|---|---|---:|---:|
|Starting handoff|0e45cb1|80748|1582|
|Flash descriptors and shared Nextion presenter|5db3e4b|78672|1528|
|Shared permission/record access|a2db304|77278|1528|
|Current, including numerical/session fixes and indexed ID lookup|0707959|78274|1502|

Net reduction from the starting checkpoint:2474flash bytes and80SRAM bytes. Functional correctness fixes consume part of the savings. The deficit remains45506flash bytes against32768. Static SRAM margin546bytes is not a nested stack proof. The capacity probe still excludes verified sensor/RTC/brightness/sound drivers and finished panel chart integration. No production HEX or upload was produced.

- O0: `tools/size_breakdown.py` groups unique address/size symbols without duplicate aliases. Baseline and intermediate measurements are in this directory; latest output is `releases/size-breakdown.json`. The30720flash/1280static-SRAM engineering budget is not met.
- O1: `hmi/Presenter` uses PROGMEM descriptors and common scalar/model/metric/date renderers. Transport keeps parser/ACK ownership and real-time sensor snapshot. Existing17page wire output remains identical; golden fixture was not regenerated.
- O2: command/page and navigation permissions are tables. `Record` shares key construction for field access to one object; the host and Arduino controller remain the same implementation. Operation IDs pass by const reference to reduce AVR argument copying and are copied into journal transaction state before the caller returns.
- O3: one CRC-verified traversal handles scan fallback for value lookup, operation lookup and maximum object ID. Index metadata now also retains maximum object ID per kind without a RAM array. Rebuild/loss/full/corruption fallback semantics are retained, and deleted IDs remain reserved. No journal schema replacement was used.
- O4: pending output owns component/value buffers throughout transmission. It streams at most16bytes per poll, retains offsets on partial writes and no longer creates a second98byte render buffer on the caller's stack. RX storage remains independent of pending TX. Non-LTO renderNext frame is10bytes; renderField71bytes. START187bytes and several nested repository/math/driver frames remain; overall stack and storage latency are still unproven.
- O5/numerical correctness: binary64 storage now converts native binary32 through IEEE bit fields with explicit nearest-even decoding. The previous decoder reproduced a failure at binary64 pattern3690000000000001: it returned0 when the correctly rounded binary32 result is the smallest positive subnormal. Normal/overflow/subnormal/signed-zero boundaries are now tested. Mathematical formulas and stored binary64 format remain unchanged.

## Session acceptance closed on host

- S09: editing a checkpoint invalidates the old preview and schedules live replay. The next valid sample rebuilds maturity from the edited checkpoint series and its current endpoint, then replaces temperature/wall/monotonic anchors. A Day0 temperature/time edit no longer continues with the old anchor. A failed edit commit leaves the prior point/revision and live trajectory intact. Existing unresolved gap status is not cleared by the edit.
- T04: invalid/backward/forward clock changes stop integration and retain ordered gap bounds. A separate21byte ClockAdjustment value records cause, observed wall endpoints and monotonic timestamp in the same commit. Restart and sample/sensor gap causes have distinct values. Reconciliation explanation still uses its separate text field.
- H07: the UART test allows RESULT_SAVE to commit while TX credit is zero, destroys the old controller/transport before ACK, boots again, then resends the original old-token request through the parser. It verifies one result, identical values and acknowledgement correlated to the original boot/sequence.

These are executable host acceptances, not physical power-cut or RTC/panel validation. Coverage is now76HOST_PASS,1EMULATED_PASS,18PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL.25of102scenarios remain incomplete. See [coverage.json](coverage.json).

## Validation executed on the final code

All12CTest suites pass independently on host64, host32 and ASan/UBSan. Existing65audit cases, both41row reference fixtures and the17page UART snapshot still pass. The new codec suite checks65536deterministic decode/encode patterns plus explicit rounding boundaries; session_clock_uart_edges checks S09/T04/H07. Detailed build/test logs are local ignored artifacts.

`tools/avr_numeric.py` reran both41row datasets on emulated ATmega328P: maximum M error0.0025, maximum Fc error below0.000009MPa. `tools/avr_precision.py` passes620codec cases and actual PROGMEM strings/tables, command permissions, decimal ties and leap-date formatting on an emulated328P. It does not execute the entire presenter or physical devices.

The indexed workload reads836112bytes versus4512800bytes scanning; setup index reads are included conservatively. Operation lookup reads344versus16812bytes. These byte counts are host measurements, not SD timing guarantees. Main/index write-cut tests, corruption tests and indexed reference workflow pass.

## Production work still open

Full controller/repository/storage restructuring is still needed to close the45KB flash deficit. The shared descriptors/context/traversal are implemented, but O0–O5 are not all complete. Sorted disk cursors, bounded rebuild/generate/save/replay and target latency remain open. New lifetime/scheduler work must preserve commit→ACK, frozen history and numerical policies.

BoardBinding sensor/RTC/clock/pins/baud, finished HMI keyboard/modal/chart/font layout, actual HMI/TFT compile and captures, storage fault matrix completeness, target stack and physical integration/soak remain pending. The production sketch still refuses an unverified board profile. No claims of fitting flash or finished hardware acceptance are made.
