#pragma once
#include <stdint.h>
#include <stddef.h>
#include <math.h>

namespace conmt {
#ifdef CONMT_REAL32
using Real = float;
#else
using Real = double;
#endif
enum class Status : uint8_t {
    Ok, Missing, Invalid, Stale, Busy, Absent, Full, IoError, Corrupt,
    Version, NoModel, NoSensor, NoClock, Conflict, Gap, NeedDay, Capacity,
    ConfirmRequired, Unsupported
};
const char* statusName(Status s);
void formatStatus(char* out,size_t capacity,Status status);
inline bool finite(Real x) { return isfinite(x); }
inline Real positive(Real x) { return x > 0 ? x : 0; }
struct Row {
    uint32_t id, revision;
    Real day, timeH, temp, fc;
    bool hasTemp, hasFc;
    Row() : id(0),revision(0),day(0),timeH(0),temp(0),fc(0),hasTemp(false),hasFc(false) {}
};
struct Fit {
    Real a, b, r2;
    uint32_t n;
    bool valid;
    Fit() : a(0),b(0),r2(0),n(0),valid(false) {}
};
struct Selection {
    Real day, factor;
    bool found;
    Selection() : day(0),factor(1),found(false) {}
};
struct Prediction {
    Real maturity, raw, factor, fc, referenceDay;
    bool hasReference;
    Prediction() : maturity(0),raw(0),factor(1),fc(0),referenceDay(0),hasReference(false) {}
};
enum class PointSource : uint8_t { Sensor, Manual, Import };
struct Point {
    uint32_t id, revision;
    uint64_t atMs;
    Real day, temp;
    uint8_t validMask;
    PointSource source;
    Point() : id(0),revision(0),atMs(0),day(0),temp(0),validMask(0),source(PointSource::Sensor) {}
};
struct SensorFrame {
    Real channel[3];
    uint32_t sampledMonoMs;
    uint8_t validMask;
    SensorFrame() : channel{0,0,0},sampledMonoMs(0),validMask(0) {}
};
struct Average { Real raw, operational; uint8_t mask; };
struct Time {
    uint32_t monoMs;
    uint64_t wallMs;
    bool valid;
};
class RowSource {
protected:
    ~RowSource() {}
public:
    virtual void reset() = 0;
    virtual Status next(Row& row) = 0;
};
class ClockPort {
protected:
    ~ClockPort() {}
public:
    virtual Time now() = 0;
};
class SensorPort {
protected:
    ~SensorPort() {}
public:
    virtual void poll(uint32_t now) = 0;
    virtual Status latest(SensorFrame& frame) = 0;
};
class DevicePort {
protected:
    ~DevicePort() {}
public:
    virtual void poll(uint32_t) {}
    virtual Status battery(uint8_t& percent) = 0;
    virtual Status brightness(uint8_t value) = 0;
    virtual Status sound(bool enabled) = 0;
};
Status average(const SensorFrame& f, uint32_t now, uint32_t maxAge, Average& out);
Status parseReal(const char* text, Real& out);
Status parseU32(const char* text, uint32_t& out);
bool safeText(const char* text, size_t capacity);
void formatReal(char* out, size_t size, Real value, uint8_t digits);
void formatCoeff(char* out,size_t size,Real value,uint8_t digits=4);
uint32_t crc32(uint32_t crc, const uint8_t* data, size_t size);
}
