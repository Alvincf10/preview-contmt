#include "core/Text.h"
#include "core/Flash.h"
#include "core/Calendar.h"
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <iostream>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
static void calendarOutputs() {
    struct { uint64_t at; const char* date; const char* clock; Status status; } cases[]={
        {0,"1970-01-01","00:00:00",Status::Ok},
        {86399999,"1970-01-01","23:59:59",Status::Ok},
        {86400000,"1970-01-02","00:00:00",Status::Ok},
        {CalendarLastMs,"2199-12-31","23:59:59",Status::Ok},
        {CalendarLastMs+1,"--","--",Status::Invalid},
    };
    for(const auto& test:cases) {
        char date[12],clock[12];
        CHECK(calendarText(test.at,date,sizeof(date),nullptr,0)==test.status);
        CHECK(calendarText(test.at,nullptr,0,clock,sizeof(clock))==test.status);
        CHECK(!std::strcmp(date,test.date)&&!std::strcmp(clock,test.clock));
    }
}
static void coefficientFormatting() {
    const Real values[]={-10,Real(-.5),Real(-.005),Real(-.000001),Real(-0.0),0,Real(.000001),Real(.005),3,Real(-1e12),NAN,INFINITY};
    for(Real value:values) {
        for(uint8_t digits=0;digits<=6;++digits) {
            for(size_t capacity=1;capacity<=29;++capacity) {
                char actual[32],expected[32];
                std::memset(actual,'?',sizeof(actual));
                std::memset(expected,'?',sizeof(expected));
                formatReal(expected,capacity,value,digits);
                Real rounded;
                if(parseReal(expected,rounded)==Status::Ok&&rounded==0) formatReal(expected,capacity,0,digits);
                formatCoeff(actual,capacity,value,digits);
                CHECK(!std::strcmp(actual,expected));
                CHECK(actual[capacity]==expected[capacity]);
            }
        }
    }
    formatCoeff(nullptr,0,0,0);
}
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
    calendarOutputs();
    coefficientFormatting();
    std::cout<<"Bounded integer, calendar, coefficient and text formatting PASS\n";
}
