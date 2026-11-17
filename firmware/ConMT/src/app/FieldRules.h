#pragma once
#include "../storage/Journal.h"
namespace conmt {
enum class InputFormat : uint8_t { Text, Date, NonNegative, Positive, Datum, PourDate, PourClock };
struct FieldRule { Kind kind; Field field; InputFormat format; uint8_t capacity; };
bool fieldRule(const char* token,FieldRule& out);
}
