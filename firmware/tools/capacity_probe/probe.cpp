#include "app/Controller.h"
#include "hmi/Transport.h"
#include "board/SdStorage.h"
#include <avr/io.h>
#include <stdlib.h>
#include "board/ArduinoUart.h"
using namespace conmt;
volatile uint8_t probeInput;
class ProbeClock : public ClockPort { public: Time now() override __attribute__((noinline)) { return {uint32_t(probeInput),uint64_t(probeInput),probeInput!=0}; } };
class ProbeSensors : public SensorPort { public: void poll(uint32_t) override {} Status latest(SensorFrame&) override __attribute__((noinline)) { return Status(probeInput); } };
class ProbeDevices : public DevicePort { public: Status battery(uint8_t&) override { return Status(probeInput); } Status brightness(uint8_t) override { return Status(probeInput); } Status sound(bool) override { return Status(probeInput); } };
class ProbeUart : public UartPort { public: int read() override { return probeInput?probeInput:-1; } uint16_t writable() override { return probeInput; } uint16_t write(const uint8_t*,uint16_t n) override { return n; } };
ProbeClock cl;
ProbeSensors se;
ProbeDevices de;
ArduinoUart uart(Serial);
SdStorage storage;
Journal journal(storage);
Repository repository(journal);
Controller controller(repository,cl,se,de);
Transport transport(controller,uart);
int main() {
    storage.begin(probeInput,probeInput);
    controller.boot();
    for(;;) { controller.tick(); transport.poll(probeInput); }
}
