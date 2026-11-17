#include "core/Battery.h"
#include <cstdlib>
#include <iostream>
using namespace conmt;
#define REQUIRE(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
int main() {
    uint8_t p=255;
    BatteryGauge empty({520,877,991}); REQUIRE(empty.read(p)==Status::Missing);
    REQUIRE(empty.sample(877)==Status::Ok&&empty.read(p)==Status::Ok&&p==0);
    BatteryGauge full({520,877,991}); REQUIRE(full.sample(991)==Status::Ok&&full.read(p)==Status::Ok&&p==100);
    BatteryGauge half({520,877,991}); REQUIRE(half.sample(934)==Status::Ok&&half.read(p)==Status::Ok&&p==50);
    for(unsigned i=0;i<400;++i) { REQUIRE(half.sample(i%2?934:935)==Status::Ok); REQUIRE(half.read(p)==Status::Ok&&p==50); }
    REQUIRE(full.sample(100)==Status::Absent&&full.read(p)==Status::Absent&&p==0);
    REQUIRE(full.sample(934)==Status::Ok&&full.read(p)==Status::Ok&&p==50);
    REQUIRE(full.sample(1024)==Status::Invalid&&full.read(p)==Status::Invalid);
    REQUIRE(full.sample(1023)==Status::Ok&&full.read(p)==Status::Ok&&p==100);
    for(unsigned i=0;i<99;++i) { REQUIRE(full.sample(877)==Status::Ok); REQUIRE(full.read(p)==Status::Ok&&p==100); }
    for(unsigned i=0;i<2000;++i) REQUIRE(full.sample(877)==Status::Ok);
    REQUIRE(full.read(p)==Status::Ok&&p==0);
    BatteryGauge invalid({520,991,877}); REQUIRE(invalid.sample(950)==Status::Invalid);
    std::cout<<"Battery calibration endpoints, noise, confirmation, unplug/replug, bounds PASS\n";
}
