ConMT NX8048K050 with Arduino firmware 1.0.1

Use this matched pair.
  Nextion display       conmt-NX8048K050-CM1-fixed.tft
  Nextion Editor        conmt-NX8048K050-CM1-fixed.HMI
  ATmega328P via ISP    ../arduino/out/ConMT-ATmega328P-ISP-CM1-K050.hex
  ATmega application   ../arduino/out/ConMT-ATmega328P-CM1-K050.hex
  Arduino source       ../arduino/ConMT/ConMT.ino

The ISP file includes the JMP 0 reset entry at 0x7E00 for the ConMT unit
previously verified in this workspace. Both new device files must be installed
to use the matched pair. Device upload has been deferred at the user's request.

The display starts at pInit with a real CM1 handshake at 9600 baud.
Four initialization stages advance at 650 ms intervals. Progress reaches 100%,
stays visible for 700 ms, then automatically opens User Information.
SAVE on User Information opens Main Menu. This follows the React preview flow.

The fixed 85% from the background is covered by live components. A missing MCU
is reported explicitly. An older firmware version is identified on the splash.
Sensor and storage attention states are shown while their checks complete.
Tap the clock in the top-left corner to set date/time; no extra button is drawn.
MCU power loss requires setting its clock again, and CLOCK_SET needs the SD journal.

Device Info shows Firmware Version, Sensors, and a Status pill: READY,
NO SENSOR, or SD ERROR. There is no Retry Storage button.

Tap an input field to open the keyboard. Apply sends the current value to the
MCU and waits for its acknowledgement. Invalid input stays in the editor.
Material quantities and brands, baseline target/datum, lab rows, dates and
measurement checkpoint corrections use the same production CM1 commands.
Rows can be paged by tapping the left or right edge of the list. Destructive actions require the MCU confirmation token.
SAVE commands include the revision being reviewed. BACK uses the documented
page route and preserves a running measurement. Resume is available at selection.

The 17 domain page IDs remain 0 through 16. Six additional local pages provide
input, confirmation, clock setup, checkpoint editing, the baseline curve, and the
Add row sheet.
They keep the original domain page ID in UART requests.

Rebuild the text source with Python, tomli-w and nxwright installed.
  python tools/k050_protocol.py
  nxwright check nxsrc-K050
  nxwright build nxsrc-K050 conmt-NX8048K050-CM1-final.HMI --overwrite --no-lock
  nxwright compile nxsrc-K050 conmt-NX8048K050-CM1-final.tft --overwrite

The generator updates the K050 variant. The default nxsrc folder has its own
earlier generator. Firmware build commands are documented in ../arduino/README.md.
The regression harness is ../arduino/tests/PanelHarness.cpp and the integration
test is tests/test_k050_integration.py. It uses the production parser, engine
and journal with a host raw card image and controlled sensor/clock ports.

The serial connection uses MCU D1/TX to display RX, MCU D0/RX to display TX,
a common GND, and the display's specified 5 V supply.

Physical sensor reliability, SD read/write/recovery and installed-panel operation
still require validation on the real hardware. The firmware now uses the last 1 MiB
of the card as a raw journal, so no CMTLOG.BIN and no FAT formatting are required.
Use a dedicated card: this region is written directly and is outside the partition's
free-space bookkeeping. The onboard microSD slot uses CS D10, MOSI D11, MISO D12,
SCK D13, 3.3 V and GND; the 6-pin ISP header does not carry SD chip select.
Battery percentage needs calibrated thresholds.
Checksums and build evidence are in conmt-NX8048K050-CM1-final.validation.json.
