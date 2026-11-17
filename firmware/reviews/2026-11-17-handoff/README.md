# Checkpoint handoff, 17 November 2026

The user paused implementation and requested a plan for Sol. The local handoff is `docs/firmware-plan/08_REMAINING_AND_SIZE_PLAN.md`; the planning directory remains intentionally ignored by Git. It must be handed over separately if Sol uses a remote clone.

Since checkpoint72697e1, constant text/table reads and transport variable names moved to explicit flash access; the static flashText scratch buffer was removed. Key construction is shared. The journal index now also finds committed operation IDs, avoiding a full journal scan for retry checks. Kind0/field0 are reserved for index metadata and rejected in journal data. Record schema and CM1 contract2 are unchanged.

The operation lookup benchmark reads344bytes with the index versus26,412bytes scanning300transactions. It also tests epoch separation, duplicate rejection, missing/corrupt sidecar recovery and committed payload corruption. This is a host byte count, not a physical SD latency result. Large index chains, boot rebuilding and synchronous workflows remain unresolved.

All10CTest suites pass on host64, host32 and ASan/UBSan after the final code changes. The added wire snapshot covers all17pages and retains441lines captured before the presenter optimizations. Existing65audit cases and numerical fixture tests still pass. No new physical hardware test or full firmware flash was performed. AVR numeric emulation is prior evidence for unchanged formulas; the changed PROGMEM/presenter path still needs a dedicated AVR runtime test.

Full capacity probe: **80,748flash bytes /1,582static SRAM bytes**; physical target32,768/2,048. Compared with72697e1 this saves358flash bytes and182SRAM bytes, including the new operation index. Deficit remains47,980flash bytes; static stack margin466bytes is not proof of safe nested execution. Non-LTO largest function frames include START187 and renderField166bytes. Probe excludes verified sensor/RTC and finished panel chart integration.

Acceptance status remains73HOST_PASS,1EMULATED_PASS,21PARTIAL,2NOT_IMPLEMENTED,3HARDWARE_PENDING,2FAIL. The additional regressions do not turn physical/latency/layout requirements into PASS.

Next work: the local plan orders measured presenter/controller/storage restructuring, shared workspace and bounded jobs, real driver/HMI completion, then target and physical acceptance. It makes no promise that flags alone can remove the59.4% flash overflow. Features, mathematical precision and MCU remain unchanged.

Current machine-readable results: `firmware/releases/status.json`, `avr-capacity.json`, `avr-stack.json`. Test logs remain local ignored build artifacts under the previous production review directory. No HEX production release has been issued.
