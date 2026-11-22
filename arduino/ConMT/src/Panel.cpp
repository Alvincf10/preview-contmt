#include "Panel.h"
#include "Board.h"
#include "Engine.h"

#include <math.h>
#include <string.h>

#ifdef __AVR__
#include <avr/pgmspace.h>
#define FLASH PROGMEM
#define FSTR(s) PSTR(s)
#else
#define FLASH
#define FSTR(s) (s)
#endif

namespace conmt {
namespace panel {
namespace {

enum Page : uint8_t { Init, User, Main, Base, NewBase, Material, Maturity, BaseResult,
                      Saved, Kuat, Select, Realtime, Strength, History, Detail, Set, Device };
enum Verb : uint8_t { Ready, Nav, Edit, UserSave, New, Focus, Row, Sensor, Early, Lab, Fill,
                      RowDelete, Schedule, Generate, BaseSave, Pick, Open, BaseDelete, Start,
                      Resume, Check, CheckEdit, Prepare, ResultSave, HistoryPick, Options,
                      OptionsSave, Retry, Confirm, Cancel, Clock, Get, Storage, VerbCount };
enum View : uint8_t { Status, IdentityView, BaselineView, MixView, ModelView, LabRowView,
                      SavedRowView, RunView, PointView, HistoryRowView, DetailView,
                      CurveView, ScatterView, ViewCount };

constexpr uint32_t pages(uint8_t page) { return 1UL << page; }
constexpr uint32_t Any = (1UL << (Device + 1)) - 1;
constexpr uint32_t Author = pages(NewBase) | pages(Material) | pages(Maturity) | pages(BaseResult);
constexpr uint32_t Roster = pages(Saved) | pages(Select);
constexpr uint32_t ReadRun = pages(Realtime) | pages(Strength) | pages(Detail);
constexpr uint32_t edges[] FLASH = {
  pages(User) | pages(Main) | pages(Device), pages(Device),
  pages(User) | pages(Base) | pages(Kuat) | pages(Set) | pages(Device),
  pages(Main) | pages(Saved), pages(Base) | pages(Material), pages(NewBase) | pages(Maturity),
  pages(Material) | pages(Saved), pages(Maturity), pages(Base),
  pages(Main) | pages(Select) | pages(History), pages(Kuat), pages(Select), pages(Realtime),
  pages(Kuat), pages(History), pages(Main), pages(Main) | pages(User)
};
struct Rule { uint32_t pageMask; uint8_t sizes; };
const Rule rules[] FLASH = {
  {Any, 1}, {Any, 2}, {Author | pages(User) | pages(Set), 4}, {pages(User), 1}, {pages(Base), 1},
  {pages(Maturity), 2}, {pages(Maturity), 8}, {pages(Maturity), 2}, {pages(Maturity), 1},
  {pages(Maturity), 1}, {pages(Maturity), 1}, {pages(Maturity), 2}, {pages(Maturity), 2},
  {pages(Maturity), 1}, {pages(BaseResult), 2}, {Roster, 2}, {pages(Saved), 1}, {pages(Saved), 2},
  {pages(Select), 1}, {pages(Select) | pages(Kuat), 1}, {pages(Realtime), 19},
  {pages(Realtime), 8}, {pages(Realtime), 1}, {pages(Strength), 2}, {pages(History), 2},
  {pages(Set), 4}, {pages(Set), 1}, {Any, 4}, {Any, 2}, {Any, 2}, {Any, 4},
  {Any, 6}, {Any, 1}
};
static_assert(sizeof(rules) / sizeof(rules[0]) == VerbCount, "Provide a rule per verb");

const char pageNames[] FLASH = "pInit\0pUser\0pMain\0pBase\0pNewB\0pMat\0pMatu\0pBaseR\0"
                               "pSaveB\0pKuat\0pSelB\0pRT\0pStr\0pHist\0pHistD\0pSet\0pDev";
const char verbs[] FLASH =
    "PAGE_READY\0NAV\0FIELD_SET\0USER_SAVE\0BASE_NEW\0ROW_FOCUS\0ROW_SET\0ROW_SENSOR\0"
    "ROW_ADD_EARLY\0ROW_ADD_LAB\0ROW_FILL_EARLY\0ROW_DELETE\0ROW_SCHEDULE\0"
    "BASE_GENERATE\0BASE_SAVE\0BASE_PICK\0BASE_OPEN\0BASE_DELETE\0MEASURE_START\0MEASURE_RESUME\0"
    "CHECK_ADD\0CHECK_SET\0RESULT_PREPARE\0RESULT_SAVE\0HISTORY_PICK\0SETTINGS_SET\0"
    "SETTINGS_SAVE\0RETRY\0CONFIRM\0CANCEL\0CLOCK_SET\0GET\0STORAGE_RETRY";
const char fields[] FLASH =
    "operator\0project\0date\0name\0target\0datum\0pourDate\0pourClock\0"
    "cement\0water\0coarse\0fine\0retarder\0accelerator\0flyAsh\0retarderBrand\0"
    "acceleratorBrand\0flyAshBrand\0day\0age\0clock\0temp\0fc\0"
    "interval\0hour\0minute\0second\0brightness\0sound\0autoSave\0timestamp\0gap";
const char views[] FLASH =
    "status\0identity\0baseline\0mix\0model\0labrow\0savedrow\0run\0point\0historyrow\0"
    "detail\0curve\0scatter";

Engine engine;
Page page = Init;
Verb pending = VerbCount;
Ref pendingValue = 0;
Ref selected = 0;
Ref selectedHistory = 0;
Ref preview = 0;
Ref knownActive = 0;
uint32_t view = 1;
uint32_t boot = 0;
uint32_t sequence = 0;
uint32_t fingerprint = 0;
uint32_t lastByte = 0;
uint32_t lastFrame = 0;
Answer previous{Error::Ok, 0};
char line[192];
uint8_t received = 0;
bool overflow = false;
bool ready = false;

char getChar(const char* text) {
#ifdef __AVR__
  return pgm_read_byte(text);
#else
  return *text;
#endif
}

uint32_t getMask(const uint32_t* value) {
#ifdef __AVR__
  return pgm_read_dword(value);
#else
  return *value;
#endif
}

const char* word(const char* table, uint8_t index) {
  while (index--) while (getChar(table++)) {}
  return table;
}

uint8_t lookup(const char* value, const char* table, uint8_t count) {
  for (uint8_t i = 0; i < count; ++i) {
    const char* p = value;
    char c;
    do { c = getChar(table++); } while (c && *p++ == c);
    if (!c && !*p) return i;
    if (c) while (getChar(table++)) {}
  }
  return count;
}

void flash(const char* text) {
  while (const char c = getChar(text++)) board::transmit(c);
}

void end() {
  for (uint8_t i = 0; i < 3; ++i) board::transmit(0xff);
}

void digits(uint32_t value, uint8_t width = 1, uint8_t fraction = 0) {
  char buffer[12];
  uint8_t used = 0;
  while (fraction--) {
    const uint8_t digit = value % 10;
    if (digit || used) buffer[used++] = '0' + digit;
    value /= 10;
  }
  if (used) buffer[used++] = '.';
  uint8_t count = 0;
  do {
    buffer[used++] = '0' + value % 10;
    value /= 10;
    ++count;
  } while (value || count < width);
  while (used) board::transmit(buffer[--used]);
}

void id(const char* assignment, uint32_t value) {
  flash(assignment);
  digits(value);
  end();
}

void beginData() { flash(FSTR("tData.txt=\"")); }
void finishData() { board::transmit('"'); end(); }
void sep() { board::transmit('|'); }

void scaled(Scaled value, uint8_t decimals = 0) {
  if (value == Missing) return;
  if (value < 0) { board::transmit('-'); value = -value; }
  digits(value, 1, decimals);
}

void real(Real value, uint8_t decimals) {
  if (!isfinite(value)) return;
  uint32_t multiplier = 1;
  for (uint8_t i = 0; i < decimals; ++i) multiplier *= 10;
  value *= multiplier;
  if (value >= 2147483520.0 || value <= -2147483520.0) return;
  scaled(static_cast<Scaled>(value + (value < 0 ? -0.5 : 0.5)), decimals);
}

void storedText(Ref ref) {
  char buffer[Journal::PayloadBytes + 1];
  if (engine.disk.readText(ref, buffer)) {
    for (const char* p = buffer; *p; ++p) board::transmit(*p);
  }
}

void localDate(const Stamp& stamp) {
  if (stamp.day == NoDate) return;
  uint16_t year;
  uint8_t month, day;
  calendar(stamp.day, year, month, day);
  digits(year, 4); board::transmit('-'); digits(month, 2); board::transmit('-'); digits(day, 2);
}

void localTime(uint32_t seconds) {
  if (seconds >= DaySeconds) return;
  const uint16_t minutes = seconds / 60;
  digits(minutes / 60, 2); board::transmit(':'); digits(minutes % 60, 2);
  board::transmit(':'); digits(seconds % 60, 2);
}

void timestamp(const Stamp& stamp) {
  localDate(stamp);
  sep();
  if (stamp.day != NoDate) localTime(stamp.second);
}

void sensors(const Sensors& data) {
  for (uint8_t i = 0; i < 3; ++i) {
    if (data.valid & (1 << i)) real(static_cast<Real>(data.channel[i]) / Scale, 1);
    sep();
  }
  if (data.valid) real(static_cast<Real>(average(data, false)) / Scale, 1);
  sep(); digits(data.valid);
}

Answer ok(Ref value = 0) { return {Error::Ok, value}; }
Answer bad(Error error) { return {error, 0}; }
Answer absent() { return bad(engine.disk.error() == Error::Ok ? Error::NotFound : engine.disk.error()); }

bool on(uint32_t mask) { return mask & pages(page); }

void advanceView() { view = view == Answer::MaxValue ? 1 : view + 1; }

Answer go(Page target, Answer result = {Error::Ok, 0}) {
  if (result.error() == Error::Ok && page != target) {
    page = target;
    ready = false;
    pending = VerbCount;
    advanceView();
  }
  return result;
}

void openPage() {
  flash(FSTR("page "));
  flash(word(pageNames, page));
  end();
}

void dim() { id(FSTR("dim="), engine.config.brightness); }

void publish() {
  id(FSTR("nBoot.val="), boot);
  id(FSTR("nView.val="), view);
}

void ack(uint32_t seq, Answer answer) {
  id(FSTR("nAckValue.val="), answer.value());
  id(FSTR("nAckCode.val="), static_cast<uint8_t>(answer.error()));
  id(FSTR("nAckSeq.val="), seq);
}

Ref runRef(Result& result) {
  if (page == Detail) {
    return selectedHistory && engine.disk.read(selectedHistory, Kind::Result, result) ? result.session : 0;
  }
  return page == Strength ? preview : engine.disk.root().active;
}

Ref baseRef() {
  if (on(Roster)) return selected;
  if (on(ReadRun)) {
    Result result;
    Session& run = engine.workingRecords().session;
    const Ref ref = runRef(result);
    return ref && engine.disk.read(ref, Kind::Session, run) ? run.baseline : 0;
  }
  return engine.disk.root().draft;
}

void baseData(Ref ref, const Baseline& base) {
  digits(ref); sep(); storedText(base.name); sep(); scaled(base.target, 5);
  sep(); scaled(base.datum); sep(); timestamp(base.pour); sep(); digits(base.rows.count);
  sep(); digits(base.model); sep(); digits(base.identity);
}

void identityData(Ref ref) {
  Identity data;
  if (!engine.identity(ref, data)) return;
  storedText(data.operatorName); sep(); storedText(data.project); sep(); localDate({data.date, 0});
}

void prediction(Real maturity, Real fc, Scaled target) {
  real(maturity, 0); sep(); real(fc, 1); sep();
  if (target > 0) real(fc * Scale * 100 / target, 0);
}

Answer pointData(uint16_t index) {
  Result saved;
  auto& records = engine.workingRecords();
  Session& run = records.session;
  Baseline& base = records.baseline;
  const Ref ref = runRef(saved);
  if (!ref || !engine.disk.read(ref, Kind::Session, run) || !engine.baseline(run.baseline, base))
    return absent();
  Point& point = records.point;
  if (!engine.disk.at(run.points, index, Kind::Point, point)) return absent();
  Real fc;
  if (!engine.strength(base, point, fc)) return absent();
  beginData();
  scaled(point.day, 3); sep(); timestamp(point.at); sep(); scaled(point.temperature, 5);
  sep(); prediction(point.maturity, fc, base.target); sep(); digits(point.flags);
  sep(); sensors(point.sensors);
  finishData();
  return ok(run.points.count);
}

Answer runData(View source) {
  Result saved;
  auto& records = engine.workingRecords();
  Session& run = records.session;
  Point& first = records.previous;
  Point& last = records.point;
  Real fc;
  uint32_t seconds = 0;
  const Ref ref = runRef(saved);
  if (!engine.result(ref, run, first, last, fc, page == Strength)) return absent();
  elapsed(first.at, last.at, seconds);
  beginData();
  if (source == DetailView) {
    digits(selectedHistory); sep(); timestamp(saved.savedAt); sep(); identityData(run.identity);
  } else {
    digits(ref); sep(); digits(run.baseline); sep(); digits(run.points.count);
    sep(); digits(run.partial); sep(); timestamp(first.at); sep(); timestamp(last.at);
    sep(); scaled(first.temperature, 5); sep(); digits(seconds); sep();
    prediction(last.maturity, page == Detail ? saved.fc : fc, records.baseline.target);
  }
  finishData();
  return ok(ref);
}

Real curveStart(Real crossing, Real upper) {
  if (crossing <= 0) return 1;
  if (crossing >= log(upper)) return upper;
  // Positive binary32 encodings have the same order as their values.
  uint32_t from = 0x3f800000UL;
  uint32_t to;
  memcpy(&to, &upper, sizeof(to));
  while (to - from > 1) {
    const uint32_t middle = from + (to - from) / 2;
    Real value;
    memcpy(&value, &middle, sizeof(value));
    if (log(value) < crossing) from = middle;
    else to = middle;
  }
  Real result;
  memcpy(&result, &to, sizeof(result));
  return result;
}

Answer chart(const Baseline& base, const Model& model, View source, uint16_t index) {
  Real x, y;
  Real maxX = 20000;
  if (model.maxM > maxX) {
    const uint32_t intervals = static_cast<uint32_t>(model.maxM / 5000);
    maxX = static_cast<Real>(intervals) * 5000;
    if (maxX < model.maxM) maxX += 5000;
  }
  if (source == CurveView) {
    if (index > 64) return bad(Error::NotFound);
    const Real origin = model.fit.b ? curveStart(-model.fit.a / model.fit.b, maxX * 0.02f) : 1;
    x = origin + (maxX - origin) * index / 64;
    y = model.fit.a + model.fit.b * log(x);
  } else {
    Integral maturity;
    Cursor cursor(base.rows);
    LabRow sample;
    while (engine.disk.next(cursor, Kind::Row, sample)) {
      maturity.add(sample.age, sample.temperature, base.datum);
      if (sample.fc > 0 && maturity.maturity > 0 && !index--) {
        x = maturity.maturity;
        y = static_cast<Real>(sample.fc) / Scale;
        goto gotPair;
      }
    }
    return absent();
  }
 gotPair:
  beginData();
  real(x, 2); sep(); real(y, 3); sep(); real(maxX, 0);
  finishData();
  return ok();
}

Answer readView(View source, uint16_t index) {
  const Root& root = engine.disk.root();
  switch (source) {
    case Status: {
      const uint16_t supply = board::supplyMv();
      const Stamp now = board::now();
      const Sensors sensor = board::temperatures();
      beginData();
      timestamp(now); sep(); digits(supply); sep();
      const int16_t battery = board::batteryPercent(supply);
      if (battery >= 0) digits(battery);
      sep(); digits(static_cast<uint8_t>(engine.disk.error())); sep(); digits(root.active);
      sep(); digits(engine.config.interval); sep(); digits(engine.config.brightness);
      sep(); digits(engine.config.flags); sep(); flash(FSTR("1.0.0"));
      sep(); sensors(sensor); sep(); digits(selected);
      sep(); digits(selectedHistory); sep(); digits(root.identityReady);
      sep(); digits(root.draftFromSaved); sep(); digits(root.baselines.count);
      finishData();
      return ok();
    }
    case IdentityView:
      beginData(); identityData(root.identity); finishData();
      return ok(root.identity);
    case PointView:
      return on(ReadRun) ? pointData(index) : bad(Error::State);
    case RunView:
    case DetailView:
      return on(source == DetailView ? pages(Detail) : ReadRun) ? runData(source) : bad(Error::State);
    case HistoryRowView: {
      Ref ref;
      Result result;
      Session& run = engine.workingRecords().session;
      Baseline& base = engine.workingRecords().baseline;
      if (page != History || !engine.historyAt(index, ref, result) ||
          !engine.disk.read(result.session, Kind::Session, run) || !engine.baseline(run.baseline, base))
        return absent();
      beginData();
      digits(ref); sep(); storedText(base.name); sep(); timestamp(result.savedAt);
      sep(); real(result.fc, 1); sep(); digits(run.points.count);
      sep(); digits(result.partial);
      finishData();
      return ok(ref);
    }
    default: break;
  }
  Ref ref = baseRef();
  if (source == SavedRowView && (!on(Roster) ||
      !engine.disk.at(root.baselines, index, Kind::BaselineRef, ref))) return absent();
  Baseline& base = engine.workingRecords().baseline;
  if (source >= ViewCount || !engine.baseline(ref, base)) return absent();
  switch (source) {
    case BaselineView:
    case SavedRowView:
      beginData(); baseData(ref, base); finishData();
      return ok(ref);
    case MixView: {
      Mix mix;
      if (!engine.material(base.mix, mix)) return absent();
      beginData();
      for (const Scaled entry : mix.quantities) { scaled(entry, 5); sep(); }
      for (const Ref brand : mix.brands) { storedText(brand); sep(); }
      if (mix.quantities[Cement] > 0 && mix.quantities[Water] >= 0)
        real(static_cast<Real>(mix.quantities[Water]) / mix.quantities[Cement], 2);
      finishData();
      return ok();
    }
    case LabRowView: {
      LabRow row;
      if (!engine.disk.at(base.rows, index, Kind::Row, row)) return absent();
      beginData();
      digits(row.id); sep(); scaled(row.day, 3); sep(); timestamp(forward(base.pour, row.age));
      sep(); scaled(row.temperature, 5); sep(); scaled(row.fc, 5); sep(); digits(row.age);
      finishData();
      return ok(base.rows.count);
    }
    case ModelView:
    case CurveView:
    case ScatterView: {
      Model model;
      if (!base.model || !engine.disk.read(base.model, Kind::Model, model)) return absent();
      if (source != ModelView) return chart(base, model, source, index);
      beginData();
      real(model.fit.a, 4); sep(); real(model.fit.b, 4); sep(); real(model.fit.r2, 4);
      sep(); digits(model.fit.count); sep(); digits(model.factors.count);
      sep(); real(model.maxM, 0); sep(); identityData(base.identity);
      finishData();
      return ok(base.model);
    }
    default: return bad(Error::Input);
  }
}

Field field(const char* name) {
  return static_cast<Field>(lookup(name, fields, static_cast<uint8_t>(Field::ClearGap) + 1));
}

bool allowedEdit(Field key) {
  switch (page) {
    case User: return key <= Field::Date;
    case NewBase: return key >= Field::Name && key <= Field::PourClock;
    case Material: return key >= Field::Cement && key <= Field::FlyAshBrand;
    case Maturity: return key == Field::PourDate || key == Field::PourClock;
    case Set: return key >= Field::Interval && key <= Field::AutoSave;
    default: return false;
  }
}

bool timeArgs(const char* dayText, const char* clockText, Stamp& stamp) {
  uint32_t day, second;
  if (!date(dayText, day) || !clock(clockText, second)) return false;
  stamp = {day, second};
  return true;
}

Answer ask(Verb what, Ref value) {
  pending = what;
  pendingValue = value;
  return {Error::Confirm, view};
}

Answer confirmed(Verb what) {
  if (what == Start) return go(Realtime, engine.start(pendingValue));
  if (what == RowDelete) return engine.deleteRow(pendingValue);
  const Answer result = engine.deleteBaseline(pendingValue);
  if (result.error() == Error::Ok && selected == pendingValue) selected = 0;
  return result;
}

Answer navigate(Ref destination) {
  if (destination > Device || !(getMask(edges + page) & pages(destination))) return bad(Error::State);
  const Root& root = engine.disk.root();
  if (page == Init && destination == Main && !root.identityReady) return bad(Error::State);
  if (page == Maturity && destination != (root.draftFromSaved ? Saved : Material)) return bad(Error::State);
  if (page == Device && destination != (root.identityReady ? Main : User)) return bad(Error::State);
  return go(static_cast<Page>(destination));
}

Answer rowAction(Verb verb, uint16_t index, const char* const* args) {
  if (verb == Row) return engine.row(index, field(args[1]), args[2]);
  if (verb == Sensor) return engine.row(index, Field::Temperature, "", true);
  Baseline& base = engine.workingRecords().baseline;
  LabRow row;
  if (!engine.baseline(engine.disk.root().draft, base) ||
      !engine.disk.at(base.rows, index, Kind::Row, row)) return absent();
  if (verb == RowDelete) return ask(verb, index);
  if (verb == Schedule) return readView(LabRowView, index);
  return ok(row.id);
}

Answer appendCheckpoint(const char* const* args, uint8_t count) {
  Scaled day = Missing, temperature = Missing;
  Stamp stamp{NoDate, 0};
  if (count && !number(args[0], 3, day)) return bad(Error::Input);
  if (count == 4 && (!timeArgs(args[1], args[2], stamp) || !number(args[3], 5, temperature)))
    return bad(Error::Input);
  return engine.checkpoint(day, stamp, temperature, count == 4, false);
}

Answer execute(Verb verb, const char* const* args, uint8_t count) {
  if (verb >= VerbCount || !(getChar(reinterpret_cast<const char*>(&rules[verb].sizes)) & (1 << count)))
    return bad(Error::Input);
  if (!on(getMask(&rules[verb].pageMask))) return bad(Error::State);
  const Verb confirmation = pending;
  if (verb != Get && verb != Retry) pending = VerbCount;
  const Root& root = engine.disk.root();
  uint32_t value = UINT32_MAX;
  if (count) integer(args[0], value);
  switch (verb) {
    case Nav: return navigate(value);
    case Edit:
    case Options: {
      const Field key = field(args[0]);
      if (!allowedEdit(key)) return bad(Error::Input);
      const Answer result = engine.set(key, args[1]);
      if (result.error() == Error::Ok && key == Field::Brightness) dim();
      return result;
    }
    case UserSave: return go(Main, engine.saveIdentity());
    case OptionsSave: return go(Main);
    case New: return go(NewBase, engine.draft(0));
    case Open: return selected ? go(Maturity, engine.draft(selected)) : bad(Error::State);
    case Pick:
    case BaseDelete:
      if (!engine.exists(value)) return absent();
      if (verb == BaseDelete) return ask(verb, value);
      selected = value;
      return ok(value);
    case Row:
    case Sensor:
    case Focus:
    case Schedule:
    case RowDelete:
      if (value <= UINT16_MAX) return rowAction(verb, value, args);
      break;
    case Early:
    case Lab:
    case Fill:
      return engine.addRows(verb != Lab, verb == Fill);
    case Generate: return go(BaseResult, engine.generate());
    case BaseSave:
      if (value == root.draft) {
        const Answer result = engine.saveBaseline(value);
        if (result.error() == Error::Ok) selected = result.value();
        return go(Saved, result);
      }
      return bad(Error::Stale);
    case Start:
      if (!selected) return bad(Error::State);
      return root.active ? ask(verb, selected) : go(Realtime, engine.start(selected));
    case Resume:
      return root.active ? go(Realtime, ok(root.active)) : bad(Error::State);
    case Check: return appendCheckpoint(args, count);
    case CheckEdit:
      if (value <= UINT16_MAX) return engine.editPoint(value, field(args[1]), args[2]);
      break;
    case Prepare:
      if (!root.active) return bad(Error::State);
      preview = root.active;
      return go(Strength, ok(preview));
    case ResultSave:
      if (value == preview) {
        const Answer result = engine.saveResult(value);
        if (result.error() == Error::Ok) selectedHistory = result.value();
        if (result.error() == Error::NotFound) return bad(Error::Stale);
        return go(History, result);
      }
      return bad(Error::Stale);
    case HistoryPick: {
      Result result;
      Ref ref;
      if (value > UINT16_MAX || !engine.historyAt(value, ref, result)) return absent();
      selectedHistory = ref;
      return go(Detail, ok(ref));
    }
    case Clock: {
      Stamp time;
      return timeArgs(args[0], args[1], time) ? engine.clockSet(time) : bad(Error::Input);
    }
    case Retry: {
      if (!integer(args[1], value) || !value) break;
      const Verb save = static_cast<Verb>(lookup(args[0], verbs, VerbCount));
      if (save == BaseSave || save == ResultSave)
        return engine.disk.findSave(save == BaseSave ? SaveKind::Baseline : SaveKind::Result, value);
      break;
    }
    case Get: {
      if (count == 1) value = 0;
      else if (!integer(args[1], value) || value > UINT16_MAX) break;
      const View source = static_cast<View>(lookup(args[0], views, ViewCount));
      if (source < ViewCount) return readView(source, static_cast<uint16_t>(value));
      break;
    }
    case Confirm:
    case Cancel:
      if (confirmation != VerbCount && value == view) return verb == Cancel ? ok() : confirmed(confirmation);
      return bad(Error::Stale);
    case Storage:
      if (!engine.recover()) return absent();
      selected = selectedHistory = preview = 0;
      return go(root.identityReady ? Main : User);
    default: break;
  }
  return bad(Error::Input);
}

void dispatch() {
  if (received && line[received - 1] == '\r') --received;
  line[received] = 0;
  const uint32_t hash = checksum(line, received);
  const char* parts[10]{line};
  uint8_t count = 1;
  for (uint8_t i = 0; i < received; ++i) {
    if (line[i] == '|') {
      if (count == 10) return;
      line[i] = 0;
      parts[count++] = line + i + 1;
    } else if (line[i] < ' ' || line[i] > '~') return;
  }
  uint32_t requestedBoot, seq, requestedPage, requestedView;
  if (count < 6 || strcmp(parts[0], "CM1") || !integer(parts[1], requestedBoot) ||
      !integer(parts[2], seq) || seq > INT32_MAX || !integer(parts[3], requestedPage) ||
      requestedPage > Device || !integer(parts[4], requestedView)) return;
  const Verb verb = static_cast<Verb>(lookup(parts[5], verbs, VerbCount));
  if (verb == Ready) {
    if (count != 6 || (requestedBoot && requestedBoot != boot)) { ack(seq, bad(Error::Version)); return; }
    if (!requestedBoot) { sequence = 0; pending = VerbCount; }
    if (requestedPage != page) { openPage(); return; }
    ready = true;
    lastFrame = board::ticks();
    flash(FSTR("bkcmd=0")); end();
    dim();
    publish();
    ack(seq, ok(engine.disk.committed()));
    return;
  }
  if (!ready || !seq || requestedBoot != boot || requestedPage != page) {
    ack(seq, bad(Error::Stale)); return;
  }
  lastFrame = board::ticks();
  if (seq <= sequence) {
    const bool replay = seq == sequence && hash == fingerprint;
    if (replay && (verb == Get || verb == Schedule) && requestedView == view)
      previous = execute(verb, parts + 6, count - 6);
    ack(seq, replay ? previous : bad(Error::Stale));
    return;
  }
  if (requestedView != view) { publish(); ack(seq, bad(Error::Stale)); return; }
  const Page old = page;
  sequence = seq;
  fingerprint = hash;
  previous = execute(verb, parts + 6, count - 6);
  if (previous.error() == Error::Ok && old == page && verb != Get && verb != Schedule &&
      verb != Focus && verb != Retry) {
    advanceView();
    publish();
  }
  knownActive = engine.disk.root().active;
  ack(seq, previous);
  if (previous.error() == Error::Ok && verb != Get && verb != Retry)
    board::beep(engine.config.flags & Sound);
  if (old != page) openPage();
}

}  // namespace

void begin() {
  engine.recover();
  boot = (engine.disk.committed() * 2654435761UL + board::ticks() + 1) & INT32_MAX;
  if (!boot) boot = 1;
  page = Init;
  knownActive = engine.disk.root().active;
}

void poll() {
  const uint32_t now = board::ticks();
  if ((received || overflow) && now - lastByte > 1200) { received = 0; overflow = false; }
  for (uint8_t budget = 32; budget; --budget) {
    const int input = board::receive();
    if (input == -2) { received = 0; overflow = true; lastByte = now; break; }
    if (input < 0) break;
    lastByte = now;
    if (input == '\n') {
      if (!overflow) dispatch();
      received = 0;
      overflow = false;
    } else if (input == 0xff) {
      received = 0;
      overflow = false;
    } else if (received < sizeof(line) - 1 && !overflow) {
      line[received++] = static_cast<char>(input);
    } else overflow = true;
  }
  engine.tick(page != Strength || !ready || now - lastFrame >= 10000);
  if (knownActive != engine.disk.root().active) {
    knownActive = engine.disk.root().active;
    advanceView();
    pending = VerbCount;
    if (ready) publish();
  }
}
}  // namespace panel
}  // namespace conmt
