#include "Flash.h"
#include "Types.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <float.h>

namespace conmt {
static const char* statusText(Status status) {
    static const char names[] CM_ROM=
        "Ok\0Missing\0Invalid\0Stale\0Busy\0Absent\0Full\0IoError\0Corrupt\0Version\0"
        "NoModel\0NoSensor\0NoClock\0Conflict\0Gap\0NeedDay\0Capacity\0ConfirmRequired\0Unsupported";
    uint8_t index=uint8_t(status); if(index>uint8_t(Status::Unsupported)) index=uint8_t(Status::Invalid);
    const char* name=names;
    while(index--) { while(flashValue(name++)) {} }
    return name;
}
void formatStatus(char* out,size_t capacity,Status status) {
    copyFlash(out,capacity,statusText(status));
}
const char* statusName(Status status) {
#ifdef __AVR__
    static char name[18]; formatStatus(name,sizeof(name),status); return name;
#else
    return statusText(status);
#endif
}
Status average(const SensorFrame& f, uint32_t now, uint32_t maxAge, Average& out) {
    out = {0,0,0};
    if (uint32_t(now-f.sampledMonoMs) > maxAge) return Status::Stale;
    uint8_t n=0;
    for (uint8_t i=0;i<3;++i) if ((f.validMask & (1u<<i)) && finite(f.channel[i])) {
        out.raw += f.channel[i]; out.mask |= 1u<<i; ++n;
    }
    if (!n) return Status::NoSensor;
    out.raw /= n;
    if(!finite(out.raw)) { out={0,0,0}; return Status::Invalid; }
    out.operational = (out.raw < 0 ? -floor(-out.raw*10+Real(.5)) : floor(out.raw*10+Real(.5)))/10;
    if(!finite(out.operational)) { out={0,0,0}; return Status::Invalid; }
    return Status::Ok;
}
Status parseReal(const char* s, Real& out) {
    if (!s || !*s) return Status::Missing;
    const char* p=s;
    if (*p=='-' || *p=='+') ++p;
    unsigned digits=0;
    while (*p>='0' && *p<='9') { ++p; ++digits; }
    if (*p=='.') { ++p; while (*p>='0' && *p<='9') { ++p; ++digits; } }
    if (!digits) return Status::Invalid;
    if (*p=='e' || *p=='E') {
        ++p; if (*p=='-' || *p=='+') ++p;
        if (*p<'0' || *p>'9') return Status::Invalid;
        while (*p>='0' && *p<='9') ++p;
    }
    if (*p) return Status::Invalid;
    char* end=nullptr;
    Real value=Real(strtod(s,&end));
    if (!end || *end || !finite(value)) return Status::Invalid;
    out=value; return Status::Ok;
}
Status parseU32(const char* s, uint32_t& out) {
    if (!s || !*s) return Status::Missing;
    uint32_t n=0;
    for (;*s;++s) {
        if (*s<'0' || *s>'9' || n>(UINT32_MAX-uint32_t(*s-'0'))/10) return Status::Invalid;
        n=n*10+uint32_t(*s-'0');
    }
    out=n; return Status::Ok;
}
bool safeText(const char* s,size_t cap) {
    if (!s) return false;
    size_t n=0;
    for (;s[n];++n) if (n+1>=cap || s[n]<32 || s[n]>126 || s[n]=='|' || s[n]=='"' || s[n]=='\\') return false;
    return n<cap;
}
static Real fixedTie(Real v,uint8_t digits) {
    if(v==0) return 0;
    int exponent; Real f=frexp(fabs(v),&exponent);
    const uint8_t bits=sizeof(Real)==4?24:53;
    uint64_t mantissa=uint64_t(ldexp(f,bits));
    int shift=exponent-bits+digits;
    while(mantissa && !(mantissa&1)) { mantissa>>=1; ++shift; }
    if(shift==-1) {
        Real scale=1; for(uint8_t i=0;i<digits;++i) scale*=10;
        return copysign(floor(fabs(v)*scale+Real(.5))/scale,v);
    }
    return v;
}
void formatReal(char* out,size_t n,Real v,uint8_t digits) {
    if (!finite(v) || digits>6 || fabs(v)>Real(1e12)) { CM_TEXT(out,n,"--"); return; }
    v=fixedTie(v,digits);
#ifdef __AVR__
    char b[28]; dtostrf(v,0,digits,b); CM_FMT(out,n,"%s",b);
#else
    CM_FMT(out,n,"%.*f",int(digits),double(v==0?0:v));
#endif
}
void formatCoeff(char* out,size_t size,Real value,uint8_t digits) {
    formatReal(out,size,value,digits);
    Real rounded;
    if(parseReal(out,rounded)==Status::Ok&&rounded==0) formatReal(out,size,0,digits);
}
uint32_t crc32(uint32_t crc,const uint8_t* p,size_t n) {
    while (n--) { crc ^= *p++; for (uint8_t b=0;b<8;++b) crc=(crc>>1)^(0xedb88320UL & (0u-(crc&1))); }
    return crc;
}
}
