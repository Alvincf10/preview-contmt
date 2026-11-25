#include <Arduino.h>

#include "Board.h"
#include "BoardProfile.h"
#include "SpiCard.h"

namespace conmt {
namespace card {
namespace {
constexpr uint8_t Dummy = 0xff;
constexpr uint8_t DataToken = 0xfe;
constexpr uint16_t TimeoutMs = 500;
bool blockAddress = false;

uint8_t transfer(uint8_t data = Dummy) {
  SPDR = data;
  while (!(SPSR & _BV(SPIF))) {}
  return SPDR;
}

void release() {
  PORTB |= _BV(PB2);
  transfer();
}

uint8_t waitByte(bool idle, uint16_t timeout = TimeoutMs) {
  const uint32_t start = millis();
  do {
    const uint8_t data = transfer();
    if ((data == Dummy) == idle) return data;
    board::poll();
  } while (millis() - start < timeout);
  return idle ? 0 : Dummy;
}

uint8_t crc7(uint8_t crc, uint8_t data) {
  crc ^= data;
  for (uint8_t i = 0; i < 8; ++i) crc = (crc << 1) ^ ((crc & 0x80) ? 0x12 : 0);
  return crc;
}

uint16_t crc16(uint16_t crc, uint8_t data) {
  crc ^= static_cast<uint16_t>(data) << 8;
  for (uint8_t i = 0; i < 8; ++i) crc = (crc << 1) ^ ((crc & 0x8000) ? 0x1021 : 0);
  return crc;
}

uint8_t command(uint8_t cmd, uint32_t arg = 0) {
  release();
  PORTB &= ~_BV(PB2);
  if (waitByte(true) != Dummy) return Dummy;
  const uint8_t packet[] = { static_cast<uint8_t>(0x40 | cmd), static_cast<uint8_t>(arg >> 24),
      static_cast<uint8_t>(arg >> 16), static_cast<uint8_t>(arg >> 8), static_cast<uint8_t>(arg) };
  uint8_t crc = 0;
  for (const uint8_t byte : packet) { transfer(byte); crc = crc7(crc, byte); }
  transfer(crc | 1);
  for (uint8_t i = 0; i < 10; ++i) {
    const uint8_t response = transfer();
    if (!(response & 0x80)) return response;
  }
  return Dummy;
}

bool receiveData(uint8_t* data, uint16_t length) {
  if (waitByte(false) != DataToken) return false;
  uint16_t crc = 0;
  for (uint16_t i = 0; i < length; ++i) {
    data[i] = transfer();
    crc = crc16(crc, data[i]);
  }
  const uint8_t high = transfer();
  const uint8_t low = transfer();
  return crc == (static_cast<uint16_t>(high) << 8 | low);
}

uint32_t address(uint32_t sector) { return blockAddress ? sector : sector << 9; }

uint32_t sectors() {
  uint8_t csd[16];
  if (command(9) || !receiveData(csd, sizeof(csd))) return 0;
  if ((csd[0] >> 6) == 1) {
    const uint32_t size = static_cast<uint32_t>(csd[7] & 63) << 16 |
                          static_cast<uint16_t>(csd[8]) << 8 | csd[9];
    return size == 0x3fffffUL ? UINT32_MAX : (size + 1) << 10;
  }
  if (csd[0] >> 6) return 0;
  const uint16_t size = static_cast<uint16_t>(csd[6] & 3) << 10 |
                        static_cast<uint16_t>(csd[7]) << 2 | csd[8] >> 6;
  const uint8_t scale = ((csd[9] & 3) << 1) | (csd[10] >> 7);
  const uint8_t length = csd[5] & 15;
  if (length < 9 || length > 11) return 0;
  return static_cast<uint32_t>(size + 1) << (scale + length - 7);
}

uint32_t initialize() {
  uint32_t start = millis();
  while (command(0) != 1) if (millis() - start >= 1000) return 0;

  const uint8_t state = command(8, 0x1aa);
  const bool version2 = state == 1;
  if (version2) {
    transfer(); transfer();
    const uint8_t voltage = transfer();
    const uint8_t pattern = transfer();
    if (voltage != 1 || pattern != 0xaa) return 0;
  } else if (state != 5) return 0;

  start = millis();
  for (;;) {
    if (command(55) > 1) return 0;
    const uint8_t status = command(41, version2 ? 0x40000000UL : 0);
    if (!status) break;
    if (status != 1 || millis() - start >= 1500) return 0;
  }
  if (command(58)) return 0;
  const uint8_t flags = transfer();
  const uint8_t voltage = transfer();
  transfer(); transfer();
  if (!(flags & 0x80) || !(voltage & 0x30)) return 0;
  blockAddress = version2 && (flags & 0x40);
  if ((!blockAddress && command(16, 512)) || command(59, 1)) return 0;
  return sectors();
}

}  // namespace

uint32_t begin() {
  static_assert(pins::SdSelect == 10, "SPI uses PB2 for SD chip select");
  PORTB |= _BV(PB2);
  DDRB |= _BV(PB2) | _BV(PB3) | _BV(PB5);
  DDRB &= ~_BV(PB4);
  SPCR = _BV(SPE) | _BV(MSTR) | _BV(SPR1) | _BV(SPR0);
  SPSR = 0;
  for (uint8_t i = 0; i < 10; ++i) transfer();
  const uint32_t blocks = initialize();
  release();
  SPCR = _BV(SPE) | _BV(MSTR);  // 4 MHz transfer after identification.
  return blocks;
}

bool read(uint32_t sector, uint8_t* data) {
  const bool success = !command(17, address(sector)) && receiveData(data, 512);
  release();
  return success;
}

bool write(uint32_t sector, const uint8_t* data) {
  bool success = false;
  if (!command(24, address(sector))) {
    transfer(); transfer(DataToken);
    uint16_t crc = 0;
    for (uint16_t i = 0; i < 512; ++i) {
      transfer(data[i]);
      crc = crc16(crc, data[i]);
    }
    transfer(crc >> 8); transfer(crc);
    if ((waitByte(false) & 0x1f) == 5 && waitByte(true) == Dummy) {
      const uint8_t first = command(13);
      const uint8_t second = transfer();
      success = !first && !second;
    }
  }
  release();
  return success;
}

}  // namespace card
}  // namespace conmt
