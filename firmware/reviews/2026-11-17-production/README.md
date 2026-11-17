# Production continuation, 17 November 2026

Status: **implementation advanced; ATmega328P production release still blocked by capacity and incomplete target/HMI integration.** This review supersedes the current-state statements in the16November audit, whose before/after evidence remains historical.

## Changes implemented

- Initial snapshot committed on main as0b55090. docs/firmware-plan remains local and ignored, together with builds/binaries/local logs. Numerical reference vectors now live in tests/fixtures so normal CTest does not depend on the ignored planning package.
- Actual Arduino battery acquisition uses A0, one discarded conversion plus8averaged ADC samples every100ms, present threshold520, empty877, full991, Q5filter and100consistent percentage confirmations. Calibration/provenance is in board-evidence/battery.json. BatteryDevices connects this acquisition to the production Controller. Missing, stale and invalid readings have distinct statuses; no voltage endpoints or state-of-charge curve were invented.
- Storage now has a disk hash index in CMT.IDX.64buckets stay on disk; nodes grow according to actual keys, with no RAM array of all records. An index node has key, latest journal entry offset, transaction offset, collision link and CRC. Existing keys update in place; tombstones retain their latest location.
- Every mount first validates journal transactions and reconstructs the index from committed entries. The index is disposable; its own writes need not provide transactional durability. Missing, invalid or full index falls back to journal scanning without changing committed values. The next mount rebuilds it. There is no dependency on a stale index generation after reset.
- On indexed lookup the referenced journal transaction is verified before returning bytes. An index lookup does not recheck unrelated committed transactions on every read; full verification occurs on mount. Existing journal schema1 is unchanged.
- Copying records now streams32byte chunks from the committed journal into the new transaction. No128byte copy buffer is retained on the caller's stack. Result calculation/persistence and UART receive/render use separate function frames. Command names/argument counts use one table shared by controller and transport.

## Validation actually executed

All9CTest suites pass on binary64host, binary32host and AddressSanitizer/UndefinedBehaviorSanitizer. This includes the original65audit cases and both41row numerical fixtures. A further indexed workflow runs the same controller through baseline generation, days4/6/26, save, reboot and logical deletion.

New tests verify battery endpoints/noise/confirmation/unplug/replug/invalid ADC, index collisions/update/tombstone/rebuild, missing/full/corrupt index,40index-write cut budgets,100scalar journal-write cut budgets and500cut positions for a three-entry128byte streaming copy. The latter accepts either all old state or all three copied entries; never a partially committed subset. A real host file/sidecar is reopened after the sidecar is deleted.

The index workload reads717050bytes versus4538400bytes for full scanning (about6.33times fewer). The indexed count conservatively includes index reads during setup. These are host byte counts, **not SD latency or electrical tests**. Boot rebuilding, collision chains, fit and large transactions still need bounded scheduling and target latency acceptance.

Non-LTO AVR per-function stack estimates decreased: prepareResult235→66bytes, Repository::copy170→46bytes, checkpointResult205→107bytes and command dispatch149→71bytes. New helper frames still nest; these reductions do not establish a safe worst-case stack. Current runtime stack watermark remains unverified.

Current full capacity probe, including real SD/index/UART/battery code: **81106flash bytes,1764static SRAM bytes**. Physical limits remain32768/2048. Only284SRAM bytes remain before nested calls/interrupts. The new battery/index features increased total footprint compared with the previous79884byte implementation despite local optimizations. No MCU replacement or feature removal was used to hide the failure.

## Remaining production work

1. Restructure the full controller/repository/presenter to fit328P and prove stack margin. Small compiler flags alone have not closed the48338byte flash deficit.
2. Bound generation, transaction copy/save, index rebuild and collision traversal so sensor/UART/menu service cannot starve at large data volume.
3. Complete sensor/RTC/brightness/sound BoardBinding from evidence. The user authorized reusing the battery configuration; that does not establish every other peripheral or its wiring. The production sketch still rejects unverified BoardBinding.
4. Assemble and compile the paired17page HMI including keyboard/modal/chart/fonts, then capture actual UART and verify reconnect on that panel.
5. Complete remaining large-record recovery, clock-adjustment, hardware SD, power-cut and soak acceptance. Automatic day assignment remains explicit/manual according to the plan until policy is confirmed.

W05 moved from NOT_IMPLEMENTED to PARTIAL: the disk index and rebuild are implemented/tested, while the plan's metadata A/B design and bounded rebuilding are not fulfilled by a claim that the whole storage stage is complete. Coverage now73HOST_PASS,1EMULATED_PASS,21PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL. The original assessment remains in its dated folder.

Original-source hash check now flags only .gitignore, which the user explicitly requested changing. Domain TS, Excel and client-reference files remain unchanged. No upload, erase or fuse write was executed.

Evidence: [battery test](battery-tests.txt), [index test](index-benchmark.txt), [indexed workflow](indexed-workflow.txt), [coverage](coverage.json), [capacity](../../releases/avr-capacity.json), [stack](../../releases/avr-stack.json). Detailed CTest logs remain local build artifacts.
