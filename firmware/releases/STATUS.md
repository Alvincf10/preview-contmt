# Current ConMT implementation status

Updated17November2026 after flash optimization resumed from520a74f. **Not ready for ATmega328P production.** See the [current implementation review](../reviews/2026-11-17-flash-fit/README.md).

New work: shared transaction execution for four workflows, streamed schema1 record codecs, smaller temporary buffers, bounded text formatting and shared field/settings rules. All15CTest suites pass on host64,host32 and sanitizer.300line workflow traces match520a74f on each precision profile, including120fault scenarios. The existing17page wire fixture remains unchanged.

| Measurement | Flash bytes | Static SRAM bytes |
|---|---:|---:|
|Historical production ELF comparison only|31288|1249|
|Previous audited ConMT implementation|79884|1685|
|Battery/index checkpoint72697e1|81106|1764|
|Starting handoff including operation index|80748|1582|
|Previous optimization/session checkpoint520a74f|78274|1502|
|Current retained implementation|75414|1502|

The current capacity probe exceeds physical328Pflash by42646bytes and leaves546bytes of static SRAM margin before nested stack/interrupts. It saves2860flash bytes from520a74f. It includes real SD, disk index, HardwareSerial and calibrated battery acquisition; sensor/RTC and brightness/sound still use explicitly labelled probe ports.16MHz is a probe assumption, not a verified board clock. Finished chart integration is also pending.

Several stack frames were reduced, but the full worst-case stack is not proven. CAPACITY_ONLY.elf uses enlarged link regions only after the physical328Pregion check fails; it is not an uploadable328Pfirmware. No production HEX is issued.

Battery calibration provenance: [battery.json](../board-evidence/battery.json). Electrical battery validation is pending. CMT.IDXis rebuildable and host-tested; worst-case index/storage scheduling is still open. Sensor/RTC BoardBinding, paired HMI/TFT and physical integration/soak are unfinished. No flashing has occurred.

Latest102scenario assessment:77HOST_PASS,1EMULATED_PASS,17PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL.24scenarios remain incomplete. W01all-field/native-extreme codec roundtrip now passes host tests. Host PASS is not hardware acceptance. AVR precision/PROGMEM tests pass620numeric cases and a separate streamed-record test image; entire presenter runtime is still pending.
