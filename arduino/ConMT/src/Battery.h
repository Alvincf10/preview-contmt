#pragma once

#include <stdint.h>

namespace conmt {

class BatteryGauge {
public:
  void sample(uint16_t adc) {
    const bool first = percent_ < 0;
    if (adc < Present) {
      percent_ = -1;
      confirmations_ = 0;
      return;
    }
    if (first) filteredQ5_ = adc << 5;
    else filteredQ5_ += static_cast<int16_t>(adc) - static_cast<int16_t>(filteredQ5_ >> 5);

    const uint16_t filtered = filteredQ5_ >> 5;
    const uint16_t span = Full - Empty;
    const uint8_t candidate = filtered <= Empty ? 0 : filtered >= Full ? 100 :
                              ((filtered - Empty) * 100 + span / 2) / span;
    if (first || candidate == percent_) {
      percent_ = candidate;
      confirmations_ = 0;
    } else if (candidate != pending_) {
      pending_ = candidate;
      confirmations_ = 1;
    } else if (++confirmations_ >= 100) {
      percent_ = candidate;
      confirmations_ = 0;
    }
  }

  int8_t percent() const { return percent_; }

private:
  // ADC calibration from firmware/board-evidence/battery.json.
  static constexpr uint16_t Present = 520, Empty = 877, Full = 991;
  uint16_t filteredQ5_ = 0;
  int8_t percent_ = -1;
  uint8_t pending_ = 0, confirmations_ = 0;
};

}  // namespace conmt
