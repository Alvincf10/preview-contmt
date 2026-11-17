#pragma once
#include "../hmi/Transport.h"
#ifdef ARDUINO
#include <Arduino.h>
namespace conmt {
class ArduinoUart : public UartPort {
    HardwareSerial& serial_;
public:
    explicit ArduinoUart(HardwareSerial& port) : serial_(port) {}
    int read() override { return serial_.available()?serial_.read():-1; }
    uint16_t writable() override { return uint16_t(serial_.availableForWrite()); }
    uint16_t write(const uint8_t* b,uint16_t n) override { return uint16_t(serial_.write(b,n)); }
};
}
#endif
