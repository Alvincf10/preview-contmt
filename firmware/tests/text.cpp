#include "core/Text.h"
#include "core/Flash.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <iostream>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
int main() {
    static const char prefix[] CM_ROM="fc = ";
    for(size_t capacity=0;capacity<96;++capacity) {
        char actual[100],expected[100];
        for(uint32_t value:{0UL,1UL,9UL,10UL,99UL,100UL,123456789UL,4294967295UL}) {
            for(uint8_t digits:{0,2,4,10,14}) {
                std::memset(actual,'?',sizeof(actual)); std::memset(expected,'?',sizeof(expected));
                formatUnsigned(actual,capacity,value,digits); std::snprintf(expected,capacity,"%0*lu",int(digits),static_cast<unsigned long>(value));
                CHECK(!std::memcmp(actual,expected,sizeof(actual)));
            }
            std::memset(actual,'?',sizeof(actual)); std::memset(expected,'?',sizeof(expected));
            formatHms(actual,capacity,value,59,9); std::snprintf(expected,capacity,"%02lu:59:09",static_cast<unsigned long>(value));
            CHECK(!std::memcmp(actual,expected,sizeof(actual)));
        }
        std::memset(actual,'?',sizeof(actual)); std::memset(expected,'?',sizeof(expected));
        Text(actual,capacity).flash(prefix).ram("-29.125").character(' ').character('+').character(' ').ram("6.5272").flash(CM_LITERAL(" ln(M)"));
        std::snprintf(expected,capacity,"fc = -29.125 + 6.5272 ln(M)"); CHECK(!std::memcmp(actual,expected,sizeof(actual)));
        std::memset(actual,'?',sizeof(actual)); std::memset(expected,'?',sizeof(expected));
        copyRam(actual,capacity,"2026-11-17 12:34:56"); std::snprintf(expected,capacity,"%s","2026-11-17 12:34:56"); CHECK(!std::memcmp(actual,expected,sizeof(actual)));
    }
    formatUnsigned(nullptr,0,UINT32_MAX); Text(nullptr,0).ram("safe").flash(prefix).number(UINT32_MAX);
    std::cout<<"Bounded integer, clock and text output matches snprintf including truncation and zero capacity PASS\n";
}
