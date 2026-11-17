#pragma once
#include "Types.h"

namespace conmt {
struct BatteryCalibration {
    uint16_t present, empty, full;
};
class BatteryGauge {
    BatteryCalibration calibration_;
    uint16_t filteredQ5_;
    uint8_t percent_, pending_, confirmations_;
    Status status_;
public:
    explicit BatteryGauge(BatteryCalibration calibration)
        : calibration_(calibration), filteredQ5_(0), percent_(0), pending_(0), confirmations_(0), status_(Status::Missing) {}
    Status sample(uint16_t adc);
    Status read(uint8_t& percent) const { percent=percent_; return status_; }
};
}
