# Flash optimization implementation from520a74f

The retained implementation uses75,414flash bytes and1,502static SRAM bytes in the current AVR capacity probe. It saves2,860flash bytes from78,274, approximately3.65%. It still exceeds the physical32,768byte limit by42,646bytes. This is not a production release or an uploadable image.

## Retained changes

| Checkpoint | Change | Flash | Static SRAM |
|---|---|---:|---:|
|520a74f|Starting implementation|78274|1502|
|8fffaa5|Shared snapshot transaction executor|77482|1500|
|b33c348|Shared streaming schema1 record codec|76964|1502|
|dd0c45e|Bounded integer/text/calendar presentation|75794|1502|
|04f34f8|Shared field/settings validation and loading|75414|1502|

Transaction tables now drive saveBaseline, START, SAVE RESULT and settings writes. Source identity, optional fields, sensor/model snapshots, copy ordering and commit-before-publish semantics remain covered by checkpoint comparison. Created timestamps are acquired at their transaction step rather than being moved ahead of copying. Hardware settings still roll back on failed persistence.

One record codec handles Row37, Point30, Fit28, Result73 and the three parts of Sensors53. Native member offsets are explicit and PROGMEM-backed; wire data remains schema1 little-endian with binary64 numbers. Journal values can be written/read in bounded chunks. An incomplete value cannot commit. Value readers open only after locating a CRC-verified committed transaction, retain their own offsets and enforce bounds. Whole-value CRC verification remains active; the new cursor does not establish bounded transaction latency.

The controller no longer carries a73byte temporary result encoding or a53byte sensor record just to read its timestamp. Presenter sensor formatting reads the selected channel and mask through a verified value reader. Numeric rounding, strtod and dtostrf remain; AVR presentation no longer pulls in varargs printf for integer, date, clock or string concatenation.

The field table covers all18input tokens, their entity, text length, numeric/date policy and model invalidation behavior. Settings share a loading/validation schema. Public flow/status/journal behavior matches the original checkpoint in the comparison below.

## Validation

All15CTest suites pass on host64, host32 and ASan/UBSan. The original12suites and65audit cases remain. Three additions cover streamed record layout/recovery, bounded text formatting and comparison with the old executable.

- `checkpoint_trace.py` compiles the immutable520a74f sources into a separate host executable and executes the same public test program against both implementations. Each precision profile produces300matching lines, including120write-cut scenarios across the four target workflows, with and without the disk index. Records include byte-level journal CRC, commit sequence, navigation/view/IDs, settings and hardware rollback. Fixtures came from that old executable; the17page UART fixture was not regenerated.
- `schema1_record_codec` checks independent wire layouts for Row/Point/Fit/Result/Sensors, invalid flags, partial value ownership,800multi-record byte-cut cases, all41field IDs across all7kinds, native numeric extremes, signed zero, maximum32bit object/index IDs and64bit timestamps/operation IDs after reopening. Opaque blob field preservation and typed record layout validation are distinct tests. This closes W01 on host; it is not physical SD endurance.
- `bounded_text_formatting` compares truncation, zero capacity, uint32 boundaries, padding, clock and joined text against snprintf.
- AVR precision tests pass620numeric codec vectors plus actual PROGMEM field/settings tables, formatting and streamed typed record read/write. Numeric and record checks run in separate physical-region-limited test images. Combining them exceeded the emulator's flash capacity and was rejected; neither image represents complete production firmware.
- Both41row datasets still pass AVR numerical emulation. Maximum maturity error remains0.0025 and maximum Fc error is below0.000009MPa. No mathematical formula was changed.
- UART fixture SHA-256 remains `13126308db2e5e367bd83b9fbf99dcd57f778840cdf0cd5cf24b5e3a211d6812`.

Non-LTO individual frame estimates include START122bytes, load84, storePreview66, sensorText35 and codec transfer28. Baseline START was187 and storePreview137. These reductions are not a nested stack/ISR watermark, and1,502static bytes still leave only546bytes before stack, interrupts and missing drivers.

## Rejected experiment

Passing repository IDs by reference reduced the probe to75,260bytes, but several frame estimates increased by2–6bytes. That change was reverted because the154byte saving did not justify the stack tradeoff. The retained firmware is75,414bytes. See [ledger.json](ledger.json); its rejected entry is explicitly marked.

## Remaining production gates

The changes complete parts of P0/P1/P2/P5 from local document09. They do not complete P0–P6 as a whole. The modest savings do not validate extrapolating table conversion to a32KB final image.

Ordered disk cursors, bounded rebuild/generate/copy/save/replay jobs and acquisition/UART scheduling during large operations are still incomplete. Storage schema2 has not been adopted or claimed to save space. All current data stays schema1. Nested stack and final hardware latency are unproven.

The capacity probe includes shared core/controller/HMI, real SD/index, HardwareSerial and calibrated battery. Sensor/clock/brightness/sound still use labelled probe ports, the clock is a16MHz measurement assumption, and the finished chart pipeline is absent. The production sketch continues to require a verified BoardBinding. It is not acceptable to call this a full production-size measurement or to flash CAPACITY_ONLY.elf.

Sensor/RTC configuration and drivers, paired HMI keyboard/modal/chart/fonts/layout/TFT, physical validation and soak remain pending. Acceptance is77HOST_PASS,1EMULATED_PASS,17PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL:24of102scenarios remain incomplete. No hardware was flashed or accessed.
