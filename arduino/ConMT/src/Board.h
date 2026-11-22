#pragma once

#include "Domain.h"

namespace conmt {
namespace board {

void begin();
void poll();
uint32_t ticks();
const Stamp& now();
bool setClock(const Stamp& stamp);
const Sensors& temperatures();
uint16_t supplyMv();
int16_t batteryPercent(uint16_t voltage);
void beep(bool enabled);

int receive();
void transmit(uint8_t value);

bool mount();
constexpr uint8_t SlotBytes = 128;
uint32_t usedSlots();
uint32_t slotCapacity();
const uint8_t* readSlot(uint32_t slot);
uint8_t* appendSlot();
bool rewindSlots(uint32_t slots);
bool flushData();
bool sync();

}  // namespace board
}  // namespace conmt
