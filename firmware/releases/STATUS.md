# Current ConMT implementation status

Updated17November2026 after implementation resumed from0e45cb1. **Not ready for ATmega328P production.** See the [current implementation review](../reviews/2026-11-17-optimization/README.md).

New work: shared descriptor presenter, controller/record access, journal traversal and maximum-ID index, streamed HMI output, corrected IEEE decoding, live anchors after manual edits and durable clock events. All12CTest suites pass on host64,host32 and sanitizer. The existing17page wire fixture remains unchanged.

| Measurement | Flash bytes | Static SRAM bytes |
|---|---:|---:|
|Historical production ELF comparison only|31288|1249|
|Previous audited ConMT implementation|79884|1685|
|Battery/index checkpoint72697e1|81106|1764|
|Starting handoff including operation index|80748|1582|
|Current implementation after optimization/session fixes|78274|1502|

The current capacity probe exceeds physical328Pflash by45506bytes and leaves546bytes of static SRAM margin before nested stack/interrupts. It includes real SD, disk index, HardwareSerial and calibrated battery acquisition; sensor/RTC and brightness/sound still use explicitly labelled probe ports.16MHz is a probe assumption, not a verified board clock. Finished chart integration is also pending.

Several stack frames were reduced, but the full worst-case stack is not proven. CAPACITY_ONLY.elf uses enlarged link regions only after the physical328Pregion check fails; it is not an uploadable328Pfirmware. No production HEX is issued.

Battery calibration provenance: [battery.json](../board-evidence/battery.json). Electrical battery validation is pending. CMT.IDXis rebuildable and host-tested; worst-case index/storage scheduling is still open. Sensor/RTC BoardBinding, paired HMI/TFT and physical integration/soak are unfinished. No flashing has occurred.

Latest102scenario assessment:76HOST_PASS,1EMULATED_PASS,18PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL.25scenarios remain incomplete. Host PASS is not hardware acceptance. The new AVR precision/PROGMEM smoke test passes620cases; entire presenter runtime is still pending.
