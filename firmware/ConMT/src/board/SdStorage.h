#pragma once
#include "../storage/Journal.h"
#ifdef ARDUINO
#include <SD.h>
namespace conmt {
class SdStorage : public StoragePort {
    Sd2Card card_; SdVolume volume_; SdFile root_,file_;
    bool ready_,configured_; uint8_t cs_,rate_;
    Status failed(Status fallback=Status::IoError);
public:
    SdStorage() : ready_(false),configured_(false),cs_(0),rate_(0) {}
    Status begin(uint8_t chipSelect,uint8_t spiRate);
    Status reopen() override { return configured_?begin(cs_,rate_):Status::Invalid; }
    Status size(uint32_t& out) override;
    Status read(uint32_t at,uint8_t* out,uint16_t size) override;
    Status write(uint32_t at,const uint8_t* data,uint16_t size) override;
    Status truncate(uint32_t size) override;
    Status sync() override;
};
}
#endif
