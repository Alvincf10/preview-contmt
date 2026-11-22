#pragma once

#include "Domain.h"

namespace conmt {

enum class Kind : uint8_t { Commit = 1, Text, Identity, Settings, Baseline, Mix, Row, Model,
                            Factor, Point, Session, Result, BaselineRef, Pad, Clock };

struct Cursor {
  Ref next;
  Ref last;
  Ref owner;
  uint16_t remaining;

  explicit Cursor(const Span& span) : next(span.first), last(span.last), owner(span.first),
                               remaining(span.count) {}
};

class Journal {
 public:
  static constexpr uint8_t PayloadBytes = 64;

  bool mount();
  bool begin();
  void abandon();
  bool commit(SaveKind kind = SaveKind::None, Ref input = 0, Ref output = 0);
  Answer findSave(SaveKind kind, Ref input);

  const Root& root() const { return root_; }
  Root& pending() { return pending_; }
  Error error() const { return error_; }
  Ref committed() const { return committed_; }
  Ref nextId() const { return written_ + 1; }

  Ref text(const char* value, uint8_t max);
  bool readText(Ref id, char (&value)[PayloadBytes + 1]);

  template<class T> Ref add(Kind kind, const T& item, Ref owner = 0) {
    static_assert(sizeof(T) <= PayloadBytes, "Record does not fit in one journal slot");
    return append(kind, owner, &item, sizeof(T));
  }

  template<class T> bool read(Ref id, Kind kind, T& item) {
    return get(id, kind, &item, sizeof(T));
  }

  template<class T> bool next(Cursor& cursor, Kind kind, T& item) {
    return scan(cursor, kind, &item, sizeof(T));
  }

  template<class T> bool at(const Span& span, uint16_t index, Kind kind, T& item) {
    return peek(span, index, kind, &item, sizeof(T));
  }

  template<class T> bool extend(Span& span, Kind kind, const T& item) {
    return push(span, kind, &item, sizeof(T));
  }

 private:
  Root root_{};
  Root pending_{};
  Ref committed_ = 0;
  Ref written_ = 0;
  Error error_ = Error::Storage;
  bool open_ = false;
  bool writing_ = false;

  const uint8_t* load(Ref id);
  bool validate(Ref first, Ref last);
  bool get(Ref id, Kind kind, void* target, uint8_t length);
  bool scan(Cursor& cursor, Kind kind, void* target, uint8_t length);
  bool peek(const Span& span, uint16_t index, Kind kind, void* target, uint8_t length);
  bool push(Span& span, Kind kind, const void* data, uint8_t length);
  Ref append(Kind kind, Ref owner, const void* data, uint8_t length);
  bool fail(Error error);
};

uint32_t checksum(const void* data, uint8_t length);

}  // namespace conmt
