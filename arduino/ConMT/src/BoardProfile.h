#pragma once

// Maturity Control LCD.pdf, revision 1.0. The clock and MCU are verified from
// the drawing. OneWire ROM/scratchpad checks qualify each temperature sensor.
#ifndef CONMT_PANEL_BAUD
#define CONMT_PANEL_BAUD 9600UL
#endif
#ifndef CONMT_BANDGAP_MV
#define CONMT_BANDGAP_MV 1100UL
#endif

namespace conmt {
namespace pins {
constexpr uint8_t Temperature = 2;
constexpr uint8_t Buzzer = 3;
constexpr uint8_t SdSelect = 10;
constexpr uint8_t VinSense = A0;
}  // namespace pins
}  // namespace conmt
