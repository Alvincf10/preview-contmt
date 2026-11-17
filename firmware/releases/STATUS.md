# Current ConMT implementation status

Updated17November2026 after commit0b55090. **Not ready for ATmega328P production.**

New work: calibrated A0battery adapter connected to the production controller, rebuildable CMT.IDX disk index,32byte streaming record copy, shared command table, reduced stack frames. All9CTest suites pass on host64,host32 and sanitizer, including the indexed reference workflow. [Details and remaining work](../reviews/2026-11-17-production/README.md).

| Measurement | Flash bytes | Static SRAM bytes |
|---|---:|---:|
|Historical production ELF comparison only|31288|1249|
|Previous audited ConMT implementation|79884|1685|
|Current implementation including battery/index|81106|1764|

The current capacity probe exceeds physical328Pflash by48338bytes and leaves284bytes of static SRAM margin before nested stack/interrupts. It includes real SD, disk index, HardwareSerial and calibrated battery acquisition; sensor/RTC and brightness/sound still use explicitly labelled probe ports.16MHz is a probe assumption, not a verified board clock.

Several stack frames were reduced, but the full worst-case stack is not proven. CAPACITY_ONLY.elf uses enlarged link regions only after the physical328Pregion check fails; it is not an uploadable328Pfirmware. No production HEX is issued.

Battery calibration provenance: [battery.json](../board-evidence/battery.json). Electrical battery validation is pending. CMT.IDXis rebuildable and host-tested; worst-case index/storage scheduling is still open. Sensor/RTC BoardBinding, paired HMI/TFT and physical integration/soak are unfinished. No flashing has occurred.

Latest102scenario assessment:73HOST_PASS,1EMULATED_PASS,21PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL. Host PASS is not hardware acceptance.
