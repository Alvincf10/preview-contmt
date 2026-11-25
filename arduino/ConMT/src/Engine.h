#pragma once

#include "Journal.h"

namespace conmt {

enum class Field : uint8_t {
  Operator, Project, Date, Name, Target, Datum, PourDate, PourClock,
  Cement, Water, Coarse, Fine, Retarder, Accelerator, FlyAsh, RetarderBrand,
  AcceleratorBrand, FlyAshBrand, Day, Age, Clock, Temperature, Fc,
  Interval, Hour, Minute, Second, Brightness, Sound, AutoSave, Timestamp, ClearGap
};

class Engine {
 public:
  struct WorkingRecords {
    Baseline baseline;
    Session session;
    Point point;
    Point previous;
  };

  Journal disk;
  Settings config = DefaultSettings;

  // Borrowed record storage for the current command or read request.
  WorkingRecords& workingRecords() { return work_; }

  bool recover();
  void tick(bool autoEnabled = true);
  Answer set(Field field, const char* value);
  Answer saveIdentity();
  Answer draft(Ref saved);
  Answer row(uint16_t index, Field field, const char* value, bool sensor = false);
  Answer addRows(bool early, bool fill);
  Answer deleteRow(uint16_t index);
  Answer generate();
  Answer saveBaseline(Ref revision);
  Answer deleteBaseline(Ref id);
  Answer start(Ref baseline);
  Answer checkpoint(Scaled day, const Stamp& time, Scaled temperature, bool manual, bool automatic);
  Answer editPoint(uint16_t index, Field field, const char* value);
  Answer clockSet(const Stamp& stamp);
  Answer saveResult(Ref revision);

  bool identity(Ref id, Identity& result);
  bool baseline(Ref id, Baseline& result);
  bool material(Ref id, Mix& result);
  bool exists(Ref id);
  bool strength(Ref baselineId, const Point& point, Real& fc, bool roundMaturity = false);
  bool strength(const Baseline& baseline, const Point& point, Real& fc, bool roundMaturity = false);
  bool result(Ref sessionId, Session& session, Point& first, Point& last, Real& fc,
              bool roundMaturity = false);
  bool historyAt(uint16_t index, Ref& id, Result& result);

 private:
  uint32_t lastAuto_ = 0;
  bool gap_ = false;

  // A command runs to completion before the next one starts. Keep the
  // largest working records away from the interrupt stack.
  WorkingRecords work_;

  Answer done(Ref id = 0);
  Answer stopped(Error reason = Error::Ok);
  Answer setIdentity(Field field, const char* value);
  Answer setBaseline(Field field, const char* value);
  Answer setSettings(Field field, const char* value);
  Answer publish(Baseline& baseline);
  bool rewriteRows(Baseline& baseline, const LabRow* insertion, Ref remove, uint16_t fill);
  Answer updateRoster(Ref id, Ref savedFrom = 0);
  Answer storePoint(Session& session, Point& point, uint16_t replace);
  bool integrate(const Point& previous, Point& next, int8_t datum);
};

}  // namespace conmt
