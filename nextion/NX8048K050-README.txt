ConMT NX8048K050 with Arduino firmware 1.0.1

Use this matched pair.
  Nextion display      conmt-NX8048K050-CM1-final.tft
  Nextion Editor       conmt-NX8048K050-CM1-final.HMI
  ATmega328P via ISP    ../arduino/out/ConMT-ATmega328P-ISP.hex
  ATmega application   ../arduino/out/ConMT-ATmega328P.hex
  Arduino source       ../arduino/ConMT/ConMT.ino

The ISP file preserves the 512-byte boot section and JMP 0 reset entry at
0x7E00 read from the ConMT unit. Install the matching TFT and firmware.

The display starts at pInit with a real CM1 handshake at 9600 baud.
Four initialization stages advance at 650 ms intervals. Progress reaches 100%,
stays visible for 700 ms, then automatically opens User Information.
SAVE on User Information opens Main Menu. This follows the React preview flow.

The fixed 85% from the background is covered by live components. A missing MCU
is reported explicitly. An older firmware version is identified on the splash.
Sensor and storage attention states are shown while their checks complete.
Tap the clock badge in User Information or Device Info to set date and time.
The SET CLOCK status in Device Info also opens the same editor. After the
clock is set, the header refreshes from the new MCU status.
The header displays HH:MM and the filtered MCU battery percentage. It displays
--:-- before clock setup and --% when the battery signal is absent.
MCU power loss requires setting its clock again.

Device Info shows the MCU firmware version, connected probe count, and
operating status. The panel communicates over Serial / CM1.

The baseline result plots MCU curve samples and lab measurements in the chart
area. Tap the plot to enlarge it and read R², the pair count and the FKZ age count.

Tap an input field to open the matching keypad. Apply sends the value to the
MCU and waits for its acknowledgement. Invalid input stays in the editor.
The date and time keypads insert separators automatically. Dates appear as
DD-MM-YYYY and travel as YYYY-MM-DD over CM1. Operator, project and baseline
names and brands use the text keyboard. Datum has four numeric choices.
Material quantities and brands, baseline target/datum, lab rows, dates and
measurement checkpoint corrections use the same production CM1 commands.
Maturity Data starts with one editable Day 0 on a fresh draft. + ADD DAY can
add a lab day while Day 0 is empty. The first lab day is saved alongside the
empty Day 0. The newly added row is focused and brought into view. SENSOR
uses the focused row and can fill the original Day 0 immediately. The info
button opens Sample schedule using the MCU's dates. Swipe vertically inside
tables and card lists to move by rows. A short swipe moves one row, while a
long swipe can move several. Short lists show every available row. The
scrollbar appears on overflow. Edit dialogs and history detail restore the
previous list position on return. Deletion and replacement use the MCU
confirmation token.
In Real Time Measurement, + ADD DAY records the current device time and
average of valid probes. Tap REAL TIME MONITORING to see the stored time and
temperature in Logged Days.
Tap a saved baseline card to select it. The confirmed card is highlighted.
START displays missing prerequisites. Test History identifies an empty list.
SAVE commands include the revision being reviewed. BACK uses the documented
page route and preserves a running measurement. Resume is available at selection.

The 17 domain page IDs are 0 through 16. Eight local pages cover text and
numeric input, confirmation, clock setup, checkpoint editing, the baseline
curve, Add day and Sample schedule. UART requests use the domain page ID.

Rebuild from the repository root with Node, Playwright, Chrome, Python 3.11+
with tomli-w, and nxwright. CONMT_PYTHON selects the Python interpreter.
  npm run hmi:k050:source
  nxwright check nextion/nxsrc-K050
  nxwright compile nextion/nxsrc-K050 nextion/conmt-NX8048K050-CM1-final.tft --project-file nextion/conmt-NX8048K050-CM1-final.HMI --no-lock --overwrite

Chrome captures the Preview ConMT artwork at 480 x 800. The export keeps
the Web typography, icons, card and button styles. The generator uses the
same DOM bounds for the panel fields and touch areas. Live values arrive
over CM1. Maturity and saved lists reveal rows as data arrives, using the
matching Web-rendered assets for their controls and selection states.
Add row, Sample schedule and confirmation are captured from the Preview's
dialogs. Long lists fetch visible rows from the MCU and reuse overlapping
rows when scrolling. The export checks that controls fit inside their dialog or panel and
that the expanded chart title, axis label and plot have separate bounds.

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
The MCU retries mount after an I/O failure and writes the journal on the first
storage transaction.
Use a dedicated card: this region is written directly and is outside the partition's
free-space bookkeeping. The onboard microSD slot uses CS D10, MOSI D11, MISO D12,
SCK D13, 3.3 V and GND; the 6-pin ISP header does not carry SD chip select.
The battery gauge uses the A0 calibration in firmware/board-evidence/battery.json.
Verify the displayed percentage with the battery connected to the physical unit.
Checksums and build evidence are in conmt-NX8048K050-CM1-final.validation.json.
