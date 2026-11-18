#pragma once
#include "../storage/Repository.h"
#include "../core/Calendar.h"
#include "../core/Command.h"
#include "TransactionOps.h"
#include "FieldRules.h"
#include "Settings.h"
namespace conmt {
enum class Page : uint8_t { Init, User, Main, Base, NewB, Mat, Matu, BaseR, SaveB, Kuat, SelB, RT, Str, Hist, HistD, Set, Dev };
enum class SessionState : uint8_t { Idle, Active, Preview, Completed, Suspended };
class Controller {
    friend class Transport;
    Repository& repo_; ClockPort& clock_; SensorPort& sensors_; DevicePort& devices_;
    Page page_;
    uint32_t draft_,selected_,session_,history_,view_,cursor_,boot_,focusedRow_;
    bool savedEntry_,mounted_,sampleKnown_,gapLatched_,inGap_,loading_,replayLive_;
    uint32_t lastMono_,lastSaveMono_,lastFrameMono_;
    uint64_t lastWall_;
    Real lastTemp_,liveM_,liveCompensation_;
    Settings settings_;
    Status status_,health_;
    Status load();
    Status dispatch(Command command,const char* const* args,const uint64_t& operation,Status admission,bool reportLookupError);
    Status tickImpl();
    Status markGap(uint64_t start,uint64_t end,ClockCause cause=ClockCause::None);
    Status finish(Status st);
    Status begin(const uint64_t& op);
    Status transact(const TxStep* steps,uint8_t count,const Entity& source,const Entity& destination,const void* data,const uint64_t& op);
    Status mutateField(const FieldRule& rule,const char* value,const uint64_t& op);
    Status setting(const char* key,const char* value,const uint64_t& op);
    Status validateDraftHeader(Real& datum);
    Status earlySlots(uint32_t max,uint32_t excluding,uint8_t* occupied);
    Status earlySlot(uint32_t max,uint32_t excluding,Real& hours);
    Status focusRow(uint32_t id);
    Status storeDraftRow(const Row& row,Field input,const char* text,bool added,const uint64_t& op);
    Status storePreview(const Result& result,const uint64_t& operation) __attribute__((noinline));
    Status calculateCheckpointResult(Kind kind,uint32_t object,uint32_t pointId,Result& result,bool roundMaturity);
    Status saveIdentity() __attribute__((noinline));
    Status reconcileGap(const char* confirmed,const char* reason,const uint64_t& operation) __attribute__((noinline));
    Status cloneDraft(uint32_t from,const uint64_t& op);
    Status persistSample(const SensorFrame& frame,const Average& avg,const Time& now);
    Status reanchorLive(const SensorFrame& frame,const Average& avg,const Time& now) __attribute__((noinline));
    bool validNavigation(Page p) const;
public:
    Controller(Repository& r,ClockPort& c,SensorPort& s,DevicePort& d);
    Status boot();
    Status newConnection();
    Status tick();
    Status dispatch(const char* verb,const char* a="",const char* b="",const char* c="",const uint64_t& operation=0);
    Status newBaseline(const uint64_t& op=0);
    Status setField(const char* key,const char* value,const uint64_t& op=0);
    Status addRow(bool early,const uint64_t& op=0);
    Status fillEarly(const uint64_t& op=0);
    Status editRow(uint32_t id,const char* field,const char* value,const uint64_t& op=0);
    Status deleteRow(uint32_t id,bool confirmed,const uint64_t& op=0);
    Status captureRow(uint32_t id,const uint64_t& op=0);
    Status generate(const uint64_t& op=0);
    Status saveBaseline(const uint64_t& op=0);
    Status openBaseline(uint32_t id,const uint64_t& op=0);
    Status deleteBaseline(uint32_t id,bool confirmed,const uint64_t& op=0);
    Status start(bool confirmed=false,const uint64_t& op=0);
    Status addCheckpoint(Real day,const uint64_t& op=0);
    Status editCheckpoint(uint32_t id,const char* field,const char* value,const uint64_t& op=0);
    Status prepareResult(const uint64_t& op=0);
    Status saveResult(const uint64_t& op=0);
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
