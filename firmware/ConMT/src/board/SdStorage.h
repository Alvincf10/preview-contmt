#pragma once
#include "../storage/Journal.h"
#ifdef ARDUINO
#include <SD.h>
namespace conmt {
class SdIndexStorage : public StoragePort {
    SdFile file_;
public:
    void close() { if(file_.isOpen()) file_.close(); }
    bool open(SdFile& root) { return file_.open(&root,"CMT.IDX",O_CREAT|O_RDWR); }
    Status size(uint32_t& n) override { n=file_.fileSize(); return file_.isOpen()?Status::Ok:Status::Absent; }
    Status read(uint32_t at,uint8_t* bytes,uint16_t n) override { return file_.isOpen()&&file_.seekSet(at)&&file_.read(bytes,n)==n?Status::Ok:Status::IoError; }
    Status write(uint32_t at,const uint8_t* bytes,uint16_t n) override { file_.clearWriteError(); return file_.isOpen()&&file_.seekSet(at)&&file_.write(bytes,n)==n&&!file_.getWriteError()?Status::Ok:Status::IoError; }
    Status truncate(uint32_t n) override { return file_.isOpen()&&file_.truncate(n)?Status::Ok:Status::IoError; }
    Status sync() override { return file_.isOpen()&&file_.sync()?Status::Ok:Status::IoError; }
};
class SdStorage : public StoragePort {
    Sd2Card card_; SdVolume volume_; SdFile file_;
    SdIndexStorage index_;
    bool ready_,configured_; uint8_t cs_,rate_;
    Status failed(Status fallback=Status::IoError);
public:
    StoragePort* indexStorage() override { return &index_; }
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
