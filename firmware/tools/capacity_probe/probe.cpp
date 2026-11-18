#include "app/Controller.h"
#include "hmi/Transport.h"
#include "board/SdStorage.h"
#include <avr/io.h>
#include <stdlib.h>
#include "board/ArduinoUart.h"
#include "board/BatteryDevices.h"
using namespace conmt;
volatile uint8_t probeInput;
struct ProbeInputs {
    uint32_t mono,sampledMono;
    uint64_t wall;
    Real channel[3];
    uint8_t validMask;
    bool clockValid;
};
volatile ProbeInputs probeState;
class ProbeClock : public ClockPort { public: Time now() override __attribute__((noinline)) { return {probeState.mono,probeState.wall,probeState.clockValid}; } };
class ProbeSensors : public SensorPort {
public:
    void poll(uint32_t) override {}
    Status latest(SensorFrame& frame) override __attribute__((noinline)) {
        frame.sampledMonoMs=probeState.sampledMono; frame.validMask=probeState.validMask;
        for(uint8_t i=0;i<3;++i) frame.channel[i]=probeState.channel[i];
        return Status(probeInput);
    }
};
class ProbeDevices : public DevicePort { public: Status battery(uint8_t&) override { return Status(probeInput); } Status brightness(uint8_t) override { return Status(probeInput); } Status sound(bool) override { return Status(probeInput); } };
class ProbeUart : public UartPort { public: int read() override { return probeInput?probeInput:-1; } uint16_t writable() override { return probeInput; } uint16_t write(const uint8_t*,uint16_t n) override { return n; } };
ProbeClock cl;
ProbeSensors se;
ProbeDevices de;
BatteryDevices batteryDevices(de);
ArduinoUart uart(Serial);
SdStorage storage;
Journal journal(storage);
Repository repository(journal);
Controller controller(repository,cl,se,batteryDevices);
Transport transport(controller,uart);
int main() {
    storage.begin(probeInput,probeInput);
    controller.boot();
    for(;;) { controller.tick(); transport.poll(probeInput); }
}
