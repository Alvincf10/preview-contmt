#include <string.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define FLASH PROGMEM
#define compareName memcmp_P
#else
#define FLASH
#define compareName memcmp
#endif

#include "Board.h"
#include "Journal.h"
#include "SpiCard.h"

namespace conmt {
namespace board {
namespace {

constexpr uint16_t BlockBytes = 512;
constexpr uint32_t Uncached = UINT32_MAX;
constexpr uint32_t AnchorMagic = 0x314c4d43;  // CML1
const char LogName[] FLASH = "CMTLOG  BIN";

struct Volume {
  uint32_t fat;
  uint32_t fatSectors;
  uint32_t data;
  uint32_t root;
  uint32_t clusters;
  uint16_t rootSectors;  // Zero means the FAT32 root is a cluster chain.
  uint8_t clusterShift;
};

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

uint16_t u16(const uint8_t* p) {
  uint16_t value;
  memcpy(&value, p, sizeof(value));
  return value;
}

uint32_t u32(const uint8_t* p) {
  uint32_t value;
  memcpy(&value, p, sizeof(value));
  return value;
}

bool volumeAt(Volume& volume, uint32_t sector, uint32_t limit) {
  if (!load(sector) || u16(buffer + 510) != 0xaa55 || u16(buffer + 11) != BlockBytes) return false;
  uint32_t blocks = u16(buffer + 19);
  if (!blocks) blocks = u32(buffer + 32);
  const uint16_t reserved = u16(buffer + 14);
  const uint8_t count = buffer[16];
  const uint8_t clusterSize = buffer[13];
  if (blocks > limit || blocks <= reserved || !reserved || !count || count > 2 ||
      !clusterSize || (clusterSize & (clusterSize - 1))) return false;
  volume.clusterShift = 0;
  while ((1U << volume.clusterShift) != clusterSize) ++volume.clusterShift;
  volume.fatSectors = u16(buffer + 22);
  const bool fat16 = volume.fatSectors != 0;
  if (!fat16) volume.fatSectors = u32(buffer + 36);
  const uint16_t entries = u16(buffer + 17);
  volume.rootSectors = entries / 16 + (entries % 16 != 0);
  if (fat16 != (volume.rootSectors != 0) || !volume.fatSectors) return false;
  uint32_t available = blocks - reserved;
  for (uint8_t i = 0; i < count; ++i) {
    if (available < volume.fatSectors) return false;
    available -= volume.fatSectors;
  }
  if (available <= volume.rootSectors) return false;
  const uint32_t root = blocks - available;
  const uint32_t data = root + volume.rootSectors;
  volume.clusters = (blocks - data) >> volume.clusterShift;
  if (volume.clusters < 4085 || fat16 != (volume.clusters < 65525) ||
      volume.clusters >= (fat16 ? 0xfff5UL : 0x0ffffff5UL)) return false;
  const uint16_t flags = fat16 ? 0 : u16(buffer + 40);
  const uint8_t active = flags & 0x80 ? flags & 15 : 0;
  if (active >= count) return false;
  volume.root = fat16 ? sector + root : u32(buffer + 44);
  volume.data = sector + data;
  volume.fat = sector + reserved;
  if (active) volume.fat += volume.fatSectors;
  return true;
}

bool mountVolume(Volume& volume, uint32_t capacityBlocks) {
  if (volumeAt(volume, 0, capacityBlocks)) return true;
  if (cached || u16(buffer + 510) != 0xaa55) return false;
  for (uint16_t entry = 446; entry <= 494; entry += 16) {
    if (!load(0)) return false;
    const uint8_t type = buffer[entry + 4];
    const uint32_t first = u32(buffer + entry + 8);
    const uint32_t size = u32(buffer + entry + 12);
    if ((type == 4 || type == 6 || type == 0xb || type == 0xc || type == 0xe) &&
        first && first < capacityBlocks && size <= capacityBlocks - first &&
        volumeAt(volume, first, size)) return true;
  }
  return false;
}

uint32_t blockOf(const Volume& volume, uint32_t cluster) {
  return volume.data + ((cluster - 2) << volume.clusterShift);
}

bool validCluster(const Volume& volume, uint32_t cluster) {
  return cluster >= 2 && cluster - 2 < volume.clusters;
}

uint32_t nextCluster(const Volume& volume, uint32_t cluster) {
  const bool fat16 = volume.rootSectors != 0;
  const uint32_t offset = cluster << (fat16 ? 1 : 2);
  const uint32_t sector = offset >> 9;
  if (sector >= volume.fatSectors || !load(volume.fat + sector)) return 0;
  const uint8_t* entry = buffer + (offset & (BlockBytes - 1));
  return fat16 ? u16(entry) : u32(entry) & 0x0fffffffUL;
}

bool locateLog(const Volume& volume, uint32_t& first, uint32_t& bytes) {
  const bool fat16 = volume.rootSectors != 0;
  uint32_t cluster = volume.root;
  for (uint32_t visited = 0; visited < volume.clusters; ++visited) {
    if (!fat16 && !validCluster(volume, cluster)) return false;
    const uint32_t start = fat16 ? cluster : blockOf(volume, cluster);
    const uint16_t blocks = fat16 ? volume.rootSectors : 1U << volume.clusterShift;
    for (uint16_t i = 0; i < blocks; ++i) {
      if (!load(start + i)) return false;
      for (uint16_t at = 0; at < BlockBytes; at += 32) {
        const uint8_t* entry = buffer + at;
        if (!entry[0]) return false;
        if (!(entry[11] & 0x19) && !compareName(entry, LogName, 11)) {
          first = u16(entry + 26) | (fat16 ? 0UL : (static_cast<uint32_t>(u16(entry + 20)) << 16));
          bytes = u32(entry + 28);
          return true;
        }
      }
      poll();
    }
    if (fat16) return false;
    cluster = nextCluster(volume, cluster);
  }
  return false;
}

bool contiguous(const Volume& volume, uint32_t first, uint32_t blocks) {
  const uint32_t count = ((blocks - 1) >> volume.clusterShift) + 1;
  if (!validCluster(volume, first) || count > volume.clusters - (first - 2)) return false;
  const uint32_t last = first + count - 1;
  for (uint32_t cluster = first; cluster < last; ++cluster) {
    if (nextCluster(volume, cluster) != cluster + 1) return false;
    poll();
  }
  return nextCluster(volume, last) >= (volume.rootSectors ? 0xfff8UL : 0x0ffffff8UL);
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
  Volume volume;
  if (!blocks || !mountVolume(volume, blocks)) return false;
  uint32_t first, bytes;
  if (!locateLog(volume, first, bytes) || bytes < 4096 || (bytes & (BlockBytes - 1)) ||
      !contiguous(volume, first, bytes >> 9)) return false;
  logStart = blockOf(volume, first);
  if (logStart >= blocks || (bytes >> 9) > blocks - logStart) return false;
  capacitySlots = (bytes - 2 * BlockBytes) / SlotBytes;
  occupied = generation = 0;
  bool blank = true;
  for (uint8_t i = 0; i < 2; ++i) {
    if (!load(logStart + i)) return false;
    Anchor candidate;
    memcpy(&candidate, buffer, sizeof(candidate));
    if (anchorValid(candidate) && candidate.generation > generation) {
      generation = candidate.generation;
      occupied = candidate.used / SlotBytes;
    }
    if (candidate.magic || candidate.generation || candidate.used || candidate.crc) blank = false;
  }
  return generation || blank;
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
