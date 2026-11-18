# ConMT workflow and journal measurement

The implementation at `3aff8f8` reduces the application capacity probe from **73,394 to 72,770 flash bytes** against `38a47aa`. Static SRAM is **1,531 bytes**. The physical-region link still overflows the ATmega328P by **40,002 bytes**. The probe includes real SD, disk index, UART, and the calibrated battery adapter. Verified sensor and RTC drivers, the paired HMI and chart integration, and runtime stack verification remain open. [Capacity report](../../releases/avr-capacity.json), [symbol attribution](../../releases/size-breakdown.json)

## Changes kept

- One journal traversal checks the existing transaction CRC and locates values, operation IDs, or the maximum object ID. An index hit must point to an actual entry in that transaction. The fallback uses the same traversal when the index is unavailable or the entry reference cannot be matched. Schema1 encoding, read-back checks, and commit order are preserved.
- `GENERATE` validates rows during the two-pass fit. `SAVE` checks the same rules before copying a draft. Both require the existing header fields, three rows, temperatures, and consistent day order. `NEXT` reuses the loaded fit and FKZ selection while applying the existing result rounding rule.
- Day0 insertion and `FILL 0–6H` build a six-byte map of occupied half-hour slots in one scan. Add, manual edit, and sensor capture share the transaction that saves a row and invalidates the generated model. Manual text, revision, and write order are preserved.

| Probe checkpoint | Flash bytes | Static SRAM bytes |
|---|---:|---:|
| Baseline `38a47aa` reproduced | 73,394 | 1,531 |
| Shared verified lookup | 73,126 | 1,531 |
| Shared row writes, Day0 scan, and prediction read | 72,836 | 1,531 |
| Validation during row traversal and fit | 72,770 | 1,531 |

The same AVR-GCC 7.3.0 toolchain, flags, and probe source were used in each link. `Journal::findEntry` falls from 82 to 35 bytes in the non-LTO frame estimates, and `verify` stays at 68 bytes. `saveBaseline` rises from 43 to 74 bytes while the separate 155-byte draft validator is removed. The header validator uses 91 bytes. These estimates are per function. The remaining 517 bytes of static SRAM margin still need to cover nested calls and interrupt stack. [Stack frames](../../releases/avr-stack.json)

## Read volume on the same host workflow

The host run starts an empty journal and uses a 13-row draft, the disk index, one session, and one checkpoint. The table counts bytes requested from both the journal and index during each operation. Physical SD latency depends on sector caching, the card, and the board.

| Action | Before | After |
|---|---:|---:|
| First `FILL 0–6H` | 48,109 | 33,289 |
| Repeat `FILL 0–6H` | 97,644 | 8,244 |
| `GENERATE` | 119,636 | 71,673 |
| Save baseline | 55,493 | 50,885 |
| `START` | 10,141 | 10,045 |
| `NEXT` | 270,054 | 249,654 |
| `SAVE RESULT` | 15,497 | 15,209 |

## Verification

- All 15 suites pass on host64, host binary32, and ASan/UBSan. The existing UART fixture for 17 pages and the transaction traces including 120 write interruptions match their original expected bytes. Tests also cover a misaligned reference in the disk index, one scan per fallback lookup, and rejected incomplete drafts with no commit. [UART fixture](../../tests/fixtures/hmi-wire.txt), [disk index tests](../../tests/disk_index.cpp), [workflow tests](../../tests/workflow.cpp)
- Both 41-row numeric datasets and the 620-case precision suite pass in AVR emulation. The preview sources, client references, ConMT math code, and HMI artifacts were preserved. [Numeric report](../../releases/avr-numeric.json), [precision report](../../releases/avr-precision.json)
