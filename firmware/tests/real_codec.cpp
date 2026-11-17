#include "storage/Journal.h"
#include <cmath>
#include <cstring>
#include <iostream>
#include <cstdlib>
#include <limits>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
static uint64_t bits(double value) { uint64_t out; std::memcpy(&out,&value,8); return out; }
static double fromBits(uint64_t value) { double out; std::memcpy(&out,&value,8); return out; }
static void decode(uint64_t pattern) {
    uint8_t bytes[8]; put64(bytes,pattern); Real got=getReal(bytes);
    double source=fromBits(pattern);
    if(!std::isfinite(source)) { CHECK(std::isnan(got)); return; }
    Real expected=Real(source);
    if(got!=expected||std::signbit(got)!=std::signbit(expected)) {
        std::cerr<<"decode pattern="<<std::hex<<pattern<<std::dec<<" got="<<got<<" expected="<<expected<<'\n'; std::exit(1);
    }
}
int main() {
    CHECK(sizeof(double)==8);
    const double edges[]={0.0,-0.0,1.0,-20.25,1e-300,1e300,
        double(std::numeric_limits<float>::denorm_min()),double(std::numeric_limits<float>::min()),double(std::numeric_limits<float>::max()),
        std::ldexp(1.,-150),std::nextafter(std::ldexp(1.,-150),1.),
        std::ldexp(1.,-126)-std::ldexp(1.,-150),1.+std::ldexp(1.,-24),1.+3*std::ldexp(1.,-24)};
    for(double value:edges) { decode(bits(value)); decode(bits(-value)); }
    uint32_t state=1729;
    for(unsigned i=0;i<65536;++i) {
        state=state*1664525u+1013904223u; uint32_t low=state;
        state=state*1664525u+1013904223u;
        decode((uint64_t(state)<<32)|low);
        float sample; std::memcpy(&sample,&state,4);
        if(!std::isfinite(sample)) continue;
        Real value=Real(sample); uint8_t wire[8]; putReal(wire,value);
        CHECK(get64(wire)==bits(double(value)));
        CHECK(getReal(wire)==value&&std::signbit(getReal(wire))==std::signbit(value));
    }
    char out[18]; formatStatus(out,sizeof(out),Status::ConfirmRequired); CHECK(!std::strcmp(out,"ConfirmRequired"));
    std::cout<<"IEEE binary64 storage: 65536 decode/encode cases, rounding/subnormal/signed-zero boundaries PASS\n";
}
