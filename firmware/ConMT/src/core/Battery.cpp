#include "Battery.h"
namespace conmt {
Status BatteryGauge::sample(uint16_t adc) {
    if(adc>1023 || calibration_.present>=calibration_.empty || calibration_.empty>=calibration_.full || calibration_.full>1023)
        return status_=Status::Invalid;
    if(adc<calibration_.present) {
        filteredQ5_=uint16_t(adc<<5); percent_=pending_=confirmations_=0;
        return status_=Status::Absent;
    }
    if(status_!=Status::Ok) filteredQ5_=uint16_t(adc<<5);
    else filteredQ5_=uint16_t(int32_t(filteredQ5_)+int16_t(adc)-int16_t(filteredQ5_>>5));
    uint16_t filtered=filteredQ5_>>5, span=calibration_.full-calibration_.empty;
    uint8_t candidate=filtered<=calibration_.empty?0:(filtered>=calibration_.full?100:
        uint8_t((uint32_t(filtered-calibration_.empty)*100+span/2)/span));
    if(status_!=Status::Ok) { percent_=pending_=candidate; confirmations_=0; }
    else if(candidate==percent_) { pending_=candidate; confirmations_=0; }
    else if(candidate!=pending_) { pending_=candidate; confirmations_=1; }
    else if(++confirmations_>=100) { percent_=candidate; confirmations_=0; }
    return status_=Status::Ok;
}
}
