#pragma once
#ifdef ARDUINO
#include <Arduino.h>
#include "../core/Battery.h"

namespace conmt {
class ArduinoBattery {
    BatteryGauge gauge_;
    uint32_t lastSample_;
    uint8_t pin_;
    bool sampled_;
public:
    ArduinoBattery(uint8_t pin,BatteryCalibration calibration)
        : gauge_(calibration),lastSample_(0),pin_(pin),sampled_(false) {}
    void poll(uint32_t now) {
        if(sampled_ && uint32_t(now-lastSample_)<100) return;
        analogRead(pin_);
        uint16_t total=0;
        for(uint8_t i=0;i<8;++i) total+=uint16_t(analogRead(pin_));
        gauge_.sample(uint16_t((total+4)/8)); lastSample_=now; sampled_=true;
    }
    Status read(uint32_t now,uint8_t& percent) const {
        percent=0;
        if(!sampled_) return Status::Missing;
        if(uint32_t(now-lastSample_)>500) return Status::Stale;
        return gauge_.read(percent);
    }
};
}
#endif
