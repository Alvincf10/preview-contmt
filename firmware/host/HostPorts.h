#pragma once
#include "storage/Journal.h"
#include "core/Types.h"
#include <vector>
#include <string>
namespace conmt { namespace host {
class MemoryStorage : public StoragePort {
public:
    std::vector<uint8_t> bytes;
    int64_t writeBudget=-1;
    bool absent=false,full=false,failSync=false;
    Status size(uint32_t& v) override;
    Status read(uint32_t at,uint8_t* b,uint16_t n) override;
    Status write(uint32_t at,const uint8_t* b,uint16_t n) override;
    Status truncate(uint32_t n) override;
    Status sync() override;
};
class FileStorage : public StoragePort {
    std::string path_;
    int fd_;
public:
    explicit FileStorage(const std::string& p);
    ~FileStorage();
    Status size(uint32_t& v) override;
    Status read(uint32_t at,uint8_t* b,uint16_t n) override;
    Status write(uint32_t at,const uint8_t* b,uint16_t n) override;
    Status truncate(uint32_t n) override;
    Status sync() override;
};
class FakeClock : public ClockPort {
public:
    Time value{0,1794787200000ULL,true};
    Time now() override { return value; }
    void advance(uint64_t ms) { value.monoMs+=uint32_t(ms); value.wallMs+=ms; }
};
class RecordedSensor : public SensorPort {
public:
    SensorFrame frame;
    bool fresh=true;
    RecordedSensor() { frame.validMask=7; frame.channel[0]=20; frame.channel[1]=20; frame.channel[2]=20; }
    void poll(uint32_t now) override { if(fresh) frame.sampledMonoMs=now; }
    Status latest(SensorFrame& f) override { f=frame; return Status::Ok; }
};
class Devices : public DevicePort {
public:
    uint8_t light=0; bool audible=false;
    Status battery(uint8_t&) override { return Status::Unsupported; }
    Status brightness(uint8_t n) override { light=n; return Status::Ok; }
    Status sound(bool n) override { audible=n; return Status::Ok; }
};
}}
