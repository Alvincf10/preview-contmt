#include "app/Controller.h"
#include "HostPorts.h"
#include <iostream>
#include <cstdlib>
using namespace conmt;

// The splash screen's job: check the sensors, the clock and the hardware, show
// what it found, and only then let the panel move on. These tests pin that down,
// because a splash that moves on regardless would hide a dead sensor behind the
// first page.

#define REQUIRE(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<"\n"; std::exit(1); } } while(0)
#define PASS(x) REQUIRE((x)==Status::Ok)

// A sensor that reports a reading the panel can trust.
class LiveSensor : public SensorPort {
public:
    SensorFrame frame;
    bool present = true;
    LiveSensor() { frame.validMask = 7; frame.channel[0] = 25; frame.channel[1] = 26; frame.channel[2] = 27; }
    void poll(uint32_t now) override { frame.sampledMonoMs = now; }
    Status latest(SensorFrame& f) override { f = frame; return present ? Status::Ok : Status::NoSensor; }
};

// A sensor that is there but has nothing to say yet.
class SilentSensor : public SensorPort {
public:
    SensorFrame frame;
    void poll(uint32_t) override {}
    Status latest(SensorFrame& f) override { f = frame; return Status::Ok; }
};

// A clock that does not know the time.
class DeadClock : public ClockPort {
public:
    Time now() override { Time t; t.monoMs = 0; t.wallMs = 0; t.valid = false; return t; }
};

static void the_panel_starts_on_its_splash() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    host::FakeClock clock; LiveSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    PASS(app.boot());
    REQUIRE(app.page() == Page::Init);
    std::cout << "starts on the splash PASS\n";
}

static void a_ready_panel_moves_on_from_the_splash() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    host::FakeClock clock; LiveSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    PASS(app.boot());
    REQUIRE(app.page() == Page::Init);
    sensor.poll(clock.value.monoMs);
    PASS(app.dispatch("SELF_CHECK"));
    REQUIRE(app.page() == Page::User);
    std::cout << "ready panel moves on PASS\n";
}

static void a_missing_sensor_holds_the_panel_on_the_splash() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    host::FakeClock clock; LiveSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    PASS(app.boot());
    sensor.present = false;
    REQUIRE(app.dispatch("SELF_CHECK") == Status::NoSensor);
    REQUIRE(app.page() == Page::Init);
    std::cout << "missing sensor holds the splash PASS\n";
}

static void a_sensor_with_no_reading_holds_the_panel_on_the_splash() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    host::FakeClock clock; SilentSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    PASS(app.boot());
    // The port answers, but its frame has no sample, so the average is unusable.
    REQUIRE(app.dispatch("SELF_CHECK") == Status::NoSensor);
    REQUIRE(app.page() == Page::Init);
    std::cout << "silent sensor holds the splash PASS\n";
}

static void a_dead_clock_holds_the_panel_on_the_splash() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    DeadClock clock; LiveSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    app.boot();
    sensor.poll(0);
    REQUIRE(app.dispatch("SELF_CHECK") == Status::NoClock);
    REQUIRE(app.page() == Page::Init);
    std::cout << "dead clock holds the splash PASS\n";
}

static void the_check_reports_which_part_failed() {
    host::MemoryStorage io; Journal j(io); Repository r(j);
    host::FakeClock clock; LiveSensor sensor; host::Devices devices;
    Controller app(r, clock, sensor, devices);
    PASS(app.boot());
    sensor.poll(clock.value.monoMs);

    Status sensors, clockStatus, deviceStatus;
    PASS(app.selfCheck(sensors, clockStatus, deviceStatus));
    REQUIRE(sensors == Status::Ok);
    REQUIRE(clockStatus == Status::Ok);

    sensor.present = false;
    REQUIRE(app.selfCheck(sensors, clockStatus, deviceStatus) == Status::NoSensor);
    REQUIRE(sensors != Status::Ok);
    REQUIRE(clockStatus == Status::Ok);
    std::cout << "check names the failing part PASS\n";
}

int main() {
    the_panel_starts_on_its_splash();
    a_ready_panel_moves_on_from_the_splash();
    a_missing_sensor_holds_the_panel_on_the_splash();
    a_sensor_with_no_reading_holds_the_panel_on_the_splash();
    a_dead_clock_holds_the_panel_on_the_splash();
    the_check_reports_which_part_failed();
    std::cout << "splash self-check PASS\n";
    return 0;
}
