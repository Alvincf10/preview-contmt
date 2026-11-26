#include "Engine.h"
#include "Board.h"

#include <math.h>
#include <string.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define EDIT_TABLE PROGMEM
#define EDIT_BYTE(ptr) pgm_read_byte(ptr)
#else
#define EDIT_TABLE
#define EDIT_BYTE(ptr) (*reinterpret_cast<const uint8_t*>(ptr))
#endif

namespace conmt {
namespace {

constexpr Answer ok(Ref value = 0) { return {Error::Ok, value}; }
constexpr Answer bad(Error error) { return {error, 0}; }

enum Input : uint8_t { ShortText, Text, Label, Date, Time, Target, Datum, Quantity };
struct EditSpec { Input input; uint8_t offset; };

// Field IDs in this range are shared with the panel dispatcher.
const EditSpec editSpec[] EDIT_TABLE = {
  {ShortText, offsetof(Identity, operatorName)}, {Text, offsetof(Identity, project)},
  {Date, offsetof(Identity, date)}, {Text, offsetof(Baseline, name)},
  {Target, offsetof(Baseline, target)}, {Datum, offsetof(Baseline, datum)},
  {Date, offsetof(Baseline, pour.day)}, {Time, offsetof(Baseline, pour.second)},
  {Quantity, offsetof(Mix, quantities[0])}, {Quantity, offsetof(Mix, quantities[1])},
  {Quantity, offsetof(Mix, quantities[2])}, {Quantity, offsetof(Mix, quantities[3])},
  {Quantity, offsetof(Mix, quantities[4])}, {Quantity, offsetof(Mix, quantities[5])},
  {Quantity, offsetof(Mix, quantities[6])}, {Label, offsetof(Mix, brands[0])},
  {Label, offsetof(Mix, brands[1])}, {Label, offsetof(Mix, brands[2])}
};
static_assert(sizeof(editSpec) / sizeof(EditSpec) == static_cast<uint8_t>(Field::FlyAshBrand) + 1,
              "Provide a descriptor for each stored metadata field");

bool editMetadata(Journal& disk, void* record, Field field, const char* value) {
  const auto* spec = editSpec + static_cast<uint8_t>(field);
  const Input input = static_cast<Input>(EDIT_BYTE(&spec->input));
  auto* target = static_cast<uint8_t*>(record) + EDIT_BYTE(&spec->offset);
  uint32_t word;
  if (input <= Label) {
    word = input == Label && !*value ? 0 : disk.text(value, input == Text ? 64 : 32);
    if (!word && (input != Label || *value)) return false;
  } else if (input == Date || input == Time) {
    if (!(input == Date ? date(value, word) : clock(value, word))) return false;
  } else {
    Scaled numberValue;
    if (!number(value, input == Datum ? 0 : 5, numberValue)) return false;
    if (input == Datum) {
      if (numberValue != -20 && numberValue != -10 && numberValue != 0 && numberValue != 10)
        return false;
      *target = static_cast<uint8_t>(numberValue);
      static_cast<Baseline*>(record)->datumSet = 1;
      return true;
    }
    if (numberValue < (input == Target ? 1 : 0)) return false;
    word = static_cast<uint32_t>(numberValue);
  }
  memcpy(target, &word, sizeof(word));
  return true;
}

bool precedes(const LabRow& a, const LabRow& b) {
  if (a.age != b.age) return a.age < b.age;
  if (a.day != b.day) return a.day < b.day;
  return a.id < b.id;
}

bool ageHours(const char* text, uint32_t& seconds) {
  Scaled hours;
  if (!number(text, 4, hours) || hours < 0) return false;
  seconds = (hours / 10000) * 3600UL + ((hours % 10000) * 3600UL + 5000) / 10000UL;
  return true;
}

bool rowClock(const Baseline& base, LabRow& row, const char* text) {
  uint32_t time, age;
  if (!validStamp(base.pour) || !clock(text, time) || !labAge(row.day, false, age)) return false;
  const uint32_t offset = (time + DaySeconds - base.pour.second) % DaySeconds;
  if (age > UINT32_MAX - offset) return false;
  row.age = age + offset;
  return true;
}

}  // namespace

bool Engine::recover() {
  config = DefaultSettings;
  if (!disk.mount()) return false;
  gap_ = disk.root().active != 0;
  lastAuto_ = board::ticks();
  return !disk.root().settings || disk.read(disk.root().settings, Kind::Settings, config);
}

Answer Engine::stopped(Error reason) {
  const Error diskError = disk.error();
  disk.abandon();
  return bad(diskError != Error::Ok ? diskError : reason == Error::Ok ? Error::Storage : reason);
}

Answer Engine::done(Ref id) {
  return disk.commit() ? ok(id) : stopped();
}

bool Engine::identity(Ref id, Identity& result) {
  result = {0, 0, NoDate};
  return !id || disk.read(id, Kind::Identity, result);
}

bool Engine::baseline(Ref id, Baseline& result) {
  result = {};
  result.pour.day = NoDate;
  result.datum = -20;
  result.datumSet = 1;
  return !id || disk.read(id, Kind::Baseline, result);
}

bool Engine::material(Ref id, Mix& result) {
  result = {};
  for (uint8_t field = 0; field < MixCount; ++field) result.quantities[field] = Missing;
  return !id || disk.read(id, Kind::Mix, result);
}

bool Engine::exists(Ref id) {
  Cursor cursor(disk.root().baselines);
  Ref item;
  while (disk.next(cursor, Kind::BaselineRef, item)) if (item == id) return true;
  return false;
}

Answer Engine::set(Field field, const char* value) {
  if (field <= Field::Date) return setIdentity(field, value);
  if (field >= Field::Interval) return setSettings(field, value);
  return setBaseline(field, value);
}

Answer Engine::setIdentity(Field field, const char* value) {
  Identity record;
  if (!identity(disk.root().identity, record) || !disk.begin()) return stopped();
  if (!editMetadata(disk, &record, field, value)) return stopped(Error::Input);
  const Ref id = disk.add(Kind::Identity, record);
  disk.pending().identity = id;
  return id ? done(id) : stopped();
}

Answer Engine::saveIdentity() {
  Identity record;
  if (!identity(disk.root().identity, record)) return stopped();
  if (!record.operatorName || !record.project || record.date == NoDate) return bad(Error::MissingData);
  if (!disk.begin()) return stopped();
  disk.pending().identityReady = 1;
  return done(disk.root().identity);
}

Answer Engine::draft(Ref saved) {
  Baseline& record = work_.baseline;
  if (saved && !exists(saved)) return stopped(Error::NotFound);
  if (!baseline(saved ? saved : disk.root().draft, record) || !disk.begin()) return stopped();
  Root& next = disk.pending();
  if (!saved) {
    Identity person;
    if (!identity(next.identity, person)) return stopped();
    record.identity = next.identity;
    record.pour = board::now();
    if (!validStamp(record.pour)) record.pour.second = DaySeconds;
    if (person.date != NoDate) record.pour.day = person.date;
    record.model = 0;
  }
  next.draftFromSaved = saved != 0;
  next.draft = saved ? saved : disk.add(Kind::Baseline, record);
  return next.draft ? done(next.draft) : stopped();
}

Answer Engine::publish(Baseline& record) {
  const Ref id = disk.add(Kind::Baseline, record);
  disk.pending().draft = id;
  return id ? done(id) : stopped();
}

Answer Engine::setBaseline(Field field, const char* value) {
  if (field > Field::FlyAshBrand) return bad(Error::Input);
  if (!disk.root().draft) return bad(Error::State);
  Baseline& record = work_.baseline;
  if (!baseline(disk.root().draft, record) || !disk.begin()) return stopped();
  if (field >= Field::Cement) {
    Mix mix;
    if (!material(record.mix, mix)) return stopped();
    if (!editMetadata(disk, &mix, field, value)) return stopped(Error::Input);
    record.mix = disk.add(Kind::Mix, mix);
    if (!record.mix) return stopped();
  } else if (!editMetadata(disk, &record, field, value)) return stopped(Error::Input);
  record.model = 0;
  return publish(record);
}

Answer Engine::setSettings(Field field, const char* value) {
  uint32_t numberValue;
  if (!integer(value, numberValue)) return bad(Error::Input);
  Settings next = config;
  switch (field) {
    case Field::Interval:
      if (numberValue >= DaySeconds) return bad(Error::Input);
      next.interval = numberValue;
      break;
    case Field::Hour:
    case Field::Minute:
    case Field::Second: {
      const uint16_t unit = field == Field::Hour ? 3600 : field == Field::Minute ? 60 : 1;
      const uint8_t limit = field == Field::Hour ? 24 : 60;
      if (numberValue >= limit) return bad(Error::Input);
      next.interval = next.interval - (next.interval / unit % limit) * unit + numberValue * unit;
      break;
    }
    case Field::Brightness:
      if (numberValue > 100) return bad(Error::Input);
      next.brightness = numberValue;
      break;
    case Field::Sound:
    case Field::AutoSave: {
      if (numberValue > 1) return bad(Error::Input);
      const uint8_t flag = field == Field::Sound ? Sound : AutoSave;
      next.flags = (next.flags & ~flag) | (numberValue ? flag : 0);
      break;
    }
    default: return bad(Error::Input);
  }
  if (!disk.begin()) return stopped();
  const Ref id = disk.add(Kind::Settings, next);
  disk.pending().settings = id;
  if (!id || !disk.commit()) return stopped();
  config = next;
  lastAuto_ = board::ticks();
  return ok(id);
}

uint16_t Engine::rewriteRows(Baseline& record, LabRow* insertion, Ref remove, uint16_t fill) {
  Cursor cursor(record.rows);
  record.rows = {};
  uint16_t slotAge = 0;
  uint16_t inserted = 0;
  LabRow current;
  for (;;) {
    const bool hasRow = disk.next(cursor, Kind::Row, current);
    if (!hasRow && cursor.remaining) return 0;
    if (hasRow && current.id == remove) continue;
    while (fill && (!hasRow || slotAge <= current.age)) {
      if (fill & 1) {
        if (!inserted) inserted = record.rows.count + 1;
        const LabRow added{disk.nextId(), 0, slotAge, Missing, Missing};
        if (!disk.extend(record.rows, Kind::Row, added)) return 0;
      }
      fill >>= 1;
      slotAge += 1800;
    }
    if (insertion && (!hasRow || precedes(*insertion, current))) {
      inserted = record.rows.count + 1;
      if (!insertion->id) insertion->id = disk.nextId();
      if (!disk.extend(record.rows, Kind::Row, *insertion)) return 0;
      insertion = nullptr;
    }
    if (!hasRow) break;
    if (!disk.extend(record.rows, Kind::Row, current)) return 0;
  }
  record.model = 0;
  return inserted ? inserted : 1;
}

Answer Engine::row(uint16_t index, Field field, const char* value, bool sensor) {
  Baseline& record = work_.baseline;
  const Ref draft = disk.root().draft;
  if (!draft || !baseline(draft, record)) return stopped(Error::NotFound);
  LabRow changed;
  const bool first = !record.rows.count && !index;
  if (first) {
    changed.id = changed.day = changed.age = 0;
    changed.temperature = changed.fc = Missing;
  } else if (!disk.at(record.rows, index, Kind::Row, changed)) return stopped(Error::NotFound);
  Scaled parsed;
  if (sensor) {
    changed.temperature = average(board::temperatures(), true);
    if (changed.temperature == Missing) return bad(Error::Sensor);
  } else switch (field) {
    case Field::Day: {
      uint32_t age;
      if (!number(value, 3, parsed) || !labAge(parsed, true, age)) return bad(Error::Input);
      if (parsed != changed.day) {
        if (!changed.day && parsed && changed.fc == Missing) changed.fc = PendingLabFc;
        if (!parsed && changed.fc == PendingLabFc) changed.fc = Missing;
        changed.day = parsed;
        changed.age = age;
      }
      break;
    }
    case Field::Age: {
      uint32_t age;
      if (!ageHours(value, age)) return bad(Error::Input);
      changed.age = age;
      break;
    }
    case Field::Clock:
      if (!rowClock(record, changed, value)) return bad(Error::Input);
      break;
    case Field::Temperature:
    case Field::Fc:
      parsed = Missing;
      if (*value && (!number(value, 5, parsed) || (field == Field::Fc && parsed < 0)))
        return bad(Error::Input);
      if (field == Field::Fc) {
        changed.fc = parsed == Missing && changed.day && changed.fc != Missing ? PendingLabFc : parsed;
      } else changed.temperature = parsed;
      break;
    default: return bad(Error::Input);
  }
  Cursor cursor(record.rows);
  LabRow other;
  while (disk.next(cursor, Kind::Row, other)) {
    if (other.id != changed.id && other.day == changed.day && (other.day || other.age == changed.age))
      return bad(Error::Input);
  }
  if (cursor.remaining || !disk.begin()) return stopped();
  if (!rewriteRows(record, &changed, changed.id, 0)) return stopped();
  return publish(record);
}

Answer Engine::addRows(bool early, bool fill) {
  Baseline& record = work_.baseline;
  if (!disk.root().draft || !baseline(disk.root().draft, record)) return stopped(Error::State);
  uint16_t used = 0;
  Scaled day = DayScale;
  Cursor cursor(record.rows);
  LabRow row;
  while (disk.next(cursor, Kind::Row, row)) {
    if (row.day == day) day += DayScale;
    if (!row.day && row.age <= 21600) {
      const uint16_t age = row.age;
      if (age % 1800U == 0) used |= 1U << (age / 1800U);
    }
  }
  if (cursor.remaining) return stopped();
  uint16_t inserted;
  if (fill) {
    const uint16_t missing = 0x1fff & ~used;
    if (!missing) return ok();
    if (!disk.begin()) return stopped();
    inserted = rewriteRows(record, nullptr, 0, missing);
  } else {
    uint32_t age;
    if (early) {
      day = 0;
      uint8_t slot = 0;
      while (slot < 13 && (used & (1U << slot))) ++slot;
      if (slot == 13) return bad(Error::Full);
      age = slot * 1800UL;
    } else if (!labAge(day, false, age)) return bad(Error::Full);
    if (!disk.begin()) return stopped();
    LabRow added{0, day, age, Missing, early ? Missing : PendingLabFc};
    const uint16_t keepDayZero = !early && !record.rows.count ? 1 : 0;
    inserted = rewriteRows(record, &added, 0, keepDayZero);
  }
  if (!inserted) return stopped();
  const Answer result = publish(record);
  return result.error() == Error::Ok ? ok(inserted) : result;
}

Answer Engine::deleteRow(uint16_t index) {
  Baseline& record = work_.baseline;
  LabRow item;
  if (!baseline(disk.root().draft, record) || !disk.at(record.rows, index, Kind::Row, item))
    return stopped(Error::NotFound);
  if (record.rows.count <= 3) return bad(Error::State);
  if (!disk.begin() || !rewriteRows(record, nullptr, item.id, 0)) return stopped();
  return publish(record);
}

Answer Engine::generate() {
  Baseline& record = work_.baseline;
  const Ref revision = disk.root().draft;
  if (!baseline(revision, record)) return stopped();
  if (!record.name || record.target <= 0 || !record.datumSet || !validStamp(record.pour))
    return bad(Error::MissingData);
  Model model{};
  {
    Regression regression;
    Integral integral;
    Cursor cursor(record.rows);
    LabRow sample;
    Scaled day = 0;
    uint16_t row = 0;
    bool hasLab = false, sawBlank = false, hasGap = false;
    while (disk.next(cursor, Kind::Row, sample)) {
      ++row;
      if (sample.temperature == Missing) {
        if (sample.fc >= 0) return {Error::MissingData, 2U * row};
        sawBlank = true;
        continue;
      }
      if (sample.fc == PendingLabFc) return {Error::MissingData, 2U * row + 1};
      hasGap |= sawBlank;
      hasLab |= sample.fc > 0;
      if (sample.day < day) return bad(Error::Input);
      day = sample.day;
      integral.add(sample.age, sample.temperature, record.datum);
      regression.add(integral.maturity, sample.fc);
      if (sample.fc > 0 && integral.maturity > model.maxM) model.maxM = integral.maturity;
    }
    if (cursor.remaining) return stopped();
    if (!hasLab) return bad(Error::MissingData);
    if (hasGap || !regression.finish(model.fit)) return ok(revision);
  }
  if (!disk.begin()) return stopped();
  Integral integral;
  Cursor cursor(record.rows);
  LabRow sample;
  Factor pending{Missing, 0};
  while (disk.next(cursor, Kind::Row, sample)) {
    if (sample.temperature == Missing) continue;
    integral.add(sample.age, sample.temperature, record.datum);
    if (sample.fc > 0 && integral.maturity > 0) {
      const Real predicted = estimate(integral.maturity, model.fit);
      if (predicted <= 0) continue;
      if (pending.day != Missing && pending.day != sample.day &&
          !disk.extend(model.factors, Kind::Factor, pending)) return stopped();
      const Real actual = static_cast<Real>(sample.fc) / Scale;
      pending = {sample.day, static_cast<float>(correction((predicted - actual) / actual))};
    }
  }
  if (cursor.remaining || (pending.day != Missing && !disk.extend(model.factors, Kind::Factor, pending)))
    return stopped();
  record.model = disk.add(Kind::Model, model);
  return record.model ? publish(record) : stopped();
}

Answer Engine::saveBaseline(Ref revision) {
  Baseline& record = work_.baseline;
  if (revision != disk.root().draft) return disk.findSave(SaveKind::Baseline, revision);
  const Answer saved = disk.findSave(SaveKind::Baseline, revision);
  if (saved.error() != Error::NotFound) return saved;
  if (!baseline(revision, record) || !record.rows.count) return stopped(Error::MissingData);
  if (!disk.begin()) return stopped();
  const Ref id = disk.add(Kind::Baseline, record);
  return id ? updateRoster(id, revision) : stopped();
}

Answer Engine::deleteBaseline(Ref id) {
  if (!exists(id) || !disk.begin()) return stopped(Error::NotFound);
  return updateRoster(id);
}

Answer Engine::updateRoster(Ref id, Ref savedFrom) {
  Root& next = disk.pending();
  Cursor cursor(next.baselines);
  next.baselines = {};
  if (savedFrom && !disk.extend(next.baselines, Kind::BaselineRef, id)) return stopped();
  Ref previous;
  while (disk.next(cursor, Kind::BaselineRef, previous))
    if (previous != id && !disk.extend(next.baselines, Kind::BaselineRef, previous)) return stopped();
  if (cursor.remaining) return stopped();
  if (!savedFrom) return done();
  return disk.commit(SaveKind::Baseline, savedFrom, id) ? ok(id) : stopped();
}

Answer Engine::start(Ref id) {
  Baseline& record = work_.baseline;
  if (!disk.root().identityReady || !exists(id) || !baseline(id, record) || !record.model)
    return stopped(Error::NoFit);
  Point& first = work_.point;
  first = {};
  first.at = board::now();
  if (!validStamp(first.at)) return bad(Error::Clock);
  first.sensors = board::temperatures();
  first.temperature = average(first.sensors, true);
  if (first.temperature == Missing) return bad(Error::Sensor);
  if (!disk.begin()) return stopped();
  Session& session = work_.session;
  session = {id, disk.root().identity, {}, 0};
  if (!disk.extend(session.points, Kind::Point, first)) return stopped();
  const Ref revision = disk.add(Kind::Session, session);
  disk.pending().active = revision;
  if (!revision || !disk.commit()) return stopped();
  lastAuto_ = board::ticks();
  gap_ = false;
  return ok(revision);
}

bool Engine::integrate(const Point& previous, Point& next, int8_t datum) {
  uint32_t seconds;
  if (!elapsed(previous.at, next.at, seconds)) return false;
  Integral integral;
  integral.maturity = previous.maturity;
  integral.compensation = previous.compensation;
  integral.temperature = previous.temperature;
  integral.add(seconds, next.temperature, datum, next.flags & Gap);
  next.maturity = integral.maturity;
  next.compensation = integral.compensation;
  return isfinite(next.maturity);
}

Answer Engine::storePoint(Session& session, Point& point, uint16_t replace) {
  Baseline& base = work_.baseline;
  Point& previous = work_.previous;
  if (!baseline(session.baseline, base) || !disk.read(session.points.last, Kind::Point, previous))
    return stopped();
  if (!disk.begin()) return stopped();
  if (replace == UINT16_MAX && !before(point.at, previous.at)) {
    if (!integrate(previous, point, base.datum)) return stopped(Error::Clock);
    if (!disk.extend(session.points, Kind::Point, point)) return stopped();
    if (point.flags & Gap) session.partial = 1;
  } else {
    Cursor cursor(session.points);
    session.points = {};
    session.partial = 0;
    bool inserted = false;
    auto put = [&](Point& next) {
      if (session.points.count) {
        if (!integrate(previous, next, base.datum)) return false;
      } else next.maturity = next.compensation = 0;
      if (!disk.extend(session.points, Kind::Point, next)) return false;
      previous = next;
      if (next.flags & Gap) session.partial = 1;
      return true;
    };
    Point current;
    uint16_t index = 0;
    while (disk.next(cursor, Kind::Point, current)) {
      if (!inserted && ((replace == 0 && index == 0) || before(point.at, current.at))) {
        if (!put(point)) return stopped(Error::Clock);
        inserted = true;
      }
      if (index++ != replace && !put(current)) return stopped(Error::Clock);
    }
    if (cursor.remaining || (!inserted && !put(point))) return stopped(Error::Clock);
  }
  const Ref revision = disk.add(Kind::Session, session);
  disk.pending().active = revision;
  return revision ? done(revision) : stopped();
}

Answer Engine::checkpoint(Scaled day, const Stamp& time, Scaled temperature, bool manual, bool automatic) {
  const Ref active = disk.root().active;
  if (!active) return bad(Error::State);
  Session& session = work_.session;
  Point& first = work_.previous;
  if (!disk.read(active, Kind::Session, session) || !disk.read(session.points.first, Kind::Point, first))
    return stopped();
  const Stamp& now = board::now();
  if (manual && validStamp(now) && before(now, time)) return bad(Error::Clock);
  const Stamp& pointAt = manual ? time : now;
  uint32_t age;
  if (!elapsed(first.at, pointAt, age)) return bad(Error::Clock);
  if (day == Missing) day = (age / DaySeconds) * DayScale;
  if (day < 0) return bad(Error::Input);
  Point& point = work_.point;
  point.at = pointAt;
  point.day = day;
  point.sensors = manual ? Sensors{} : board::temperatures();
  point.temperature = manual ? temperature : average(point.sensors, true);
  if (point.temperature == Missing) return bad(Error::Sensor);
  point.maturity = point.compensation = 0;
  point.flags = manual ? Manual : (automatic ? Automatic : 0) | (gap_ ? Gap : 0);
  const Answer answer = storePoint(session, point, UINT16_MAX);
  if (answer.error() == Error::Ok && !manual) {
    lastAuto_ = board::ticks();
    gap_ = false;
  }
  return answer;
}

Answer Engine::editPoint(uint16_t index, Field field, const char* text) {
  if (!disk.root().active) return bad(Error::State);
  Session& session = work_.session;
  Point& point = work_.point;
  Point& first = work_.previous;
  if (!disk.read(disk.root().active, Kind::Session, session) ||
      !disk.at(session.points, index, Kind::Point, point) ||
      !disk.read(session.points.first, Kind::Point, first)) return stopped(Error::NotFound);
  uint32_t position;
  Scaled value;
  switch (field) {
    case Field::Date:
      if (!date(text, position)) return bad(Error::Input);
      point.at.day = position;
      break;
    case Field::Clock:
      if (!clock(text, position)) return bad(Error::Input);
      point.at.second = position;
      break;
    case Field::Day:
      if (!number(text, 3, value) || value < 0 || (!index && value)) return bad(Error::Input);
      point.day = value;
      break;
    case Field::Temperature:
      if (!number(text, 5, value)) return bad(Error::Input);
      point.temperature = value;
      break;
    case Field::Timestamp: {
      char day[11];
      uint32_t seconds;
      if (strlen(text) < 16 || text[10] != 'T') return bad(Error::Input);
      memcpy(day, text, 10);
      day[10] = 0;
      if (!date(day, position) || !clock(text + 11, seconds)) return bad(Error::Input);
      point.at = {position, seconds};
      break;
    }
    case Field::ClearGap:
      if ((point.flags & (Gap | Manual)) != (Gap | Manual) || strcmp(text, "0")) return bad(Error::Input);
      point.flags &= ~Gap;
      break;
    default: return bad(Error::Input);
  }
  const Stamp time = board::now();
  if ((index && before(point.at, first.at)) || !validStamp(point.at) ||
      (validStamp(time) && before(time, point.at))) return bad(Error::Clock);
  point.flags |= Manual;
  return storePoint(session, point, index);
}

Answer Engine::clockSet(const Stamp& stamp) {
  if (!validStamp(stamp)) return bad(Error::Clock);
  const Stamp changes[] = {board::now(), stamp};
  if (!disk.begin()) return stopped();
  if (!disk.add(Kind::Clock, changes) || !disk.commit()) return stopped();
  if (!board::setClock(stamp)) return bad(Error::Clock);
  if (disk.root().active) gap_ = true;
  return ok();
}

void Engine::tick(bool autoEnabled) {
  if (!disk.root().active || disk.error() != Error::Ok) return;
  if (!board::temperatures().valid) { gap_ = true; return; }
  if (autoEnabled && (config.flags & AutoSave) && config.interval && validStamp(board::now()) &&
      board::ticks() - lastAuto_ >= config.interval * 1000UL) {
    lastAuto_ = board::ticks();
    checkpoint(Missing, {}, Missing, false, true);
  }
}

bool Engine::strength(Ref id, const Point& point, Real& fc, bool roundMaturity) {
  Baseline& base = work_.baseline;
  return id && baseline(id, base) && strength(base, point, fc, roundMaturity);
}

bool Engine::strength(const Baseline& base, const Point& point, Real& fc, bool roundMaturity) {
  Model model;
  if (!base.model || !disk.read(base.model, Kind::Model, model))
    return false;
  Cursor cursor(model.factors);
  Factor factor;
  Real value = 1;
  while (cursor.remaining) {
    if (!disk.next(cursor, Kind::Factor, factor)) return false;
    value = factor.value;
    if (factor.day >= point.day) break;
  }
  if (disk.error() == Error::Corrupt || disk.error() == Error::Storage) return false;
  const Real maturity = roundMaturity ? roundf(point.maturity) : point.maturity;
  fc = estimate(maturity, model.fit, value);
  return true;
}

bool Engine::result(Ref id, Session& session, Point& first, Point& last, Real& fc,
                    bool roundMaturity) {
  return id && disk.read(id, Kind::Session, session) &&
         disk.read(session.points.first, Kind::Point, first) &&
         disk.read(session.points.last, Kind::Point, last) &&
         strength(session.baseline, last, fc, roundMaturity);
}

Answer Engine::saveResult(Ref revision) {
  if (revision != disk.root().active) return disk.findSave(SaveKind::Result, revision);
  Session& session = work_.session;
  Point& first = work_.previous;
  Point& last = work_.point;
  Real fc;
  if (!result(revision, session, first, last, fc, true)) return stopped(Error::State);
  uint32_t age;
  if (!elapsed(first.at, last.at, age) || !age) return bad(Error::NoInterval);
  const Stamp time = board::now();
  if (!validStamp(time) || before(time, last.at)) return bad(Error::Clock);
  if (!disk.begin()) return stopped();
  Root& next = disk.pending();
  const Result saved{next.history, revision, time, static_cast<float>(fc), session.partial};
  const Ref id = disk.add(Kind::Result, saved);
  next.history = id;
  next.active = 0;
  if (!id || !disk.commit(SaveKind::Result, revision, id)) return stopped();
  return ok(id);
}

bool Engine::historyAt(uint16_t index, Ref& id, Result& result) {
  id = disk.root().history;
  while (id) {
    if (!disk.read(id, Kind::Result, result)) return false;
    if (!index--) return true;
    id = result.previous;
    board::poll();
  }
  return false;
}

}  // namespace conmt
