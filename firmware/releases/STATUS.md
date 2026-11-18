# Current ConMT implementation status

Updated18November2026 after further optimization fromc1ebca9. **Not ready for ATmega328P production.** See the [current implementation review](../reviews/2026-11-18-size-study/README.md) and the [feature choices, not implemented](../reviews/2026-11-18-size-study/FEATURE_CHOICES.md).

New work: one checkpoint replay implementation, scoped replay temporaries and one reused journal verification buffer. All15CTest suites pass on host64,host32 and sanitizer.300line workflow traces match520a74f on each precision profile, including120fault scenarios. The existing17page wire fixture remains unchanged. No production feature was removed.

| Measurement | Flash bytes | Static SRAM bytes |
|---|---:|---:|
|Historical production ELF comparison only|31288|1249|
|Previous audited ConMT implementation|79884|1685|
|Battery/index checkpoint72697e1|81106|1764|
|Starting handoff including operation index|80748|1582|
|Previous optimization/session checkpoint520a74f|78274|1502|
|Previous retained implementation, old probe|75414|1502|
|Same previous source remeasured with stronger probe|75554|1532|
|Current retained implementation, stronger probe|74618|1532|

The current capacity probe exceeds physical328Pflash by41850bytes and leaves516bytes of static SRAM margin before nested stack/interrupts. Further code optimization saves936bytes on comparable measurements. The stronger probe now fills sensor frames and uses full-width clock inputs; this adds140flash/30SRAM bytes to both comparison builds, including31SRAM bytes of measurement inputs. It includes real SD, disk index, HardwareSerial and calibrated battery acquisition; sensor/RTC and brightness/sound still use explicitly labelled probe ports.16MHz is a probe assumption, not a verified board clock. Finished chart integration is also pending.

Several stack frames were reduced, but the full worst-case stack is not proven. CAPACITY_ONLY.elf uses enlarged link regions only after the physical328Pregion check fails; it is not an uploadable328Pfirmware. No production HEX is issued.

Battery calibration provenance: [battery.json](../board-evidence/battery.json). Electrical battery validation is pending. CMT.IDXis rebuildable and host-tested; worst-case index/storage scheduling is still open. Sensor/RTC BoardBinding, paired HMI/TFT and physical integration/soak are unfinished. No flashing has occurred.

Latest102scenario assessment:77HOST_PASS,1EMULATED_PASS,17PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL.24scenarios remain incomplete. W01all-field/native-extreme codec roundtrip now passes host tests. Host PASS is not hardware acceptance. AVR precision/PROGMEM tests pass620numeric cases and a separate streamed-record test image; entire presenter runtime is still pending.

Hypothetical feature cuts were measured only in isolated source copies. Even their combined study image uses61754bytes. These are not functional release candidates, and no feature cuts were applied to production source.
