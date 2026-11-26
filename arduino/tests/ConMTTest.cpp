#include "Board.h"
#include "Battery.h"
#include "Engine.h"
#include "Panel.h"
#include "SpiCard.h"

#undef NDEBUG
#include <assert.h>
#include <math.h>
#include <string.h>
#include <deque>
#include <iostream>
#include <string>
#include <stdlib.h>
#include <vector>

namespace {
using namespace conmt;

const uint32_t CardBlocks = 16384;
const uint32_t RawBlocks = 2048;
const uint32_t LogBlocks = RawBlocks;
uint32_t fileStart = CardBlocks - RawBlocks;
std::vector<uint8_t> image;
std::deque<uint8_t> incoming;
std::string output;
uint32_t tick = 0;
Stamp wall{NoDate, 0};
Sensors live{};
int8_t batteryValue = -1;

enum Fault { None, TearBody, TearAnchor, LostCommitAck };
Fault fault = None;

void write16(size_t offset, uint16_t value) {
  image[offset] = value;
  image[offset + 1] = value >> 8;
}

void write32(size_t offset, uint32_t value) {
  write16(offset, value);
  write16(offset + 2, value >> 16);
}

void formatCard() {
  fileStart = CardBlocks - RawBlocks;
  image.assign(CardBlocks * 512, 0);
}

struct Calibration {
  std::string day, timeH, temperature, crushing;
  double maturity, strength;
};

struct Fixture {
  double a, b, r2, clientMaturity, clientStrength;
  unsigned pairs;
  std::vector<Calibration> rows;
  std::vector<Factor> factors;

  explicit Fixture(std::istream& stream) {
    assert(stream >> a >> b >> r2 >> pairs >> clientMaturity >> clientStrength);
    for (unsigned i = 0; i < pairs; ++i) {
      int day;
      float factor;
      assert(stream >> day >> factor);
      factors.push_back({day * DayScale, factor});
    }
    for (Calibration row; stream >> row.day >> row.timeH >> row.temperature >> row.crushing
                              >> row.maturity >> row.strength; ) rows.push_back(row);
    assert(rows.size() == 41);
  }
};

Ref success(Answer answer) {
  if (answer.error() != Error::Ok) {
    std::cerr << "Unexpected ConMT error " << static_cast<int>(answer.error()) << '\n';
    abort();
  }
  return answer.value();
}

void near(double actual, double expected, double tolerance) {
  if (fabs(actual - expected) > tolerance || !isfinite(actual)) {
    std::cerr << "Expected " << expected << ", got " << actual << ", tolerance " << tolerance << '\n';
    abort();
  }
}

void numericLimits() {
  uint32_t ordinal;
  assert(date("2000-02-29", ordinal));
  assert(!date("2100-02-29", ordinal));
  assert(!date("20x6-11-01", ordinal));
  assert(date("2199-12-31", ordinal));
  uint16_t year;
  uint8_t month, day;
  calendar(ordinal, year, month, day);
  assert(year == 2199 && month == 12 && day == 31);
  uint32_t value;
  assert(clock("23:59:59", value) && value == 86399);
  assert(!clock("23:5x:59", value));
  assert(integer("4294967295", value) && value == UINT32_MAX);
  assert(!integer("4294967296", value));
  assert(labAge(49710269, false, value));
  assert(!labAge(49710270, false, value));
}

void batteryCalibration() {
  BatteryGauge gauge;
  gauge.sample(519);
  assert(gauge.percent() == -1);
  gauge.sample(877);
  assert(gauge.percent() == 0);
  for (uint8_t i = 0; i < 99; ++i) gauge.sample(991);
  assert(gauge.percent() == 0);
  for (uint16_t i = 0; i < 700; ++i) gauge.sample(991);
  assert(gauge.percent() == 100);
  gauge.sample(0);
  assert(gauge.percent() == -1);
  gauge.sample(934);
  assert(gauge.percent() == 50);
}

Stamp setUser(Engine& engine) {
  uint32_t day;
  assert(date("2026-11-01", day));
  const Stamp begin{day, 7 * 3600 + 30 * 60};
  success(engine.clockSet(begin));
  assert(engine.set(Field::Operator, "a|b").error() == Error::Input);
  assert(engine.disk.error() == Error::Ok);
  success(engine.set(Field::Operator, "OP-17"));
  success(engine.set(Field::Project, "Proyek ConMT"));
  assert(engine.saveIdentity().error() == Error::MissingData);
  success(engine.set(Field::Date, "2026-11-01"));
  success(engine.saveIdentity());
  return begin;
}

Ref author(Engine& engine, const Fixture& fixture) {
  assert(engine.row(0, Field::Temperature, "26").error() == Error::NotFound);
  success(engine.draft(0));
  success(engine.set(Field::Name, "Referensi Excel"));
  success(engine.set(Field::Target, "35"));
  success(engine.set(Field::Datum, "-20"));
  success(engine.set(Field::Cement, "380.07"));
  success(engine.set(Field::Water, "190"));
  success(engine.set(Field::RetarderBrand, "R-Test"));
  const Ref empty = engine.disk.root().draft;
  assert(engine.row(1, Field::Temperature, "26").error() == Error::NotFound);
  assert(engine.row(0, Field::Temperature, "abc").error() == Error::Input);
  const auto sensors = live;
  live.valid = 0;
  assert(engine.row(0, Field::Temperature, "", true).error() == Error::Sensor);
  live = sensors;
  assert(engine.disk.root().draft == empty);
  Baseline first;
  LabRow row;
  success(engine.row(0, Field::Temperature, "36.00"));
  assert(engine.baseline(engine.disk.root().draft, first) && first.rows.count == 1);
  assert(engine.disk.at(first.rows, 0, Kind::Row, row) && row.day == 0 && row.age == 0);
  const Ref firstId = row.id;
  assert(firstId && row.temperature == 3600000L && row.fc == Missing);
  success(engine.row(0, Field::Temperature, "36.01"));
  assert(engine.baseline(engine.disk.root().draft, first) && first.rows.count == 1);
  assert(engine.disk.at(first.rows, 0, Kind::Row, row) && row.id == firstId);
  success(engine.addRows(true, true));
  success(engine.addRows(true, true));
  assert(engine.addRows(true, false).error() == Error::Full);
  assert(engine.generate().error() == Error::MissingData);
  for (unsigned i = 13; i < fixture.rows.size(); ++i) success(engine.addRows(false, false));
  for (unsigned i = 0; i < fixture.rows.size(); ++i) {
    const auto& row = fixture.rows[i];
    success(engine.row(i, Field::Temperature, row.temperature.c_str()));
    success(engine.row(i, Field::Fc, row.crushing.c_str()));
  }
  const Ref revision = success(engine.generate());
  Baseline base;
  Model model;
  assert(engine.baseline(revision, base));
  assert(engine.disk.read(base.model, Kind::Model, model));
  assert(base.rows.count == 41);
  assert(model.fit.count == fixture.pairs);
  near(model.fit.a, fixture.a, 0.00015);
  near(model.fit.b, fixture.b, 0.000015);
  near(model.fit.r2, fixture.r2, 0.000015);
  near(model.maxM, fixture.rows.back().maturity, 0.025);
  Cursor factors(model.factors);
  for (const Factor& expected : fixture.factors) {
    Factor actual;
    assert(engine.disk.next(factors, Kind::Factor, actual) && actual.day == expected.day);
    near(actual.value, expected.value, 0.00003);
  }
  assert(!factors.remaining);
  return revision;
}

void rejectsUnknownFactorVersion(Engine& engine, Ref baselineId) {
  Baseline base;
  Model model;
  assert(engine.baseline(baselineId, base));
  assert(engine.disk.read(base.model, Kind::Model, model));
  const size_t offset = (fileStart + 2) * 512 + (model.factors.first - 1) * board::SlotBytes;
  assert(image[offset + 2] == 1 && image[offset + 3] == static_cast<uint8_t>(Kind::Factor));
  constexpr uint8_t crcOffset = 9 + Journal::PayloadBytes;
  image[offset + 2] = 2;
  write32(offset + crcOffset, checksum(image.data() + offset, crcOffset));
  assert(engine.recover());

  Point point{};
  point.day = DayScale;
  point.maturity = 1600;
  Real fc = -1;
  assert(!engine.strength(baselineId, point, fc));
  assert(engine.disk.error() == Error::Version && fc == -1);

  image[offset + 2] = 1;
  write32(offset + crcOffset, checksum(image.data() + offset, crcOffset));
  assert(engine.recover());
}

void measurement(Engine& engine, Ref base, Stamp start, const Fixture& fixture) {
  live = {{3590000, 3600000, 3610000}, 0};
  assert(engine.start(base).error() == Error::Sensor);
  live.valid = 7;
  success(engine.start(base));
  assert(engine.saveResult(engine.disk.root().active).error() == Error::NoInterval);
  Real reviewedFc = 0;
  for (unsigned i = 1; i < fixture.rows.size(); ++i) {
    const Calibration& row = fixture.rows[i];
    Scaled day, temperature;
    assert(number(row.day.c_str(), 3, day));
    assert(number(row.temperature.c_str(), 5, temperature));
    const Stamp at = forward(start, static_cast<uint32_t>(stod(row.timeH) * 3600));
    wall = at;
    const Ref revision = success(engine.checkpoint(day, at, temperature, true, false));
    Session run;
    Point first, last;
    Real fc;
    assert(engine.result(revision, run, first, last, fc));
    assert(run.points.count == i + 1);
    near(last.maturity, row.maturity, 0.025);
    near(fc, row.strength, 0.002);
    const bool final = i + 1 == fixture.rows.size();
    if (i == 5 || final) {
      const Real rawMaturity = last.maturity;
      const double factor = final ? fixture.factors.back().value : fixture.factors.front().value;
      const double expected = (fixture.a + fixture.b * log(round(row.maturity))) * factor;
      assert(engine.result(revision, run, first, last, reviewedFc, true));
      assert(last.maturity == rawMaturity);
      near(reviewedFc, expected, 0.002);
      if (i == 5) assert(fabs(reviewedFc - fc) > 0.01);
    }
  }
  const Ref revision = engine.disk.root().active;
  const Ref saved = success(engine.saveResult(revision));
  assert(success(engine.saveResult(revision)) == saved);
  assert(engine.disk.root().active == 0);
  Ref found;
  Result result;
  assert(engine.historyAt(0, found, result) && found == saved && result.session == revision);
  assert(result.fc == reviewedFc);

  Point client{};
  client.day = 26 * DayScale;
  client.maturity = fixture.clientMaturity;
  Real fc;
  assert(engine.strength(base, client, fc));
  near(fc, fixture.clientStrength, 0.002);
}

uint32_t numericOutput(const std::string& component) {
  const size_t pos = output.rfind(component);
  assert(pos != std::string::npos);
  return std::stoul(output.substr(pos + component.size()));
}

void frame(const std::string& message) {
  output.clear();
  for (const char byte : message + '\n') incoming.push_back(byte);
  while (!incoming.empty()) panel::poll();
}

void wire(const Fixture& fixture) {
  panel::begin();
  frame("CM1|0|0|0|0|PAGE_READY");
  const uint32_t boot = numericOutput("nBoot.val=");
  uint32_t view = numericOutput("nView.val=");
  uint32_t seq = 0;
  auto send = [&](const std::string& verb, uint8_t page, Error expected) {
    frame("CM1|" + std::to_string(boot) + "|" + std::to_string(++seq) + "|" +
          std::to_string(page) + "|" + std::to_string(view) + "|" + verb);
    assert(numericOutput("nAckCode.val=") == static_cast<uint8_t>(expected));
    assert(numericOutput("nAckSeq.val=") == seq);
    if (output.find("nView.val=") != std::string::npos) view = numericOutput("nView.val=");
  };
  auto ready = [&](uint8_t page) {
    frame("CM1|" + std::to_string(boot) + "|" + std::to_string(seq) + "|" +
          std::to_string(page) + "|0|PAGE_READY");
    view = numericOutput("nView.val=");
  };
  send("GET|status", 0, Error::Ok);
  send("NAV|2", 0, Error::Ok);
  assert(output.find("page pMain") != std::string::npos);
  ready(2);
  send("GET|identity", 2, Error::Ok);
  assert(output.find("tData.txt=\"OP-17|Proyek ConMT|2026-11-01\"") != std::string::npos);
  send("NAV|9", 2, Error::Ok); ready(9);
  send("NAV|13", 9, Error::Ok); ready(13);
  send("HISTORY_PICK|99999", 13, Error::NotFound);
  send("GET|historyrow|0", 13, Error::Ok);
  assert(output.find("Referensi Excel") != std::string::npos);
  send("HISTORY_PICK|0", 13, Error::Ok); ready(14);
  send("GET|detail", 14, Error::Ok);
  assert(output.find("OP-17|Proyek ConMT") != std::string::npos);
  send("GET|point|40", 14, Error::Ok);
  assert(output.find("38.7") != std::string::npos);
  frame("CM1|" + std::to_string(boot) + "|400|14|" + std::to_string(view - 1) + "|NAV|13");
  assert(numericOutput("nAckCode.val=") == static_cast<uint8_t>(Error::Stale));
  frame(std::string(192, 'A'));
  assert(output.empty());
  send("GET|status", 14, Error::Ok);

  send("NAV|13", 14, Error::Ok); ready(13);
  send("NAV|9", 13, Error::Ok); ready(9);
  send("NAV|2", 9, Error::Ok); ready(2);
  send("NAV|16", 2, Error::Ok); ready(16);
  send("GET|status", 16, Error::Ok);
  send("NAV|2", 16, Error::Ok); ready(2);
  send("NAV|15", 2, Error::Ok); ready(15);
  send("SETTINGS_SET|brightness|70", 15, Error::Ok);
  assert(output.find("dim=70") != std::string::npos);
  send("SETTINGS_SET|autoSave|0", 15, Error::Ok);
  send("SETTINGS_SAVE", 15, Error::Ok); ready(2);
  send("NAV|1", 2, Error::Ok); ready(1);
  send("USER_SAVE", 1, Error::Ok); ready(2);
  send("NAV|3", 2, Error::Ok); ready(3);
  send("BASE_NEW", 3, Error::Ok); ready(4);
  send("FIELD_SET|name|Baseline CM1", 4, Error::Ok);
  send("NAV|5", 4, Error::Ok); ready(5);
  send("GET|mix", 5, Error::Ok);
  assert(output.find("R-Test") != std::string::npos);
  send("NAV|6", 5, Error::Ok); ready(6);
  send("ROW_SCHEDULE|40", 6, Error::Ok);
  send("ROW_FOCUS|0", 6, Error::Ok);
  live = {{3600000, 3600000, 3600000}, 7};
  send("ROW_SENSOR|0", 6, Error::Ok);
  send("ROW_DELETE|39", 6, Error::Confirm);
  send("GET|status", 6, Error::Ok);
  send("CANCEL|" + std::to_string(view), 6, Error::Ok);
  send("BASE_GENERATE", 6, Error::Ok); ready(7);
  send("GET|scatter|9", 7, Error::Ok);
  assert(output.find("38.7") != std::string::npos);
  send("GET|curve|0", 7, Error::Ok);
  const std::string dataPrefix = "tData.txt=\"";
  const size_t column = output.find(dataPrefix);
  assert(column != std::string::npos);
  near(std::stod(output.substr(column + dataPrefix.size())), exp(-fixture.a / fixture.b), 0.01);
  send("GET|curve|64", 7, Error::Ok);
  assert(output.find("35000|") != std::string::npos);
  send("GET|baseline", 7, Error::Ok);
  const std::string revision = std::to_string(numericOutput("nAckValue.val="));
  send("BASE_SAVE|" + revision, 7, Error::Ok);
  const std::string baseline = std::to_string(numericOutput("nAckValue.val="));
  ready(8);
  send("BASE_OPEN", 8, Error::Ok); ready(6);
  send("NAV|8", 6, Error::Ok); ready(8);
  send("NAV|3", 8, Error::Ok); ready(3);
  send("NAV|2", 3, Error::Ok); ready(2);
  send("NAV|9", 2, Error::Ok); ready(9);
  send("NAV|10", 9, Error::Ok); ready(10);
  send("BASE_PICK|" + baseline, 10, Error::Ok);
  send("MEASURE_START", 10, Error::Confirm);
  send("CONFIRM|" + std::to_string(view), 10, Error::Ok); ready(11);
  tick += 3000;
  wall = forward(wall, 3);
  send("CHECK_ADD", 11, Error::Ok);
  send("RESULT_PREPARE", 11, Error::Ok);
  const std::string run = std::to_string(numericOutput("nAckValue.val="));
  ready(12);
  send("RESULT_SAVE|" + run, 12, Error::Ok);
  const uint32_t saved = numericOutput("nAckValue.val=");
  ready(13);
  send("RETRY|RESULT_SAVE|" + run, 13, Error::Ok);
  assert(numericOutput("nAckValue.val=") == saved);
}

void autoLog(Engine& engine, Ref baseline) {
  const Stamp start = wall;
  live = {{0, 0, 0}, 7};
  success(engine.set(Field::Interval, "5"));
  success(engine.start(baseline));
  const Ref initial = engine.disk.root().active;

  wall = forward(start, 5);
  tick += 5000;
  engine.tick();
  assert(initial != engine.disk.root().active);
  const Ref active = engine.disk.root().active;
  live.valid = 0;
  tick += 5000;
  wall = forward(start, 10);
  engine.tick();
  assert(engine.disk.root().active == active);

  live.valid = 1;
  tick += 5000;
  wall = forward(start, 15);
  engine.tick();
  Session run;
  Point first, last;
  Real fc;
  assert(engine.result(engine.disk.root().active, run, first, last, fc));
  assert(run.points.count == 3 && run.partial == 1 && (last.flags & Gap));
  near(last.maturity, 20.0 * 5 / 3600, 0.0001);
  assert(engine.editPoint(2, Field::ClearGap, "0").error() == Error::Input);
  success(engine.editPoint(2, Field::Temperature, "0"));
  success(engine.editPoint(2, Field::ClearGap, "0"));
  assert(engine.result(engine.disk.root().active, run, first, last, fc));
  assert(!run.partial);
  near(last.maturity, 20.0 * 15 / 3600, 0.0001);
  assert(engine.checkpoint(0, forward(start, 16), 0, true, false).error() == Error::Clock);
}

void faults(Engine& engine, Ref revision) {
  fault = TearBody;
  assert(engine.saveBaseline(revision).error() == Error::Storage);
  assert(engine.recover());
  assert(engine.disk.root().baselines.count == 0);

  fault = TearAnchor;
  assert(engine.saveBaseline(revision).error() == Error::Storage);
  assert(engine.recover());
  assert(engine.disk.root().baselines.count == 0);

  fault = LostCommitAck;
  assert(engine.saveBaseline(revision).error() == Error::Storage);
  assert(engine.recover());
  assert(engine.disk.root().baselines.count == 1);
}
}  // namespace

namespace conmt {
namespace board {
void poll() {}
uint32_t ticks() { return tick; }
const Stamp& now() { return wall; }
bool setClock(const Stamp& stamp) {
  if (!validStamp(stamp)) return false;
  wall = stamp;
  return true;
}
const Sensors& temperatures() { return live; }
uint16_t supplyMv() { return 8500; }
int8_t batteryPercent() { return batteryValue; }
void beep(bool) {}
int receive() {
  if (incoming.empty()) return -1;
  const uint8_t byte = incoming.front();
  incoming.pop_front();
  return byte;
}
void transmit(uint8_t byte) { output.push_back(static_cast<char>(byte)); }
}  // namespace board

namespace card {
uint32_t begin() { return image.size() / 512; }
bool read(uint32_t sector, uint8_t* data) {
  if (sector >= begin()) return false;
  memcpy(data, &image[sector * 512], 512);
  return true;
}
bool write(uint32_t sector, const uint8_t* data) {
  assert(sector >= fileStart && sector < fileStart + LogBlocks);
  const bool anchor = sector < fileStart + 2;
  if ((fault == TearBody && !anchor) || (fault == TearAnchor && anchor)) {
    memcpy(&image[sector * 512], data, 8);
    fault = None;
    return false;
  }
  memcpy(&image[sector * 512], data, 512);
  if (fault == LostCommitAck && anchor) {
    fault = None;
    return false;
  }
  return true;
}
}  // namespace card
}  // namespace conmt

int main() {
  numericLimits();
  batteryCalibration();
  const Fixture data(std::cin);
  near(correction(0.25f), 0.8, 0.00001);
  near(correction(-0.05f), 1, 0.00001);
  near(correction(-0.1f), 1, 0.00001);
  near(correction(-0.3f), 1.2, 0.00001);
  formatCard();
  Engine engine;
  assert(engine.recover());
  const Stamp begin = setUser(engine);
  const Ref revision = author(engine, data);
  faults(engine, revision);
  const Ref saved = success(engine.saveBaseline(revision));
  assert(saved == success(engine.disk.findSave(SaveKind::Baseline, revision)));
  assert(engine.disk.root().baselines.count == 1);
  rejectsUnknownFactorVersion(engine, saved);
  measurement(engine, saved, begin, data);
  autoLog(engine, saved);
  success(engine.deleteBaseline(saved));
  assert(!engine.exists(saved));
  wire(data);
  formatCard();
  assert(engine.recover());
  success(engine.set(Field::Operator, "RAW-CARD"));
  assert(engine.recover());
  std::cout << "41 rows, 10 FKZ values, rounded result, FKZ version errors, AutoSave, "
               "3 SD interruption modes, raw card and CM1 passed\n";
  return 0;
}
