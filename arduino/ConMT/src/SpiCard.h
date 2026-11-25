#pragma once

#include <stdint.h>

namespace conmt {
namespace card {
// Returns sector count, or zero on initialization failure.
uint32_t begin();
bool read(uint32_t sector, uint8_t* data);
bool write(uint32_t sector, const uint8_t* data);
}  // namespace card
}  // namespace conmt
