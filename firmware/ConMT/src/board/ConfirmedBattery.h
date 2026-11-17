#pragma once
#include "ArduinoBattery.h"
#ifdef ARDUINO
namespace conmt {
// User-confirmed battery circuit from the 2026-09-22 production sketch.
class ConfirmedBattery : public ArduinoBattery {
public:
    ConfirmedBattery() : ArduinoBattery(A0,BatteryCalibration{520,877,991}) {}
};
}
#endif
