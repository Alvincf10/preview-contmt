#pragma once
#include "../storage/Repository.h"
#include "../core/Calendar.h"
namespace conmt {
enum class Page : uint8_t { Init, User, Main, Base, NewB, Mat, Matu, BaseR, SaveB, Kuat, SelB, RT, Str, Hist, HistD, Set, Dev };
enum class SessionState : uint8_t { Idle, Active, Preview, Completed, Suspended };
struct Result {
    Prediction prediction;
    Real rawM, initialTemp, lastTemp;
    uint64_t endMs;
    Result() : rawM(0),initialTemp(0),lastTemp(0),endMs(0) {}
};
struct Settings { uint32_t intervalSeconds; uint8_t brightness; bool sound,autoSave; };
class Controller {
    Repository& repo_; ClockPort& clock_; SensorPort& sensors_; DevicePort& devices_;
    Page page_;
    uint32_t draft_,selected_,session_,history_,view_,cursor_,boot_,focusedRow_;
    bool savedEntry_,mounted_,sampleKnown_,gapLatched_,inGap_,loading_;
    uint32_t lastMono_,lastSaveMono_,lastFrameMono_;
    uint64_t lastWall_;
    Real lastTemp_,liveM_,liveCompensation_;
    Settings settings_;
    Status status_,health_;
    Status load();
    Status tickImpl();
    Status markGap(uint64_t start,uint64_t end);
    Status finish(Status st);
    Status begin(uint64_t op);
    Status mutateField(Kind k,uint32_t o,Field f,const char* value,uint64_t op);
    Status setting(const char* key,const char* value,uint64_t op);
    Status validateDraft();
    Status earlySlot(uint32_t excluding,Real& hours);
    Status focusRow(uint32_t id);
    Status cloneDraft(uint32_t from,uint64_t op);
    Status persistSample(const SensorFrame& frame,const Average& avg,const Time& now);
    bool validNavigation(Page p) const;
public:
    Controller(Repository& r,ClockPort& c,SensorPort& s,DevicePort& d);
    Status boot();
    Status newConnection();
    Status tick();
    Status dispatch(const char* verb,const char* a="",const char* b="",const char* c="",uint64_t operation=0);
    Status newBaseline(uint64_t op=0);
    Status setField(const char* key,const char* value,uint64_t op=0);
    Status addRow(bool early,uint64_t op=0);
    Status fillEarly(uint64_t op=0);
    Status editRow(uint32_t id,const char* field,const char* value,uint64_t op=0);
    Status deleteRow(uint32_t id,bool confirmed,uint64_t op=0);
    Status captureRow(uint32_t id,uint64_t op=0);
    Status generate(uint64_t op=0);
    Status saveBaseline(uint64_t op=0);
    Status openBaseline(uint32_t id,uint64_t op=0);
    Status deleteBaseline(uint32_t id,bool confirmed,uint64_t op=0);
    Status start(bool confirmed=false,uint64_t op=0);
    Status addCheckpoint(Real day,uint64_t op=0);
    Status editCheckpoint(uint32_t id,const char* field,const char* value,uint64_t op=0);
    Status prepareResult(uint64_t op=0);
    Status saveResult(uint64_t op=0);
    Status readResult(Kind kind,uint32_t id,Result& out);
    Status checkpointResult(Kind kind,uint32_t object,uint32_t pointId,Result& out);
    Status rowAt(uint32_t slot,Row& out);
    Status pointAt(uint32_t slot,Point& out);
    Status baselineAt(uint32_t slot,uint32_t& id);
    Status historyAt(uint32_t slot,uint32_t& id);
    Status getAverage(Average& out,SensorFrame* frame=nullptr);
    Status state(SessionState& out);
    Status select(uint32_t id);
    Page page() const { return page_; }
    uint32_t view() const { return view_; }
    uint32_t bootToken() const { return boot_; }
    uint32_t draftId() const { return draft_; }
    uint32_t selectedId() const { return selected_; }
    uint32_t sessionId() const { return session_; }
    uint32_t historyId() const { return history_; }
    uint32_t cursor() const { return cursor_; }
    uint32_t focusedRow() const { return focusedRow_; }
    Real liveMaturity() const { return liveM_; }
    Status status() const { return health_==Status::Ok?status_:health_; }
    const Settings& settings() const { return settings_; }
    Repository& repository() { return repo_; }
    ClockPort& clock() { return clock_; }
    DevicePort& devices() { return devices_; }
};
}
