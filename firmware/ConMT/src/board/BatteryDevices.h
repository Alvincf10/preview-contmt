#pragma once
#include "ConfirmedBattery.h"
#ifdef ARDUINO
namespace conmt {
class BatteryDevices : public DevicePort {
    DevicePort& board_;
    ConfirmedBattery battery_;
public:
    explicit BatteryDevices(DevicePort& board) : board_(board) {}
    void poll(uint32_t now) override { board_.poll(now); battery_.poll(now); }
    Status battery(uint8_t& value) override { return battery_.read(millis(),value); }
    Status brightness(uint8_t value) override { return board_.brightness(value); }
    Status sound(bool enabled) override { return board_.sound(enabled); }
};
}
#endif
