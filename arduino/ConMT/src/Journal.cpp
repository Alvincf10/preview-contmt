#include "Journal.h"
#include "Board.h"

#include <string.h>

namespace conmt {
namespace {
constexpr uint16_t Magic = 0x4d43;
constexpr uint8_t Version = 1;
enum Offset : uint8_t { MagicAt = 0, VersionAt = 2, KindAt = 3, OwnerAt = 4,
                        LengthAt = 8, PayloadAt = 9, CrcAt = PayloadAt + Journal::PayloadBytes };

template<class T> T readValue(const uint8_t* bytes) {
  T value;
  memcpy(&value, bytes, sizeof(value));
  return value;
}

template<class T> void writeValue(uint8_t* bytes, T value) {
  memcpy(bytes, &value, sizeof(value));
}
}  // namespace

uint32_t checksum(const void* data, uint8_t length) {
  const uint8_t* bytes = static_cast<const uint8_t*>(data);
  uint32_t crc = UINT32_MAX;
  while (length--) {
    crc ^= *bytes++;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      const bool set = crc & 1;
      crc >>= 1;
      if (set) crc ^= 0xedb88320UL;
    }
  }
  return ~crc;
}

bool Journal::fail(Error error) {
  error_ = error;
  if (error == Error::Storage || error == Error::Corrupt || error == Error::Version) open_ = false;
  return false;
}

const uint8_t* Journal::load(Ref id) {
  const uint8_t* frame = nullptr;
  if (!id || id > written_) fail(Error::Corrupt);
  else if (!(frame = board::readSlot(id - 1))) fail(Error::Storage);
  else if (readValue<uint16_t>(frame + MagicAt) != Magic || frame[LengthAt] > PayloadBytes ||
           readValue<uint32_t>(frame + CrcAt) != checksum(frame, CrcAt)) fail(Error::Corrupt);
  else if (frame[VersionAt] != Version) fail(Error::Version);
  else return frame;
  return nullptr;
}

bool Journal::validate(Ref first, Ref last) {
  if (!first || first > last) return fail(Error::Corrupt);
  for (Ref id = first; id <= last; ++id) {
    const uint8_t* frame = load(id);
    if (!frame) return false;
    if ((frame[KindAt] == static_cast<uint8_t>(Kind::Commit)) != (id == last)) return fail(Error::Corrupt);
    board::poll();
  }
  return true;
}

bool Journal::mount() {
  static_assert(CrcAt + 4 == 77, "Journal format changed");
  static_assert(sizeof(Root) == 45, "Commit format changed");
  writing_ = false;
  committed_ = 0;
  root_ = {};
  if (!board::mount()) return fail(Error::Storage);
  written_ = board::usedSlots();
  open_ = true;
  error_ = Error::Ok;
  if (!written_) return begin() && commit();

  for (Ref id = written_; id; --id) {
    const uint8_t* frame = load(id);
    if (frame && frame[KindAt] == static_cast<uint8_t>(Kind::Commit) && frame[LengthAt] == sizeof(Root)) {
      memcpy(&root_, frame + PayloadAt, sizeof(Root));
      if (validate(root_.transactionStart, id)) {
        committed_ = written_ = id;
        error_ = Error::Ok;
        open_ = true;
        return true;
      }
    }
    if (error_ == Error::Version || error_ == Error::Storage) return false;
    board::poll();
  }
  return fail(Error::Corrupt);
}

bool Journal::begin() {
  if (!open_) return false;
  if (writing_) return fail(Error::Busy);
  if (board::usedSlots() != committed_ && !board::rewindSlots(committed_)) return fail(Error::Storage);
  pending_ = root_;
  written_ = committed_;
  writing_ = true;
  error_ = Error::Ok;
  return true;
}

void Journal::abandon() {
  writing_ = false;
  written_ = committed_;
  if (open_) error_ = Error::Ok;
}

Ref Journal::append(Kind kind, Ref owner, const void* data, uint8_t length) {
  if (!writing_ || error_ != Error::Ok) return 0;
  if (written_ >= board::slotCapacity() || length > PayloadBytes) { fail(Error::Full); return 0; }
  uint8_t* frame = board::appendSlot();
  if (!frame) { fail(Error::Storage); return 0; }
  writeValue(frame + MagicAt, Magic);
  frame[VersionAt] = Version;
  frame[KindAt] = static_cast<uint8_t>(kind);
  writeValue(frame + OwnerAt, owner);
  frame[LengthAt] = length;
  if (length) memcpy(frame + PayloadAt, data, length);
  memset(frame + PayloadAt + length, 0, PayloadBytes - length);
  writeValue(frame + CrcAt, checksum(frame, CrcAt));
  board::poll();
  return ++written_;
}

bool Journal::commit(SaveKind kind, Ref input, Ref output) {
  Root& next = pending_;
  next.transactionStart = committed_ + 1;
  next.saveKind = kind;
  next.savedInput = input;
  next.savedOutput = output;
  // The next transaction starts in a different sector from this commit.
  while ((written_ & 3) != 3 && append(Kind::Pad, 0, nullptr, 0)) {}
  const Ref last = add(Kind::Commit, next);
  if (!last || !board::flushData() || !validate(next.transactionStart, last) || !board::sync()) {
    if (error_ == Error::Ok) fail(Error::Storage);
    writing_ = false;
    return false;
  }
  root_ = next;
  committed_ = last;
  writing_ = false;
  return true;
}

Answer Journal::findSave(SaveKind kind, Ref input) {
  if (!open_) return {error_, 0};
  Root commit{};
  for (Ref id = committed_; id > input; id = commit.transactionStart - 1) {
    if (!read(id, Kind::Commit, commit) || !commit.transactionStart || commit.transactionStart > id)
      return {Error::Corrupt, 0};
    if (commit.saveKind == kind && commit.savedInput == input) return {Error::Ok, commit.savedOutput};
    board::poll();
  }
  return {Error::NotFound, 0};
}

bool Journal::get(Ref id, Kind kind, void* target, uint8_t length) {
  const uint8_t* frame = load(id);
  if (!frame) return false;
  if (frame[KindAt] != static_cast<uint8_t>(kind) || frame[LengthAt] != length) return fail(Error::Corrupt);
  memcpy(target, frame + PayloadAt, length);
  return true;
}

bool Journal::scan(Cursor& cursor, Kind kind, void* target, uint8_t length) {
  if (!cursor.remaining) return false;
  while (cursor.next && cursor.next <= cursor.last) {
    const uint8_t* frame = load(cursor.next++);
    if (!frame) return false;
    if (frame[KindAt] == static_cast<uint8_t>(kind) && readValue<Ref>(frame + OwnerAt) == cursor.owner) {
      if (frame[LengthAt] != length) return fail(Error::Corrupt);
      memcpy(target, frame + PayloadAt, length);
      --cursor.remaining;
      return true;
    }
    board::poll();
  }
  return fail(Error::Corrupt);
}

bool Journal::peek(const Span& span, uint16_t index, Kind kind, void* target, uint8_t length) {
  if (index >= span.count) return false;
  Cursor cursor(span);
  do { if (!scan(cursor, kind, target, length)) return false; } while (index--);
  return true;
}

bool Journal::push(Span& span, Kind kind, const void* data, uint8_t length) {
  if (span.count == UINT16_MAX) return fail(Error::Full);
  const Ref id = append(kind, span.first ? span.first : nextId(), data, length);
  if (!id) return false;
  if (!span.first) span.first = id;
  span.last = id;
  ++span.count;
  return true;
}

Ref Journal::text(const char* value, uint8_t max) {
  const size_t length = strlen(value);
  if (!length || length > max || length > PayloadBytes) { fail(Error::Input); return 0; }
  for (size_t i = 0; i < length; ++i) {
    const char c = value[i];
    if (c < ' ' || c > '~' || c == '|' || c == '"' || c == '\\') { fail(Error::Input); return 0; }
  }
  return append(Kind::Text, 0, value, static_cast<uint8_t>(length));
}

bool Journal::readText(Ref id, char (&value)[PayloadBytes + 1]) {
  value[0] = 0;
  if (!id) return true;
  const uint8_t* frame = load(id);
  if (!frame) return false;
  if (frame[KindAt] != static_cast<uint8_t>(Kind::Text)) return fail(Error::Corrupt);
  memcpy(value, frame + PayloadAt, frame[LengthAt]);
  value[frame[LengthAt]] = 0;
  return true;
}

}  // namespace conmt
