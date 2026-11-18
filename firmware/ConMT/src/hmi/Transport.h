#pragma once
#include "../app/Controller.h"
namespace conmt {
static const uint8_t HmiContractVersion=2;
class UartPort {
protected:
    ~UartPort() {}
public:
    virtual int read()=0;
    virtual uint16_t writable()=0;
    virtual uint16_t write(const uint8_t* bytes,uint16_t size)=0;
};
struct Frame {
    uint32_t boot,seq,view;
    uint8_t page,argc;
    const char* verb;
    const char* args[3];
};
class Parser {
    char buffer_[192];
    static_assert(sizeof(buffer_)<=UINT8_MAX+1u,"Parser index must span the frame buffer");
    uint8_t used_;
    uint32_t lastAt_;
    bool dropping_;
public:
    Parser() : used_(0),lastAt_(0),dropping_(false) {}
    Status feed(uint8_t byte,uint32_t now,Frame& out);
    void expire(uint32_t now);
};
class Transport {
    Controller& app_; UartPort& uart_;
    Parser parser_;
    char component_[18],value_[80];
    uint8_t componentSize_,valueSize_,txMode_;
    uint8_t txSize_,txAt_,phase_,actualPage_;
    uint16_t field_;
    uint32_t seq_,ackBoot_,viewSent_,lastRefresh_,renderView_,lastRequestCrc_;
    uint64_t lastOperation_;
    Real sensorCache_[3],averageCache_;
    uint8_t sensorMask_;
    Status sensorStatus_,lastAck_;
    Status ack_;
    bool dirty_,ackPending_,compatible_,full_,seenConnection_;
    Status encode();
    Status numeric(const char* component,uint32_t value);
    bool renderField(uint16_t index,char* component,size_t cc,char* value,size_t vc);
    void accept(const Frame& frame);
    void flush();
    void receive(uint32_t now) __attribute__((noinline));
    bool renderNext() __attribute__((noinline));
public:
    Transport(Controller& app,UartPort& uart);
    void poll(uint32_t now);
    void refresh() { dirty_=true; full_=true; }
};
}
