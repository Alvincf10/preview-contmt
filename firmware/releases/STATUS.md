# Current ConMT implementation status

Updated 18 November 2026 for `optimize/conmt-flash-parity`. **ATmega328P capacity and board integration are still open.** See the [offline storage fit review](../reviews/2026-11-18-offline-storage-fit/README.md) and the [dispatch/journal parity review](../reviews/2026-11-18-flash-parity/README.md).

Schema1 key bytes, index traversal, and integer codecs are shared. All 15 CTest suites pass on host64, host32 and sanitizer. The 300-line workflow traces match `f7aea07` for each precision, including 120 write-cut scenarios. The original UART fixture for 17 pages and production features are preserved.

| Measurement | Flash bytes | Static SRAM bytes |
|---|---:|---:|
|Historical production ELF comparison only|31288|1249|
|Previous audited ConMT implementation|79884|1685|
|Battery/index checkpoint72697e1|81106|1764|
|Starting handoff including operation index|80748|1582|
|Previous optimization/session checkpoint520a74f|78274|1502|
|Previous retained implementation, old probe|75414|1502|
|Same previous source remeasured with stronger probe|75554|1532|
|Previous retained implementation, stronger probe|74618|1532|
|Branch following dispatch, journal and formatter changes|74082|1531|
|Current branch following offline storage changes|73394|1531|

The current capacity probe exceeds physical ATmega328P flash by 40,626 bytes and leaves 517 bytes of static SRAM margin before nested stack and interrupts. The latest changes save 688 flash bytes on the same probe. The diagnostic SD, numeric, codec, and storage subset drops from 42,208 to 41,606 bytes. The probe includes real SD, disk index, HardwareSerial and calibrated battery acquisition. Sensor, RTC, brightness and sound still use labelled probe ports, with 16 MHz used as a measurement assumption. Finished chart integration is also pending.

Several stack frames were reduced, but the full worst-case stack is not proven. CAPACITY_ONLY.elf uses enlarged link regions only after the physical328Pregion check fails; it is not an uploadable328Pfirmware. No production HEX is issued.

Battery calibration provenance: [battery.json](../board-evidence/battery.json). Electrical battery validation is pending. CMT.IDXis rebuildable and host-tested; worst-case index/storage scheduling is still open. Sensor/RTC BoardBinding, paired HMI/TFT and physical integration/soak are unfinished. No flashing has occurred.

Latest102scenario assessment:77HOST_PASS,1EMULATED_PASS,17PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL.24scenarios remain incomplete. W01all-field/native-extreme codec roundtrip now passes host tests. Host PASS is not hardware acceptance. AVR precision/PROGMEM tests pass620numeric cases and a separate streamed-record test image; entire presenter runtime is still pending.

Hypothetical feature cuts were measured only in isolated source copies. Even their combined study image uses61754bytes. These are not functional release candidates, and no feature cuts were applied to production source.
