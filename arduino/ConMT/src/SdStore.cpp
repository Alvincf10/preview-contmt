#include <string.h>

#include "Board.h"
#include "Journal.h"
#include "SpiCard.h"

namespace conmt {
namespace board {
namespace {

constexpr uint16_t BlockBytes = 512;
constexpr uint32_t Uncached = UINT32_MAX;
constexpr uint32_t AnchorMagic = 0x314c4d43;  // CML1
// The journal owns the last 1 MiB of the card. It needs no filesystem and no
// CMTLOG.BIN: the two anchor blocks sit at the start of this region and the
// slots follow. Use a card dedicated to the device, because this region is
// written directly and is not part of any partition's free-space bookkeeping.
constexpr uint32_t JournalBlocks = 2048;

uint8_t buffer[BlockBytes];
uint32_t cached = Uncached;
uint32_t logStart = 0;
uint32_t capacitySlots = 0;
uint32_t occupied = 0;
uint32_t generation = 0;
bool dirty = false;

struct __attribute__((packed)) Anchor {
  uint32_t magic;
  uint32_t generation;
  uint32_t used;
  uint32_t crc;
};

bool flush() {
  if (!dirty) return true;
  if (!card::write(cached, buffer)) return false;
  dirty = false;
  return true;
}

bool load(uint32_t block) {
  if (block == cached) return true;
  if (!flush()) return false;
  cached = Uncached;
  if (!card::read(block, buffer)) return false;
  cached = block;
  return true;
}

bool anchorValid(const Anchor& anchor) {
  return anchor.magic == AnchorMagic && anchor.generation &&
         !(anchor.used & (BlockBytes - 1)) && anchor.used / SlotBytes <= capacitySlots &&
         anchor.crc == checksum(&anchor, offsetof(Anchor, crc));
}

}  // namespace

bool mount() {
  dirty = false;
  cached = Uncached;
  const uint32_t blocks = card::begin();
  if (!blocks || blocks <= JournalBlocks) return false;
  logStart = blocks - JournalBlocks;
  capacitySlots = ((JournalBlocks - 2) * BlockBytes) / SlotBytes;
  occupied = generation = 0;
  // A blank card, or one that still holds a previous CMTLOG file, is accepted:
  // the first commit writes fresh anchors and slots over this region.
  for (uint8_t i = 0; i < 2; ++i) {
    if (!load(logStart + i)) return false;
    Anchor candidate;
    memcpy(&candidate, buffer, sizeof(candidate));
    if (anchorValid(candidate) && candidate.generation > generation) {
      generation = candidate.generation;
      occupied = candidate.used / SlotBytes;
    }
  }
  return true;
}

uint32_t usedSlots() { return occupied; }
uint32_t slotCapacity() { return capacitySlots; }

bool rewindSlots(uint32_t slots) {
  if (slots > occupied || (slots & 3)) return false;
  dirty = false;
  cached = Uncached;
  occupied = slots;
  return true;
}

const uint8_t* readSlot(uint32_t slot) {
  if (slot >= occupied || !load(logStart + 2 + (slot >> 2))) return nullptr;
  return buffer + static_cast<uint16_t>(slot & 3) * SlotBytes;
}

uint8_t* appendSlot() {
  if (occupied >= capacitySlots) return nullptr;
  const uint16_t within = static_cast<uint16_t>(occupied & 3) * SlotBytes;
  const uint32_t block = logStart + 2 + (occupied >> 2);
  if (!within && block != cached) {
    if (!flush()) return nullptr;
    memset(buffer, 0, BlockBytes);
    cached = block;
  } else if (!load(block)) return nullptr;
  dirty = true;
  ++occupied;
  return buffer + within;
}

bool flushData() {
  if (!flush()) return false;
  cached = Uncached;
  return true;
}

bool sync() {
  if ((occupied & 3) || generation == UINT32_MAX || !flushData()) return false;
  Anchor anchor{AnchorMagic, generation + 1, occupied * SlotBytes, 0};
  anchor.crc = checksum(&anchor, offsetof(Anchor, crc));
  memset(buffer, 0, BlockBytes);
  memcpy(buffer, &anchor, sizeof(anchor));
  cached = Uncached;
  const uint32_t slot = logStart + (anchor.generation & 1);
  if (!card::write(slot, buffer) || !load(slot) || memcmp(&anchor, buffer, sizeof(anchor))) return false;
  generation = anchor.generation;
  return true;
}

}  // namespace board
}  // namespace conmt
