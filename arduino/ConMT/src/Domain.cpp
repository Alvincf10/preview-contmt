#include "Domain.h"

#include <math.h>
#include <string.h>

namespace conmt {
namespace {

bool digit(char c) { return c >= '0' && c <= '9'; }

bool appendDigit(uint32_t& value, uint8_t next) {
  constexpr uint32_t limit = UINT32_MAX / 10;
  if (value > limit || (value == limit && next > UINT32_MAX % 10)) return false;
  value = value * 10 + next;
  return true;
}

// The supported calendar spans 1970–2199, with 2100 the only skipped leap year.
bool leap(uint16_t year) { return year % 4 == 0 && year != 2100; }

uint8_t monthDays(uint16_t year, uint8_t month) {
  if (month == 2) return leap(year) ? 29 : 28;
  return (month < 8 ? month & 1 : !(month & 1)) ? 31 : 30;
}

uint8_t pair(const char* text) {
  return digit(text[0]) && digit(text[1]) ? (text[0] - '0') * 10 + text[1] - '0' : UINT8_MAX;
}

constexpr uint32_t CalendarDays = 84006UL;  // 1970-01-01 through 2199-12-31.

}  // namespace

bool number(const char* text, uint8_t decimals, Scaled& output) {
  if (!text || !*text) return false;
  const bool negative = *text == '-';
  if (negative || *text == '+') ++text;
  bool found = false;
  uint32_t value = 0;
  while (digit(*text)) {
    found = true;
    if (!appendDigit(value, *text++ - '0')) return false;
  }
  if (*text == '.') {
    ++text;
    while (digit(*text)) {
      found = true;
      const uint8_t next = *text++ - '0';
      if (!decimals) {
        if (next) return false;
      } else {
        if (!appendDigit(value, next)) return false;
        --decimals;
      }
    }
  }
  if (!found || *text) return false;
  while (decimals--) if (!appendDigit(value, 0)) return false;
  if (value > INT32_MAX) return false;
  output = negative ? -static_cast<Scaled>(value) : static_cast<Scaled>(value);
  return true;
}

bool integer(const char* text, uint32_t& output) {
  if (!text || !*text) return false;
  uint32_t value = 0;
  for (; *text; ++text) if (!digit(*text) || !appendDigit(value, *text - '0')) return false;
  output = value;
  return true;
}

bool date(const char* text, uint32_t& output) {
  if (!text || strlen(text) != 10 || text[4] != '-' || text[7] != '-') return false;
  const uint8_t century = pair(text);
  const uint8_t withinCentury = pair(text + 2);
  if (withinCentury > 99) return false;
  const uint16_t year = century * 100U + withinCentury;
  const uint8_t month = pair(text + 5);
  const uint8_t day = pair(text + 8);
  if (year < 1970 || year > 2199 || !month || month > 12 || !day || day > monthDays(year, month))
    return false;
  output = day - 1;
  for (uint16_t y = 1970; y < year; ++y) output += leap(y) ? 366 : 365;
  for (uint8_t m = 1; m < month; ++m) output += monthDays(year, m);
  return true;
}

void calendar(uint32_t ordinal, uint16_t& year, uint8_t& month, uint8_t& day) {
  if (ordinal >= CalendarDays) { year = month = day = 0; return; }
  year = 1970;
  while (ordinal >= static_cast<uint16_t>(leap(year) ? 366 : 365)) {
    ordinal -= leap(year) ? 366 : 365;
    ++year;
  }
  month = 1;
  while (ordinal >= monthDays(year, month)) ordinal -= monthDays(year, month++);
  day = static_cast<uint8_t>(ordinal + 1);
}

bool clock(const char* text, uint32_t& output) {
  if (!text) return false;
  const size_t size = strlen(text);
  if ((size != 5 && size != 8) || text[2] != ':' || (size == 8 && text[5] != ':')) return false;
  const uint8_t hours = pair(text);
  const uint8_t minutes = pair(text + 3);
  const uint8_t seconds = size == 8 ? pair(text + 6) : 0;
  if (hours >= 24 || minutes >= 60 || seconds >= 60) return false;
  output = hours * 3600UL + minutes * 60U + seconds;
  return true;
}

bool validStamp(const Stamp& stamp) { return stamp.day < CalendarDays && stamp.second < DaySeconds; }

bool before(const Stamp& first, const Stamp& second) {
  return first.day < second.day || (first.day == second.day && first.second < second.second);
}

bool elapsed(const Stamp& start, const Stamp& end, uint32_t& seconds) {
  if (!validStamp(start) || !validStamp(end) || before(end, start)) return false;
  uint32_t days = end.day - start.day;
  uint32_t tail;
  if (end.second < start.second) {
    --days;
    tail = DaySeconds - start.second + end.second;
  } else tail = end.second - start.second;
  if (days > UINT32_MAX / DaySeconds) return false;
  const uint32_t whole = days * DaySeconds;
  if (UINT32_MAX - whole < tail) return false;
  seconds = whole + tail;
  return true;
}

Stamp forward(Stamp start, uint32_t seconds) {
  if (!validStamp(start)) return {NoDate, 0};
  start.day += seconds / DaySeconds;
  start.second += seconds % DaySeconds;
  if (start.second >= DaySeconds) { start.second -= DaySeconds; ++start.day; }
  return validStamp(start) ? start : Stamp{NoDate, 0};
}

bool labAge(Scaled day, bool early, uint32_t& seconds) {
  constexpr uint32_t maxDay = (UINT32_MAX / DaySeconds) * DayScale +
      ((UINT32_MAX % DaySeconds) * 5 + 2) / 432;
  if (day < 0 || static_cast<uint32_t>(day) > maxDay) return false;
  const uint32_t whole = day / DayScale;
  const uint32_t rest = (day % DayScale * 432 + 2) / 5;
  seconds = day == 0 && early ? 1800 : whole * DaySeconds + rest;
  return true;
}

Scaled average(const Sensors& sensors, bool operational) {
  // Hardware readings are bounded by their drivers. Use a floating sum so even
  // a host fixture spanning the full signed input range cannot overflow it.
  Real sum = 0;
  uint8_t count = 0;
  for (uint8_t i = 0; i < 3; ++i) if ((sensors.valid & (1 << i)) && sensors.channel[i] != Missing) {
    sum += sensors.channel[i];
    ++count;
  }
  if (!count) return Missing;
  const Real value = sum / count;
  if (operational) {
    constexpr Scaled step = Scale / 10;
    return static_cast<Scaled>(floor(value / step + 0.5)) * step;
  }
  return static_cast<Scaled>(value);
}

void Integral::add(uint32_t seconds, Scaled sample, int8_t datum, bool gap) {
  if (temperature != Missing && sample != Missing && !gap && seconds > age) {
    const Real mean = (static_cast<Real>(temperature) + sample) / (2 * static_cast<Real>(Scale));
    const Real delta = (mean - datum) * ((seconds - age) / static_cast<Real>(3600));
    const Real adjusted = delta - compensation;
    const Real next = maturity + adjusted;
    compensation = (next - maturity) - adjusted;
    maturity = next;
    if (maturity <= 0) maturity = compensation = 0;
  }
  age = seconds;
  temperature = sample;
}

void Regression::add(Real maturity, Scaled fc) {
  if (maturity <= 0 || fc <= 0 || count == UINT16_MAX) return;
  const Real x = log(maturity);
  const Real y = static_cast<Real>(fc) / Scale;
  const Real dx = x - meanX;
  const Real dy = y - meanY;
  ++count;
  meanX += dx / count;
  meanY += dy / count;
  xx += dx * (x - meanX);
  xy += dx * (y - meanY);
  yy += dy * (y - meanY);
}

bool Regression::finish(Fit& fit) const {
  if (count < 2 || !(xx > 0)) return false;
  const Real b = xy / xx;
  const Real a = meanY - b * meanX;
  Real r2 = yy > 0 ? (xy / xx) * (xy / yy) : 1;
  if (!isfinite(a) || !isfinite(b) || !isfinite(r2)) return false;
  if (r2 < 0) r2 = 0;
  if (r2 > 1) r2 = 1;
  fit = {static_cast<float>(a), static_cast<float>(b), static_cast<float>(r2), count};
  return isfinite(fit.a) && isfinite(fit.b);
}

Real correction(Real error) {
  if (error > 0) return 1 / (1 + error);
  if (error > -0.1) return 1;
  return 0.9 - error;
}

Real estimate(Real m, const Fit& fit, Real factor) {
  if (m <= 0 || !fit.count) return 0;
  const Real fc = (fit.a + fit.b * log(m)) * factor;
  return isfinite(fc) && fc > 0 ? fc : 0;
}

}  // namespace conmt
