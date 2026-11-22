#include <Arduino.h>
#include <OneWire.h>
#include <avr/interrupt.h>

#include "Board.h"
#include "BoardProfile.h"

#if !defined(__AVR_ATmega328P__) || F_CPU != 16000000UL
#error Select the 16 MHz ATmega328P profile for ConMT revision 1.0
#endif

namespace {
constexpr uint8_t RxMask = 63;
volatile uint8_t uartInput[RxMask + 1];
volatile uint8_t uartHead = 0;
volatile uint8_t uartTail = 0;
volatile bool uartLost = false;
}

ISR(USART_RX_vect) {
  const uint8_t status = UCSR0A;
  const uint8_t byte = UDR0;
  const uint8_t next = (uartHead + 1) & RxMask;
  if ((status & (_BV(FE0) | _BV(DOR0) | _BV(UPE0))) || next == uartTail) {
    uartLost = true;
  } else if (!uartLost) {
    uartInput[uartHead] = byte;
    uartHead = next;
  }
}

namespace conmt {
namespace board {
namespace {

OneWire bus(pins::Temperature);
uint8_t addresses[3][8]{};
Sensors readings{};
uint32_t sensorTime = 0;
uint32_t searchTime = 0;
uint32_t clockTick = 0;
uint32_t buzzerTick = 0;
uint8_t converting = 0;
uint8_t previous85 = 0;
Stamp current{NoDate, 0};

void discover() {
  uint8_t rom[8];
  bus.reset_search();
  while (bus.search(rom)) {
    if (rom[0] != 0x28 || OneWire::crc8(rom, 7) != rom[7]) continue;
    uint8_t freeSlot = 3;
    bool known = false;
    for (uint8_t i = 0; i < 3; ++i) {
      if (!addresses[i][0] && freeSlot == 3) freeSlot = i;
      if (!memcmp(addresses[i], rom, sizeof(rom))) known = true;
    }
    if (!known && freeSlot < 3) memcpy(addresses[freeSlot], rom, sizeof(rom));
    if (freeSlot == 3) break;
  }
}

void convert() {
  converting = 0;
  for (uint8_t i = 0, bit = 1; i < 3; ++i, bit <<= 1) {
    if (!addresses[i][0] || !bus.reset()) continue;
    bus.select(addresses[i]);
    bus.write(0x44);
    // Externally powered DS18B20s drive the bus low while converting.
    if (!bus.read_bit()) converting |= bit;
  }
  readings.valid &= converting;
  sensorTime = millis();
}

void readSensors() {
  readings.valid = 0;
  uint8_t current85 = 0;
  for (uint8_t i = 0, bit = 1; i < 3; ++i, bit <<= 1) {
    if (!(converting & bit) || !bus.reset()) continue;
    bus.select(addresses[i]);
    bus.write(0xbe);
    uint8_t scratch[9];
    for (uint8_t& byte : scratch) byte = bus.read();
    if ((scratch[4] & 31) != 31 || OneWire::crc8(scratch, 8) != scratch[8]) continue;
    const int16_t raw = (static_cast<uint16_t>(scratch[1]) << 8) | scratch[0];
    if (raw < -880 || raw > 2000) continue;
    // The reset scratchpad can have a valid CRC and report 85 °C.
    if (raw == 0x0550) {
      current85 |= bit;
      if (!(previous85 & bit)) continue;
    }
    readings.channel[i] = static_cast<Scaled>(raw) * (Scale / 16);
    readings.valid |= bit;
  }
  previous85 = current85;
}

}  // namespace

void begin() {
  constexpr uint16_t divisor = (F_CPU + 4UL * CONMT_PANEL_BAUD) / (8UL * CONMT_PANEL_BAUD) - 1;
  UBRR0H = divisor >> 8;
  UBRR0L = divisor & 0xff;
  UCSR0A = _BV(U2X0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
  UCSR0B = _BV(RXEN0) | _BV(TXEN0) | _BV(RXCIE0);
  static_assert(pins::Buzzer == 3, "The buzzer requires PD3");
  PORTD &= ~_BV(PD3);
  DDRD |= _BV(PD3);
  clockTick = millis();
  discover();
  searchTime = clockTick;
  convert();
}

void poll() {
  const uint32_t tick = millis();
  const uint32_t seconds = (tick - clockTick) / 1000UL;
  if (seconds) {
    clockTick += seconds * 1000UL;
    if (current.day != NoDate) current = forward(current, seconds);
  }
  if ((PORTD & _BV(PD3)) && tick - buzzerTick >= 60) PORTD &= ~_BV(PD3);
  if (tick - sensorTime < 800) return;
  readSensors();
  if (tick - searchTime >= 30000UL && (!addresses[0][0] || !addresses[1][0] || !addresses[2][0])) {
    discover();
    searchTime = tick;
  }
  convert();
}

uint32_t ticks() { return millis(); }
const Stamp& now() { return current; }

bool setClock(const Stamp& stamp) {
  if (!validStamp(stamp)) return false;
  current = stamp;
  clockTick = millis();
  return true;
}

const Sensors& temperatures() { return readings; }

uint16_t supplyMv() {
  // Vin uses a 3:1 resistor divider. Both ADC inputs are measured against AVCC.
  const uint32_t reading = analogRead(pins::VinSense);
#ifdef CONMT_VIN_REF_MV
  return static_cast<uint16_t>((reading * (3UL * CONMT_VIN_REF_MV) + 511) / 1023);
#else
  ADMUX = _BV(REFS0) | 0x0e;  // Select the internal bandgap as the ADC input.
  delay(2);
  ADCSRA |= _BV(ADSC);
  while (ADCSRA & _BV(ADSC)) {}
  const uint16_t bandgap = ADC;
  return bandgap >= 128 ? (reading * (3UL * CONMT_BANDGAP_MV) + bandgap / 2) / bandgap : 0;
#endif
}

int16_t batteryPercent(uint16_t voltage) {
#if CONMT_BATTERY_FULL_MV > CONMT_BATTERY_EMPTY_MV && CONMT_BATTERY_EMPTY_MV > 0
  if (voltage <= CONMT_BATTERY_EMPTY_MV) return 0;
  if (voltage >= CONMT_BATTERY_FULL_MV) return 100;
  return (100UL * (voltage - CONMT_BATTERY_EMPTY_MV)) /
         (CONMT_BATTERY_FULL_MV - CONMT_BATTERY_EMPTY_MV);
#else
  (void)voltage;
  return -1;
#endif
}

void beep(bool enabled) {
  if (enabled) {
    PORTD |= _BV(PD3);
    buzzerTick = millis();
  }
}

int receive() {
  if (uartLost) {
    const uint8_t saved = SREG;
    cli();
    uartTail = uartHead;
    uartLost = false;
    SREG = saved;
    return -2;
  }
  const uint8_t tail = uartTail;
  if (tail == uartHead) return -1;
  const uint8_t value = uartInput[tail];
  uartTail = (tail + 1) & RxMask;
  return value;
}

void transmit(uint8_t byte) {
  while (!(UCSR0A & _BV(UDRE0))) poll();
  UDR0 = byte;
}

}  // namespace board
}  // namespace conmt
