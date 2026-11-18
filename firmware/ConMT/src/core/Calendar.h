#pragma once
#include "Types.h"
namespace conmt {
Status parseClock(const char* text, uint32_t& seconds);
Status parseDate(const char* text, uint64_t& midnightMs);
Status clockToHours(uint32_t pourSeconds,uint32_t clockSeconds,Real day,Real& hours);
static const uint64_t CalendarLastMs=7258118399999ULL;
Status scheduleTime(uint64_t pourMs,Real timeH,uint64_t& out);
// Pass a zero size to omit either output.
Status calendarText(uint64_t atMs,char* date,size_t dateSize,char* clock,size_t clockSize);
}
