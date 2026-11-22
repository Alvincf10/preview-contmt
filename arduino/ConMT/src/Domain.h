#pragma once

#include <stdint.h>
#include <stddef.h>
#include <float.h>

namespace conmt {

using Ref = uint32_t;
using Scaled = int32_t;
using Real = float;

constexpr Scaled Missing = INT32_MIN;
constexpr Scaled Scale = 100000;
constexpr Scaled DayScale = 1000;
constexpr uint32_t DaySeconds = 86400UL;
constexpr uint32_t NoDate = UINT32_MAX;
constexpr uint8_t ViewRows = 6;

// The disk format uses explicitly packed, fixed-width little-endian fields.
// No pointer, native bool, enum of unspecified width, or native double is stored.
#if !defined(__BYTE_ORDER__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error ConMT record format requires a little-endian target
#endif
static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,
              "ConMT records use IEEE-754 binary32");

struct __attribute__((packed)) Stamp {
  uint32_t day;
  uint32_t second;
};

struct __attribute__((packed)) Span {
  Ref first;
  Ref last;
  uint16_t count;
};

struct __attribute__((packed)) Identity {
  Ref operatorName;
  Ref project;
  uint32_t date;
};

struct __attribute__((packed)) Settings {
  uint32_t interval;
  uint8_t brightness;
  uint8_t flags;
};

constexpr uint8_t Sound = 1;
constexpr uint8_t AutoSave = 2;
const Settings DefaultSettings = {300, 80, Sound | AutoSave};

enum MixField : uint8_t { Cement, Water, Coarse, Fine, Retarder, Accelerator, FlyAsh, MixCount };
struct __attribute__((packed)) Mix {
  Scaled quantities[MixCount];
  Ref brands[3];
};

struct __attribute__((packed)) Baseline {
  Ref name;
  Ref identity;
  Ref mix;
  Ref model;
  Span rows;
  Stamp pour;
  Scaled target;
  int8_t datum;
  uint8_t datumSet;
};

struct __attribute__((packed)) LabRow {
  Ref id;
  Scaled day;
  uint32_t age;
  Scaled temperature;
  Scaled fc;
};

struct __attribute__((packed)) Fit {
  float a;
  float b;
  float r2;
  uint16_t count;
};

struct __attribute__((packed)) Model {
  Fit fit;
  Span factors;
  float maxM;
};

struct __attribute__((packed)) Factor {
  Scaled day;
  float value;
};

struct __attribute__((packed)) Sensors {
  Scaled channel[3];
  uint8_t valid;
};

enum PointFlags : uint8_t { Manual = 1, Gap = 2, Automatic = 4 };
struct __attribute__((packed)) Point {
  Stamp at;
  Scaled day;
  Sensors sensors;
  Scaled temperature;
  float maturity;
  float compensation;
  uint8_t flags;
};

struct __attribute__((packed)) Session {
  Ref baseline;
  Ref identity;
  Span points;
  uint8_t partial;
};

struct __attribute__((packed)) Result {
  Ref previous;
  Ref session;
  Stamp savedAt;
  float fc;
  uint8_t partial;
};

enum class SaveKind : uint8_t { None, Baseline, Result };
struct __attribute__((packed)) Root {
  Ref identity;
  Ref settings;
  Ref draft;
  Ref active;
  Ref history;
  Span baselines;
  Ref transactionStart;
  Ref savedInput;
  Ref savedOutput;
  SaveKind saveKind;
  uint8_t identityReady;
  uint8_t draftFromSaved;
};

enum class Error : uint8_t {
  Ok, Input, MissingData, State, Stale, Full, Storage, Corrupt, Version,
  Sensor, Clock, NoFit, NoInterval, Confirm, Busy, NotFound
};

class Answer {
 public:
  static constexpr uint32_t MaxValue = 0x0fffffffUL;
  constexpr Answer(Error error, Ref value) : word_(static_cast<uint32_t>(error) << 28 | value) {}
  Error error() const { return static_cast<Error>(word_ >> 28); }
  Ref value() const { return word_ & MaxValue; }

 private:
  uint32_t word_;
};
static_assert(static_cast<uint8_t>(Error::NotFound) <= 15, "Fit the error in the response word");

bool number(const char* text, uint8_t decimals, Scaled& output);
bool integer(const char* text, uint32_t& output);
bool date(const char* text, uint32_t& output);
bool clock(const char* text, uint32_t& output);
void calendar(uint32_t day, uint16_t& year, uint8_t& month, uint8_t& date);
bool validStamp(const Stamp& stamp);
bool elapsed(const Stamp& start, const Stamp& end, uint32_t& seconds);
bool before(const Stamp& first, const Stamp& second);
Stamp forward(Stamp start, uint32_t seconds);
bool labAge(Scaled day, bool early, uint32_t& seconds);

Scaled average(const Sensors& sensors, bool operational);
Real correction(Real error);
Real estimate(Real maturity, const Fit& fit, Real factor = 1);

struct Integral {
  uint32_t age = 0;
  Scaled temperature = Missing;
  Real maturity = 0;
  Real compensation = 0;

  void add(uint32_t seconds, Scaled sample, int8_t datum, bool gap = false);
};

struct Regression {
  Real meanX = 0;
  Real meanY = 0;
  Real xx = 0;
  Real xy = 0;
  Real yy = 0;
  uint16_t count = 0;

  void add(Real maturity, Scaled fc);
  bool finish(Fit& fit) const;
};

}  // namespace conmt
