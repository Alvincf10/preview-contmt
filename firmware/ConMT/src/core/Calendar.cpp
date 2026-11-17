#include "Flash.h"
#include "Calendar.h"
#include "Text.h"
#include <string.h>
#include <stdio.h>
namespace conmt {
static bool leap(unsigned y) { return y%4==0 && (y%100!=0 || y%400==0); }
static unsigned daysIn(unsigned y,unsigned m) {
    static const uint8_t d[] CM_ROM={31,28,31,30,31,30,31,31,30,31,30,31};
    return flashValue(d+m-1)+(m==2 && leap(y)?1:0);
}
static bool decimal(const char* s,unsigned n,unsigned& value) {
    value=0; for(unsigned i=0;i<n;++i) { if(s[i]<'0'||s[i]>'9') return false; value=value*10+unsigned(s[i]-'0'); } return true;
}
Status parseClock(const char* s,uint32_t& sec) {
    size_t n=strlen(s); if(n!=5 && n!=8) return Status::Invalid;
    unsigned h,m,x=0;
    if(s[2]!=':' || !decimal(s,2,h) || !decimal(s+3,2,m) || h>23 || m>59) return Status::Invalid;
    if(n==8 && (s[5]!=':' || !decimal(s+6,2,x) || x>59)) return Status::Invalid;
    sec=h*3600UL+m*60+x; return Status::Ok;
}
Status parseDate(const char* s,uint64_t& ms) {
    unsigned y,m,d;
    if(strlen(s)!=10 || s[4]!='-'||s[7]!='-' || !decimal(s,4,y)||!decimal(s+5,2,m)||!decimal(s+8,2,d)) return Status::Invalid;
    if(y<1970||y>2199||m<1||m>12||d<1||d>daysIn(y,m)) return Status::Invalid;
    uint32_t days=0;
    for(unsigned i=1970;i<y;++i) days+=leap(i)?366:365;
    for(unsigned i=1;i<m;++i) days+=daysIn(y,i);
    ms=uint64_t(days+d-1)*86400000ULL; return Status::Ok;
}
Status clockToHours(uint32_t start,uint32_t now,Real day,Real& hours) {
    if(start>=86400||now>=86400||!finite(day)||day<0) return Status::Invalid;
    uint32_t delta=(now+86400-start)%86400;
    hours=round((day*24+Real(delta)/3600)*10000)/10000; return Status::Ok;
}
Status scheduleTime(uint64_t pour,Real hours,uint64_t& out) {
    if(pour>CalendarLastMs||!finite(hours)||hours<0) return Status::Invalid;
    Real milliseconds=hours*Real(3600000);
    if(!finite(milliseconds)||milliseconds>Real(CalendarLastMs-pour)) return Status::Capacity;
    uint64_t delta=uint64_t(milliseconds);
    if(delta>CalendarLastMs-pour) return Status::Capacity;
    out=pour+delta; return Status::Ok;
}
Status calendarText(uint64_t at,char* date,size_t ds,char* clock,size_t cs) {
    if(at>CalendarLastMs) { CM_TEXT(date,ds,"--"); CM_TEXT(clock,cs,"--"); return Status::Invalid; }
    uint32_t days=uint32_t(at/86400000ULL), sec=uint32_t((at/1000)%86400);
    unsigned y=1970,m=1;
    while(y<2200 && days>=unsigned(leap(y)?366:365)) { days-=leap(y)?366:365; ++y; }
    while(m<12 && days>=daysIn(y,m)) { days-=daysIn(y,m); ++m; }
    Text(date,ds).number(y,4).character('-').number(m,2).character('-').number(days+1,2);
    formatHms(clock,cs,sec/3600,uint8_t(sec/60%60),uint8_t(sec%60));
    return Status::Ok;
}
}
