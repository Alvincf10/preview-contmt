#include "../core/Flash.h"
#include "Controller.h"
#include "../core/Command.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
namespace conmt {
#define TRY(expr) do { Status st_=(expr); if(st_!=Status::Ok) return st_; } while(0)
Controller::Controller(Repository& r,ClockPort& c,SensorPort& s,DevicePort& d) : repo_(r),clock_(c),sensors_(s),devices_(d),page_(Page::Init),draft_(0),selected_(0),session_(0),history_(0),view_(1),cursor_(0),boot_(0),focusedRow_(0),savedEntry_(false),mounted_(false),sampleKnown_(false),gapLatched_(false),inGap_(false),loading_(false),replayLive_(false),lastMono_(0),lastSaveMono_(0),lastFrameMono_(0),lastWall_(0),lastTemp_(0),liveM_(0),liveCompensation_(0),settings_{300,80,true,false},status_(Status::Ok),health_(Status::Ok) {}
Status Controller::finish(Status s) {
    if(s==Status::Ok) s=repo_.journal().commit(); else repo_.journal().abort();
    if(s==Status::Ok) ++view_;
    return s;
}
Status Controller::begin(const uint64_t& op) {
    if(!mounted_&&!loading_) return health_==Status::Ok?Status::Absent:health_;
    return repo_.journal().begin(op);
}
Status Controller::transact(const TxStep* steps,uint8_t count,const Entity& source,const Entity& destination,const void* data,const uint64_t& op) {
    TRY(begin(op)); return finish(applyTransaction(repo_,clock_,steps,count,source,destination,data));
}
Status Controller::newConnection() {
    if(boot_==UINT32_MAX) return Status::Capacity;
    TRY(begin(0)); TRY(finish(repo_.putInteger(Key(Kind::System,0,Field::State),boot_+1))); ++boot_; return Status::Ok;
}
Status Controller::boot() {
    mounted_=false; loading_=true; sampleKnown_=false; gapLatched_=false; inGap_=false; replayLive_=false;
    liveM_=liveCompensation_=0; selected_=session_=draft_=0;
    page_=Page::User;
    Status st=load(); loading_=false;
    if(st!=Status::Ok) repo_.journal().abort();
    mounted_=st==Status::Ok; status_=health_=st;
    return st;
}
Status Controller::load() {
    Status s=repo_.journal().mount(); status_=s;
    if(s!=Status::Ok) { page_=Page::User; return s; }

    TRY(repo_.journal().maxObject(Kind::Draft,draft_));
    TRY(repo_.journal().maxObject(Kind::Session,session_));
    uint32_t token=0; s=repo_.integer(Key(Kind::System,0,Field::State),token);
    if(s!=Status::Ok && s!=Status::Missing) return s;
    if(token<boot_) token=boot_;
    if(token==UINT32_MAX) return Status::Capacity;
    boot_=token+1; TRY(begin(0)); TRY(repo_.putInteger(Key(Kind::System,0,Field::State),boot_)); TRY(finish(Status::Ok));
    uint32_t n=0;
    s=repo_.integer(Key(Kind::Settings,0,Field::Interval),n); if(s==Status::Ok) settings_.intervalSeconds=n; else if(s!=Status::Missing) return s;
    s=repo_.integer(Key(Kind::Settings,0,Field::Brightness),n); if(s==Status::Ok) { if(n>100||n%5) return Status::Corrupt; settings_.brightness=uint8_t(n); } else if(s!=Status::Missing) return s;
    s=repo_.integer(Key(Kind::Settings,0,Field::Sound),n); if(s==Status::Ok) { if(n>1) return Status::Corrupt; settings_.sound=n!=0; } else if(s!=Status::Missing) return s;
    s=repo_.integer(Key(Kind::Settings,0,Field::AutoSave),n); if(s==Status::Ok) { if(n>1) return Status::Corrupt; settings_.autoSave=n!=0; } else if(s!=Status::Missing) return s;
    if(settings_.intervalSeconds>86399 || settings_.brightness>100 || settings_.brightness%5) return Status::Corrupt;
    devices_.brightness(settings_.brightness); devices_.sound(settings_.sound);
    if(session_) {
        Status saved=repo_.number(Key(Kind::Session,session_,Field::Result,1),liveM_);
        if(saved!=Status::Ok && saved!=Status::Missing) return saved;
        SessionState ss; TRY(state(ss));
        if(ss!=SessionState::Completed) {
            uint64_t start=0; uint8_t frame[53]; uint16_t frameSize=53;
            Status frameStatus=repo_.journal().get(Key(Kind::Session,session_,Field::Sensors),frame,frameSize);
            if(frameStatus==Status::Ok&&frameSize==53) start=get64(frame);
            else if(frameStatus==Status::Missing) TRY(repo_.time(Key(Kind::Session,session_,Field::Start),start));
            else return frameStatus==Status::Ok?Status::Corrupt:frameStatus;
            uint64_t sessionStart; TRY(repo_.time(Key(Kind::Session,session_,Field::Start),sessionStart)); if(start<sessionStart) start=sessionStart;
            TRY(markGap(start,clock_.now().valid?clock_.now().wallMs:start,ClockCause::Restart));
            TRY(begin(0)); TRY(finish(repo_.putInteger(Key(Kind::Session,session_,Field::State),uint32_t(SessionState::Suspended))));
            gapLatched_=true; inGap_=true;
        }
    }
    uint32_t selected=0;
    s=repo_.integer(Key(Kind::System,0,Field::BaselineRef),selected);
    if(s!=Status::Ok && s!=Status::Missing) return s;
    if(selected) { uint32_t exists=0; s=repo_.integer(Key(Kind::Baseline,selected,Field::Exists),exists); if(s!=Status::Ok&&s!=Status::Missing) return s; if(s==Status::Ok&&exists) selected_=selected; }
    if(!selected_) { s=repo_.list(Kind::Baseline,0,selected_); if(s!=Status::Ok&&s!=Status::Missing) return s; }
    page_=Page::User; return Status::Ok;
}
Status Controller::getAverage(Average& avg,SensorFrame* frame) {
    avg={0,0,0}; if(frame) *frame=SensorFrame();
    SensorFrame f; TRY(sensors_.latest(f));
    Status s=average(f,clock_.now().monoMs,5000,avg);
    if(frame) *frame=f;
    return s;
}
Status Controller::state(SessionState& out) {
    Record record(repo_,Kind::Session,session_);
    if(!session_) { out=SessionState::Idle; return Status::Ok; }
    uint32_t value=0; TRY(record.integer(Field::State,value));
    if(value>uint32_t(SessionState::Suspended)) return Status::Corrupt;
    out=SessionState(value); return Status::Ok;
}
Status Controller::persistSample(const SensorFrame& f,const Average& a,const Time& t) {
    TRY(begin(0)); Status s=repo_.putSensors(Kind::Session,session_,f,a,t);
    if(s==Status::Ok) s=repo_.putNumber(Key(Kind::Session,session_,Field::Result,1),liveM_);
    s=finish(s); if(s==Status::Ok) lastSaveMono_=t.monoMs; return s;
}
Status Controller::markGap(uint64_t start,uint64_t end,ClockCause cause) {
    Record record(repo_,Kind::Session,session_);
    uint8_t event[21]; event[0]=uint8_t(cause); put64(event+1,start); put64(event+9,end); put32(event+17,clock_.now().monoMs);
    if(start>end) { uint64_t swap=start; start=end; end=swap; }
    uint32_t existing=0; Status st=record.integer(Field::Gap,existing);
    if(st!=Status::Ok && st!=Status::Missing) return st;
    if(existing) { uint64_t oldStart,oldEnd; TRY(record.time(Field::GapStart,oldStart)); TRY(record.time(Field::GapEnd,oldEnd)); if(oldStart<start) start=oldStart; if(oldEnd>end) end=oldEnd; }
    TRY(begin(0)); Status s=record.putInteger(Field::Gap,1);
    if(s==Status::Ok) s=record.putTime(Field::GapStart,start);
    if(s==Status::Ok) s=record.putTime(Field::GapEnd,end);
    if(s==Status::Ok&&cause!=ClockCause::None) s=record.put(Field::ClockAdjustment,event,sizeof(event));
    TRY(finish(s)); gapLatched_=true; return Status::Ok;
}
Status Controller::tick() {
    Status st=tickImpl(); health_=st;
    if(st==Status::Ok&&gapLatched_) health_=Status::Gap;
    return st;
}
Status Controller::tickImpl() {
    Record record(repo_,Kind::Session,session_);
    Time t=clock_.now(); sensors_.poll(t.monoMs); devices_.poll(t.monoMs);
    if(!mounted_ || !session_) return Status::Ok;
    SessionState ss; TRY(state(ss));
    if(ss!=SessionState::Active && ss!=SessionState::Preview) return Status::Ok;
    Average avg; SensorFrame f; Status s=getAverage(avg,&f);
    bool gap=s!=Status::Ok || !t.valid;
    ClockCause cause=!t.valid?ClockCause::Invalid:ClockCause::Sensor;
    if(replayLive_&&!gap) return reanchorLive(f,avg,t);
    if(sampleKnown_) {
        uint32_t dt=t.monoMs-lastMono_;
        if(dt>5000) { gap=true; if(t.valid&&s==Status::Ok) cause=ClockCause::SampleDelay; }
        if(t.valid) {
            if(t.wallMs<lastWall_ || uint64_t(dt)>t.wallMs-lastWall_+2000) { gap=true; cause=ClockCause::Backward; }
            else if(t.wallMs-lastWall_>uint64_t(dt)+2000) { gap=true; cause=ClockCause::Forward; }
        }
    }
    if(gap) {
        sampleKnown_=false;
        if(!inGap_) { TRY(markGap(lastWall_,t.valid?t.wallMs:lastWall_,cause)); inGap_=true; }
        return status_=t.valid?(s==Status::Ok?Status::NoClock:s):Status::NoClock;
    }
    if(inGap_) { TRY(markGap(lastWall_,t.wallMs)); inGap_=false; }
    if(sampleKnown_ && f.sampledMonoMs==lastFrameMono_) return Status::Ok;
    uint64_t sampledWall=t.wallMs-uint32_t(t.monoMs-f.sampledMonoMs);
    if(sampleKnown_ && sampledWall<lastWall_) return Status::NoClock;
    if(sampleKnown_) {
        Real datum; TRY(record.number(Field::Datum,datum));
        Real increment=interval(lastTemp_,avg.operational,datum,Real(sampledWall-lastWall_)/3600000)-liveCompensation_;
        Real sum=liveM_+increment; liveCompensation_=(sum-liveM_)-increment;
        liveM_=positive(sum); if(sum<0) liveCompensation_=0;
    }
    lastTemp_=avg.operational; lastFrameMono_=f.sampledMonoMs; lastMono_=f.sampledMonoMs; lastWall_=sampledWall; sampleKnown_=true;
    if(settings_.autoSave && settings_.intervalSeconds && uint32_t(t.monoMs-lastSaveMono_)>=settings_.intervalSeconds*1000UL) return persistSample(f,avg,t);
    return Status::Ok;
}
Status Controller::reanchorLive(const SensorFrame& frame,const Average& avg,const Time& now) {
    Real datum,maturity; Point last;
    TRY(repo_.number(Key(Kind::Session,session_,Field::Datum),datum));
    TRY(replayPoints(repo_,Kind::Session,session_,datum,maturity,last));
    uint32_t age=now.monoMs-frame.sampledMonoMs; if(now.wallMs<age) return Status::NoClock;
    uint64_t sampled=now.wallMs-age; if(sampled<last.atMs) return Status::NoClock;
    Real rebased=positive(maturity+interval(last.temp,avg.operational,datum,Real(sampled-last.atMs)/3600000));
    if(!finite(rebased)) return Status::Invalid;
    liveM_=rebased; liveCompensation_=0; lastTemp_=avg.operational; lastWall_=sampled;
    lastMono_=lastFrameMono_=frame.sampledMonoMs; sampleKnown_=true; replayLive_=false; return Status::Ok;
}
Status Controller::mutateField(Kind k,uint32_t o,Field f,const char* value,const uint64_t& op) {
    Record record(repo_,k,o);
    Real v=0; uint64_t at=0; Status s;
    bool text=f==Field::Name||f==Field::Operator||f==Field::Project||f==Field::Date||f==Field::RetarderBrand||f==Field::AcceleratorBrand||f==Field::FlyAshBrand;
    if(f==Field::Date) TRY(parseDate(value,at));
    if(text && !safeText(value,(f==Field::Operator||f==Field::RetarderBrand||f==Field::AcceleratorBrand||f==Field::FlyAshBrand)?33:65)) return Status::Invalid;
    if(!text) {
        TRY(parseReal(value,v));
        if(f==Field::Datum) { if(v!=-20&&v!=-10&&v!=0&&v!=10) return Status::Invalid; }
        else if(v<0 || (f==Field::Target && v==0)) return Status::Invalid;
    }
    TRY(begin(op));
    s=text?record.putText(f,value,(f==Field::Operator||f==Field::RetarderBrand||f==Field::AcceleratorBrand||f==Field::FlyAshBrand)?33:65):record.putNumber(f,v);
    if(s==Status::Ok && k==Kind::Draft) s=record.erase(Field::Model);
    return finish(s);
}
Status Controller::setField(const char* key,const char* value,const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    if(CM_EQ(key,"operator")) return mutateField(Kind::User,0,Field::Operator,value,op);
    if(CM_EQ(key,"project")) return mutateField(Kind::User,0,Field::Project,value,op);
    if(CM_EQ(key,"date")) return mutateField(Kind::User,0,Field::Date,value,op);
    if(!draft_) return Status::Missing;
    if(CM_EQ(key,"pourDate")||CM_EQ(key,"pourClock")) {
        uint64_t at=0; TRY(record.time(Field::Pour,at));
        if(CM_EQ(key,"pourDate")) { uint64_t day; TRY(parseDate(value,day)); at=day+at%86400000ULL; }
        else { uint32_t sec; TRY(parseClock(value,sec)); at=at/86400000ULL*86400000ULL+uint64_t(sec)*1000; }
        TRY(begin(op)); return finish(record.putTime(Field::Pour,at));
    }
    Field field;
#define F(name,f) if(CM_EQ(key,name)) field=Field::f; else
    F("name",Name) F("target",Target) F("datum",Datum) F("cement",Cement) F("water",Water)
    F("coarse",Coarse) F("fine",Fine) F("retarderPct",RetarderPct) F("retarderBrand",RetarderBrand)
    F("acceleratorPct",AcceleratorPct) F("acceleratorBrand",AcceleratorBrand) F("flyAshPct",FlyAshPct) F("flyAshBrand",FlyAshBrand)
    return Status::Invalid;
#undef F
    return mutateField(Kind::Draft,draft_,field,value,op);
}
Status Controller::newBaseline(const uint64_t& op) {
    if(!mounted_) return Status::Absent;
    Time now=clock_.now(); if(!now.valid) return Status::NoClock;
    if(!draft_) {
        uint32_t max; TRY(repo_.journal().maxObject(Kind::Draft,max)); if(max==UINT32_MAX) return Status::Capacity;
        draft_=max+1;
        TRY(begin(op));
        Status s=repo_.putInteger(Key(Kind::Draft,draft_,Field::Exists),1);
        if(s==Status::Ok) s=repo_.putNumber(Key(Kind::Draft,draft_,Field::Datum),-20);
        if(s==Status::Ok) s=repo_.putInteger(Key(Kind::Draft,draft_,Field::MaxRow),3);
        for(uint32_t i=1;i<=3 && s==Status::Ok;++i) { Row r; r.id=i; r.revision=1; r.timeH=Real(i-1)*Real(.5); s=repo_.putRow(Kind::Draft,draft_,r); }
        if(s==Status::Ok) s=repo_.putTime(Key(Kind::Draft,draft_,Field::Pour),now.wallMs/60000*60000);
        s=finish(s); if(s!=Status::Ok) { draft_=0; return s; }
    } else {
        TRY(begin(op)); TRY(finish(repo_.putTime(Key(Kind::Draft,draft_,Field::Pour),now.wallMs/60000*60000)));
    }
    savedEntry_=false; page_=Page::NewB; cursor_=0; return Status::Ok;
}
static Real snapEarly(Real hours) {
    Real lower=floor(hours*2)/2;
    Real value=lower+(hours-lower>Real(.25)?Real(.5):0);
    return value<0?0:(value>Real(23.5)?Real(23.5):value);
}
Status Controller::earlySlot(uint32_t excluding,Real& hours) {
    Record record(repo_,Kind::Draft,draft_);
    uint32_t max; TRY(record.integer(Field::MaxRow,max));
    for(uint8_t slot=0;slot<48;++slot) {
        bool used=false;
        for(uint32_t id=1;id<=max;++id) {
            if(id==excluding) continue;
            Row row; Status st=repo_.row(Kind::Draft,draft_,id,row);
            if(st==Status::Missing) continue;
            if(st!=Status::Ok) return st;
            if(row.day==0&&snapEarly(row.timeH)==Real(slot)/2) { used=true; break; }
        }
        if(!used) { hours=Real(slot)/2; return Status::Ok; }
    }
    return Status::Capacity;
}
Status Controller::focusRow(uint32_t id) {
    StoredRows rows(repo_,Kind::Draft,draft_,true); Row row; uint32_t index=0; Status st;
    while((st=rows.next(row))==Status::Ok) {
        if(row.id==id) { focusedRow_=id; cursor_=index/6*6; return Status::Ok; }
        ++index;
    }
    return st;
}
Status Controller::addRow(bool early,const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    uint32_t max; TRY(record.integer(Field::MaxRow,max));
    if(max==UINT32_MAX) return Status::Capacity;
    Real day=early?0:1, hours=0; bool available=false;
    for(uint32_t candidate=0;candidate<(early?48UL:max+2);++candidate) {
        if(!early) day=Real(candidate+1);
        hours=early?Real(candidate)/2:day*24; bool used=false;
        for(uint32_t id=1;id<=max;++id) {
            Row r; Status st=repo_.row(Kind::Draft,draft_,id,r); if(st==Status::Missing) continue; if(st!=Status::Ok) return st;
            if(early?(r.day==0&&snapEarly(r.timeH)==hours):(r.day==day)) { used=true; break; }
        }
        if(!used) { available=true; break; }
    }
    if(!available) return Status::Capacity;
    Row r; r.id=max+1; r.revision=1; r.day=day; r.timeH=hours;
    TRY(begin(op)); Status s=repo_.putRow(Kind::Draft,draft_,r);
    if(s==Status::Ok) s=record.putInteger(Field::MaxRow,r.id);
    if(s==Status::Ok) s=record.erase(Field::Model);
    TRY(finish(s)); return focusRow(r.id);
}
Status Controller::fillEarly(const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    uint32_t max; TRY(record.integer(Field::MaxRow,max));
    TRY(begin(op)); Status s=Status::Ok;
    uint32_t next=max,firstNew=0;
    for(uint8_t slot=0;slot<=12 && s==Status::Ok;++slot) {
        bool used=false;
        for(uint32_t i=1;i<=max;++i) { Row r; s=repo_.row(Kind::Draft,draft_,i,r); if(s==Status::Missing) { s=Status::Ok; continue; } if(s!=Status::Ok) break; if(r.day==0&&snapEarly(r.timeH)==Real(slot)/2) used=true; }
        if(s!=Status::Ok) break;
        if(!used) { if(next==UINT32_MAX) { s=Status::Capacity; break; } Row r; r.id=++next; r.revision=1; r.timeH=Real(slot)/2; s=repo_.putRow(Kind::Draft,draft_,r); if(!firstNew) firstNew=r.id; }
    }
    if(s==Status::Ok) s=record.putInteger(Field::MaxRow,next);
    if(s==Status::Ok) s=record.erase(Field::Model);
    TRY(finish(s)); return firstNew?focusRow(firstNew):Status::Ok;
}
Status Controller::editRow(uint32_t id,const char* field,const char* value,const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    Row r; TRY(repo_.row(Kind::Draft,draft_,id,r));
    Real v=0;
    Field input=CM_EQ(field,"temp")?Field::TempInput:(CM_EQ(field,"fc")?Field::FcInput:(CM_EQ(field,"day")?Field::DayInput:Field::Exists));
    if(input!=Field::Exists&&!safeText(value,65)) return Status::Invalid;
    if(CM_EQ(field,"clock")) {
        uint32_t sec; uint64_t pour; TRY(parseClock(value,sec)); TRY(record.time(Field::Pour,pour));
        TRY(clockToHours(uint32_t(pour/1000%86400),sec,r.day,r.timeH));
    } else if((CM_EQ(field,"temp")||CM_EQ(field,"fc")) && !*value) {
        if(CM_EQ(field,"temp")) r.hasTemp=false; else r.hasFc=false;
    } else {
        TRY(parseReal(value,v));
        if(CM_EQ(field,"day")) {
            if(v<0) return Status::Invalid;
            if(v==0) { if(r.day==0) r.timeH=snapEarly(r.timeH); else TRY(earlySlot(r.id,r.timeH)); }
            else r.timeH=v*24;
            r.day=v;
        }
        else if(CM_EQ(field,"timeH")) { if(v<0) return Status::Invalid; r.timeH=v; }
        else if(CM_EQ(field,"temp")) { r.temp=v; r.hasTemp=true; }
        else if(CM_EQ(field,"fc")) { if(v<0) return Status::Invalid; r.fc=v; r.hasFc=true; }
        else return Status::Invalid;
    }
    if(r.day!=0) {
        uint32_t max; TRY(record.integer(Field::MaxRow,max));
        for(uint32_t i=1;i<=max;++i) { if(i==id) continue; Row other; Status s=repo_.row(Kind::Draft,draft_,i,other); if(s==Status::Missing) continue; if(s!=Status::Ok) return s; if(other.day==r.day) return Status::Conflict; }
    }
    if(r.revision==UINT32_MAX) return Status::Capacity;
    ++r.revision; TRY(begin(op)); Status s=repo_.putRow(Kind::Draft,draft_,r);
    if(s==Status::Ok&&input!=Field::Exists) s=repo_.putText(Key(Kind::Draft,draft_,input,r.id),value,65);
    if(s==Status::Ok) s=record.erase(Field::Model);
    return finish(s);
}
Status Controller::deleteRow(uint32_t id,bool confirmed,const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    if(!confirmed) return Status::ConfirmRequired;
    uint32_t count=0; StoredRows source(repo_,Kind::Draft,draft_); Row r; Status s;
    while((s=source.next(r))==Status::Ok) ++count;
    if(s!=Status::Missing) return s;
    if(count<=3) return Status::Invalid;
    TRY(repo_.row(Kind::Draft,draft_,id,r));
    TRY(begin(op)); s=repo_.journal().erase(Key(Kind::Draft,draft_,Field::Row,id));
    if(s==Status::Ok) s=record.erase(Field::Model);
    return finish(s);
}
Status Controller::captureRow(uint32_t id,const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    Row r; TRY(repo_.row(Kind::Draft,draft_,id,r)); if(r.revision==UINT32_MAX) return Status::Capacity; Average a; TRY(getAverage(a));
    r.temp=a.operational; r.hasTemp=true; ++r.revision;
    char reading[28]; formatReal(reading,sizeof(reading),r.temp,1);
    TRY(begin(op)); Status s=repo_.putRow(Kind::Draft,draft_,r);
    if(s==Status::Ok) s=repo_.putText(Key(Kind::Draft,draft_,Field::TempInput,r.id),reading,65);
    if(s==Status::Ok) s=record.erase(Field::Model);
    return finish(s);
}
Status Controller::validateDraft() {
    Record record(repo_,Kind::Draft,draft_);
    char name[65]; TRY(record.text(Field::Name,name,65)); if(!*name) return Status::Invalid;
    Real target,datum; TRY(record.number(Field::Target,target)); if(!(target>0)) return Status::Invalid;
    TRY(record.number(Field::Datum,datum));
    if(datum!=-20&&datum!=-10&&datum!=0&&datum!=10) return Status::Invalid;
    StoredRows rows(repo_,Kind::Draft,draft_); Row r; uint32_t count=0; Real prevDay=0; Status s;
    while((s=rows.next(r))==Status::Ok) { if(!r.hasTemp || (count&&r.day<prevDay)) return Status::Invalid; prevDay=r.day; ++count; }
    if(s!=Status::Missing) return s;
    return count>=3?Status::Ok:Status::Invalid;
}
Status Controller::generate(const uint64_t& op) {
    Record record(repo_,Kind::Draft,draft_);
    TRY(validateDraft()); Real datum; TRY(record.number(Field::Datum,datum));
    StoredRows rows(repo_,Kind::Draft,draft_); Fit fit; TRY(fitRows(rows,datum,fit));
    TRY(begin(op)); TRY(finish(repo_.putModel(Kind::Draft,draft_,fit))); page_=Page::BaseR; return Status::Ok;
}
Status Controller::saveBaseline(const uint64_t& op) {
    TRY(validateDraft()); Fit f; TRY(repo_.model(Kind::Draft,draft_,f));
    uint32_t id; TRY(repo_.journal().maxObject(Kind::Baseline,id)); if(id==UINT32_MAX) return Status::Capacity; ++id;
    static const TxStep steps[] CM_ROM={
        {TxOp::Constant,TxTarget::Destination,Field::Exists,1},
        {TxOp::CopyObject,TxTarget::Destination,Field::Exists,0},
        {TxOp::Now,TxTarget::Destination,Field::Created,0},
        {TxOp::DestinationId,TxTarget::System,Field::BaselineRef,0},
        {TxOp::CopyUserField,TxTarget::Destination,Field::Operator,0},
        {TxOp::CopyUserField,TxTarget::Destination,Field::Project,0},
        {TxOp::CopyUserField,TxTarget::Destination,Field::Date,0}
    };
    TRY(transact(steps,sizeof(steps)/sizeof(*steps),{Kind::Draft,draft_},{Kind::Baseline,id},nullptr,op));
    selected_=id; cursor_=0; page_=Page::SaveB; return Status::Ok;
}
Status Controller::cloneDraft(uint32_t id,const uint64_t& op) {
    uint32_t max; TRY(repo_.journal().maxObject(Kind::Draft,max)); if(max==UINT32_MAX) return Status::Capacity;
    TRY(begin(op)); Status s=repo_.copy(Kind::Baseline,id,Kind::Draft,max+1);
    TRY(finish(s)); draft_=max+1; return Status::Ok;
}
Status Controller::select(uint32_t id) {
    uint32_t exists=0; TRY(repo_.integer(Key(Kind::Baseline,id,Field::Exists),exists)); if(!exists) return Status::Missing;
    TRY(begin(0)); TRY(finish(repo_.putInteger(Key(Kind::System,0,Field::BaselineRef),id))); selected_=id; return Status::Ok;
}
Status Controller::openBaseline(uint32_t id,const uint64_t& op) {
    TRY(select(id)); TRY(cloneDraft(id,op)); savedEntry_=true; cursor_=0; page_=Page::Matu; return Status::Ok;
}
Status Controller::deleteBaseline(uint32_t id,bool confirm,const uint64_t& op) {
    if(!confirm) return Status::ConfirmRequired;
    uint32_t exists; TRY(repo_.integer(Key(Kind::Baseline,id,Field::Exists),exists)); if(!exists) return Status::Missing;
    uint32_t replacement=selected_;
    if(selected_==id) {
        Status st=repo_.list(Kind::Baseline,0,replacement);
        if(st==Status::Ok&&replacement==id) st=repo_.list(Kind::Baseline,id,replacement);
        if(st==Status::Missing) replacement=0; else if(st!=Status::Ok) return st;
    }
    TRY(begin(op)); Status saved=repo_.putInteger(Key(Kind::Baseline,id,Field::Exists),0);
    if(saved==Status::Ok&&selected_==id) saved=repo_.putInteger(Key(Kind::System,0,Field::BaselineRef),replacement);
    TRY(finish(saved)); selected_=replacement;
    return Status::Ok;
}
Status Controller::start(bool confirmed,const uint64_t& op) {
    SessionState old; TRY(state(old));
    if(old!=SessionState::Idle && old!=SessionState::Completed && !confirmed) return Status::ConfirmRequired;
    if(!selected_) return Status::Missing;
    struct Data { TxSample sample; Fit fit; Point point; } data;
    TRY(select(selected_)); Time& t=data.sample.time; t=clock_.now(); if(!t.valid) return Status::NoClock;
    Average& avg=data.sample.average; SensorFrame& frame=data.sample.frame;
    TRY(getAverage(avg,&frame)); TRY(repo_.model(Kind::Baseline,selected_,data.fit));
    uint32_t id; TRY(repo_.journal().maxObject(Kind::Session,id)); if(id==UINT32_MAX) return Status::Capacity; ++id;
    Point& p=data.point; p.id=1; p.revision=1; p.atMs=t.wallMs; p.temp=avg.operational; p.validMask=avg.mask;
    static_assert(sizeof(Data)<256,"Transaction offsets must fit uint8");
    static const TxStep steps[] CM_ROM={
        {TxOp::Constant,TxTarget::Destination,Field::Exists,1},
        {TxOp::SourceId,TxTarget::Destination,Field::BaselineRef,0},
        {TxOp::Constant,TxTarget::Destination,Field::State,uint8_t(SessionState::Active)},
        {TxOp::Time,TxTarget::Destination,Field::Start,offsetof(Data,sample)+offsetof(TxSample,time)+offsetof(Time,wallMs)},
        {TxOp::Number,TxTarget::Destination,Field::InitialTemp,offsetof(Data,sample)+offsetof(TxSample,average)+offsetof(Average,operational)},
        {TxOp::Model,TxTarget::Destination,Field::Model,offsetof(Data,fit)},
        {TxOp::CopyNumber,TxTarget::Destination,Field::Datum,0},
        {TxOp::CopyNumber,TxTarget::Destination,Field::Target,0},
        {TxOp::CopyText,TxTarget::Destination,Field::Name,0},
        {TxOp::CopyUserText,TxTarget::Destination,Field::Operator,0},
        {TxOp::CopyUserText,TxTarget::Destination,Field::Project,0},
        {TxOp::CopyUserText,TxTarget::Destination,Field::Date,0},
        {TxOp::Point,TxTarget::Destination,Field::Row,offsetof(Data,point)},
        {TxOp::Constant,TxTarget::Destination,Field::MaxRow,1},
        {TxOp::Constant,TxTarget::Destination,Field::Gap,0},
        {TxOp::Sensors,TxTarget::Destination,Field::Sensors,offsetof(Data,sample)}
    };
    TRY(transact(steps,sizeof(steps)/sizeof(*steps),{Kind::Baseline,selected_},{Kind::Session,id},&data,op));
#define PUT(expr) do { if(s==Status::Ok) s=(expr); } while(0)
    replayLive_=false; session_=id; liveM_=0; liveCompensation_=0; lastTemp_=avg.operational; lastWall_=t.wallMs; lastMono_=t.monoMs; lastSaveMono_=t.monoMs; lastFrameMono_=frame.sampledMonoMs; sampleKnown_=true; gapLatched_=false; inGap_=false; health_=Status::Ok; cursor_=0; page_=Page::RT; return Status::Ok;
}
Status Controller::addCheckpoint(Real day,const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    SessionState ss; TRY(state(ss)); if(ss!=SessionState::Active && ss!=SessionState::Preview) return Status::Invalid;
    if(!finite(day)||day<0) return Status::Invalid;
    Time t=clock_.now(); if(!t.valid) return Status::NoClock;
    Average avg; SensorFrame frame; TRY(getAverage(avg,&frame));
    uint32_t max; TRY(record.integer(Field::MaxRow,max)); if(max==UINT32_MAX) return Status::Capacity;
    Point last; Real m,datum; TRY(record.number(Field::Datum,datum)); TRY(replayPoints(repo_,Kind::Session,session_,datum,m,last));
    if(t.wallMs<=last.atMs || day<last.day) return Status::Invalid;
    Point p; p.id=max+1; p.revision=1; p.atMs=t.wallMs; p.day=day; p.temp=avg.operational; p.validMask=avg.mask;
    TRY(begin(op)); Status s=repo_.putPoint(Kind::Session,session_,p);
    PUT(repo_.putSensors(Kind::Session,session_,frame,avg,t));
    PUT(record.putInteger(Field::MaxRow,p.id));
    PUT(record.putInteger(Field::State,uint32_t(SessionState::Active)));
    PUT(record.erase(Field::Result));
    return finish(s);
}
Status Controller::editCheckpoint(uint32_t id,const char* field,const char* value,const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    SessionState ss; TRY(state(ss)); if(ss==SessionState::Completed || ss==SessionState::Idle) return Status::Invalid;
    Point p; TRY(repo_.point(Kind::Session,session_,id,p));
    if(CM_EQ(field,"temp")) TRY(parseReal(value,p.temp));
    else if(CM_EQ(field,"day")) { TRY(parseReal(value,p.day)); if(p.day<0 || (id==1&&p.day!=0)) return Status::Invalid; }
    else if(CM_EQ(field,"clock")) { uint32_t sec; TRY(parseClock(value,sec)); p.atMs=p.atMs/86400000ULL*86400000ULL+uint64_t(sec)*1000; }
    else if(CM_EQ(field,"date")) { uint64_t date; TRY(parseDate(value,date)); p.atMs=date+p.atMs%86400000ULL; }
    else return Status::Invalid;
    uint32_t max; TRY(record.integer(Field::MaxRow,max));
    for(uint32_t i=1;i<=max;++i) {
        if(i==id) continue;
        Point q; TRY(repo_.point(Kind::Session,session_,i,q));
        if((q.id==1 && p.atMs<q.atMs)||(id==1&&p.atMs>q.atMs)||(p.atMs<q.atMs&&p.day>q.day)||(p.atMs>q.atMs&&p.day<q.day)) return Status::Invalid;
    }
    Time now=clock_.now(); if(!now.valid) return Status::NoClock; if(p.atMs>now.wallMs) return Status::Invalid;
    if(p.revision==UINT32_MAX) return Status::Capacity;
    p.source=PointSource::Manual; p.validMask=0; ++p.revision;
    TRY(begin(op)); Status s=repo_.putPoint(Kind::Session,session_,p);
    if(id==1) { PUT(record.putTime(Field::Start,p.atMs)); PUT(record.putNumber(Field::InitialTemp,p.temp)); }
    PUT(record.erase(Field::Result));
    if(ss!=SessionState::Suspended) PUT(record.putInteger(Field::State,uint32_t(SessionState::Active)));
    TRY(finish(s)); replayLive_=true; sampleKnown_=false; return Status::Ok;
}
Status Controller::prepareResult(const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    SessionState ss; TRY(state(ss)); if(ss!=SessionState::Active&&ss!=SessionState::Preview) return Status::Invalid;
    uint32_t gap; TRY(record.integer(Field::Gap,gap)); if(gap) return Status::Gap;
    Result result; TRY(checkpointResult(Kind::Session,session_,0,result));
    TRY(roundResult(result));
    return storePreview(result,op);
}
Status Controller::roundResult(Result& result) {
    Fit fit; TRY(repo_.model(Kind::Session,session_,fit));
    Selection selection; selection.factor=result.prediction.factor; selection.day=result.prediction.referenceDay; selection.found=result.prediction.hasReference;
    result.prediction=trace(floor(result.rawM+Real(.5)),fit,selection);
    return Status::Ok;
}
Status Controller::storePreview(const Result& result,const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    Average avg; SensorFrame frame; TRY(getAverage(avg,&frame)); Time now=clock_.now(); if(!now.valid) return Status::NoClock;
    uint8_t b[73]; putReal(b,result.rawM); putReal(b+8,result.prediction.maturity); putReal(b+16,result.prediction.raw); putReal(b+24,result.prediction.factor); putReal(b+32,result.prediction.fc); putReal(b+40,result.prediction.referenceDay); put64(b+48,result.endMs); putReal(b+56,result.initialTemp); putReal(b+64,result.lastTemp); b[72]=result.prediction.hasReference;
    TRY(begin(op)); Status s=repo_.putSensors(Kind::Session,session_,frame,avg,now,Field::PreviewSensors);
    PUT(record.put(Field::Result,b,73));
    PUT(record.putInteger(Field::State,uint32_t(SessionState::Preview)));
    TRY(finish(s)); page_=Page::Str; return Status::Ok;
}
Status Controller::checkpointResult(Kind kind,uint32_t object,uint32_t pointId,Result& out) {
    Record record(repo_,kind,object);
    Real day; TRY(replayResult(kind,object,pointId,out,day));
    Real datum; Fit fit; uint32_t baseline=0;
    TRY(record.number(Field::Datum,datum)); TRY(repo_.model(kind,object,fit)); TRY(record.integer(Field::BaselineRef,baseline));
    StoredRows rows(repo_,Kind::Baseline,baseline); Selection selection; TRY(lookupRows(rows,datum,fit,day,selection));
    out.prediction=trace(out.rawM,fit,selection); return Status::Ok;
}
Status Controller::replayResult(Kind kind,uint32_t object,uint32_t pointId,Result& out,Real& day) {
    Record record(repo_,kind,object);
    Real datum; TRY(record.number(Field::Datum,datum));
    Point p,previous; bool first=true,found=false; uint64_t start=0; Accumulator acc;
    Status st;
    while((st=nextPoint(repo_,kind,object,first?nullptr:&previous,p))==Status::Ok) {
        if(first) start=p.atMs;
        if(!first&&p.day<previous.day) return Status::Invalid;
        TRY(acc.add(Real(p.atMs-start)/3600000,p.temp,datum));
        previous=p; first=false;
        if(pointId&&p.id==pointId) { found=true; break; }
    }
    if(first || (pointId&&!found)) return Status::Missing;
    if(st!=Status::Ok&&st!=Status::Missing) return st;
    day=p.day; out.rawM=acc.maturity(); out.endMs=p.atMs; out.lastTemp=p.temp;
    TRY(record.number(Field::InitialTemp,out.initialTemp)); return Status::Ok;
}
Status Controller::readResult(Kind kind,uint32_t id,Result& r) {
    Record record(repo_,kind,id);
    uint8_t b[73]; uint16_t n=73; TRY(record.get(Field::Result,b,n)); if(n!=73) return Status::Corrupt;
    r.rawM=getReal(b); r.prediction.maturity=getReal(b+8); r.prediction.raw=getReal(b+16); r.prediction.factor=getReal(b+24); r.prediction.fc=getReal(b+32); r.prediction.referenceDay=getReal(b+40); r.endMs=get64(b+48); r.initialTemp=getReal(b+56); r.lastTemp=getReal(b+64); r.prediction.hasReference=b[72]!=0;
    if(b[72]>1||r.rawM<0||r.prediction.maturity<0||r.prediction.fc<0||r.prediction.factor<=0||r.prediction.referenceDay<0) return Status::Corrupt;
    return finite(r.rawM)&&finite(r.prediction.maturity)&&finite(r.prediction.raw)&&finite(r.prediction.factor)&&finite(r.prediction.fc)&&finite(r.prediction.referenceDay)&&finite(r.initialTemp)&&finite(r.lastTemp)?Status::Ok:Status::Corrupt;
}
Status Controller::saveResult(const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    uint32_t existing=0; Status st=repo_.integer(Key(Kind::Result,session_,Field::Exists),existing);
    if(st==Status::Ok&&existing) { history_=session_; page_=Page::Hist; return Status::Ok; }
    if(st!=Status::Missing && st!=Status::Ok) return st;
    SessionState ss; TRY(state(ss)); if(ss!=SessionState::Preview) return Status::Invalid;
    uint32_t gap=0; TRY(record.integer(Field::Gap,gap)); if(gap) return Status::Gap;
    { Result r; TRY(readResult(Kind::Session,session_,r)); }
    static const TxStep steps[] CM_ROM={
        {TxOp::Constant,TxTarget::Destination,Field::Exists,1},
        {TxOp::CopyObject,TxTarget::Destination,Field::Exists,0},
        {TxOp::CopySensors,TxTarget::Destination,Field::Sensors,uint8_t(Field::PreviewSensors)},
        {TxOp::Constant,TxTarget::Destination,Field::State,uint8_t(SessionState::Completed)},
        {TxOp::Constant,TxTarget::Source,Field::State,uint8_t(SessionState::Completed)},
        {TxOp::Now,TxTarget::Destination,Field::Created,0}
    };
    TRY(transact(steps,sizeof(steps)/sizeof(*steps),{Kind::Session,session_},{Kind::Result,session_},nullptr,op));
    history_=session_; page_=Page::Hist; cursor_=0; return Status::Ok;
}
Status Controller::rowAt(uint32_t slot,Row& out) {
    if(slot>=6) return Status::Invalid;
    StoredRows rows(repo_,Kind::Draft,draft_,true); Status s=Status::Missing;
    for(uint32_t i=0;i<=cursor_+slot;++i) { s=rows.next(out); if(s!=Status::Ok) return s; } return s;
}
Status Controller::pointAt(uint32_t slot,Point& out) {
    if(slot>=6) return Status::Invalid;
    bool first=true; Point previous;
    for(uint32_t i=0;i<=cursor_+slot;++i) { TRY(nextPoint(repo_,page_==Page::HistD?Kind::Result:Kind::Session,page_==Page::HistD?history_:session_,first?nullptr:&previous,out)); previous=out; first=false; }
    return Status::Ok;
}
Status Controller::baselineAt(uint32_t slot,uint32_t& id) {
    if(slot>=6) return Status::Invalid;
    id=0; for(uint32_t i=0;i<=cursor_+slot;++i) TRY(repo_.list(Kind::Baseline,id,id)); return Status::Ok;
}
Status Controller::historyAt(uint32_t slot,uint32_t& id) {
    if(slot>=6) return Status::Invalid;
    id=0; for(uint32_t i=0;i<=cursor_+slot;++i) TRY(repo_.list(Kind::Result,id,id)); return Status::Ok;
}
Status Controller::setting(const char* name,const char* value,const uint64_t& op) {
    uint32_t v; TRY(parseU32(value,v)); Field field;
    if(CM_EQ(name,"hour")||CM_EQ(name,"minute")||CM_EQ(name,"second")) {
        if(v>(CM_EQ(name,"hour")?23u:59u)) return Status::Invalid;
        if(CM_EQ(name,"hour")) v=v*3600+settings_.intervalSeconds%3600;
        else if(CM_EQ(name,"minute")) v=settings_.intervalSeconds/3600*3600+v*60+settings_.intervalSeconds%60;
        else v=settings_.intervalSeconds/60*60+v;
        field=Field::Interval;
    }
    else if(CM_EQ(name,"interval")) { if(v>86399) return Status::Invalid; field=Field::Interval; }
    else if(CM_EQ(name,"brightness")) { if(v>100||v%5) return Status::Invalid; field=Field::Brightness; }
    else if(CM_EQ(name,"sound")) { if(v>1) return Status::Invalid; field=Field::Sound; }
    else if(CM_EQ(name,"autoSave")) { if(v>1) return Status::Invalid; field=Field::AutoSave; }
    else return Status::Invalid;
    Status hardware=Status::Ok;
    if(field==Field::Brightness) hardware=devices_.brightness(uint8_t(v));
    if(field==Field::Sound) hardware=devices_.sound(v!=0);
    if(hardware!=Status::Ok) return hardware;
    Status saved=begin(op);
    if(saved==Status::Ok) {
        static const TxStep steps[] CM_ROM={
            {TxOp::Integer,TxTarget::Destination,Field::Interval,0},
            {TxOp::Integer,TxTarget::Destination,Field::Brightness,0},
            {TxOp::Integer,TxTarget::Destination,Field::Sound,0},
            {TxOp::Integer,TxTarget::Destination,Field::AutoSave,0}
        };
        const Entity entity={Kind::Settings,0};
        saved=finish(applyTransaction(repo_,clock_,steps+uint8_t(field)-uint8_t(Field::Interval),1,entity,entity,&v));
    }
    if(saved!=Status::Ok) {
        if(field==Field::Brightness) devices_.brightness(settings_.brightness);
        if(field==Field::Sound) devices_.sound(settings_.sound);
        return saved;
    }
    if(field==Field::Interval) settings_.intervalSeconds=v;
    if(field==Field::Brightness) settings_.brightness=uint8_t(v);
    if(field==Field::Sound) settings_.sound=v!=0;
    if(field==Field::AutoSave) settings_.autoSave=v!=0;
    return Status::Ok;
}
bool Controller::validNavigation(Page destination) const {
#define P(n) (1UL<<(n))
    static const uint32_t targets[] CM_ROM={P(1),0,P(3)|P(9)|P(15)|P(16),P(2)|P(8),P(3)|P(5),P(4)|P(6),0,P(6),P(3),P(2)|P(10)|P(13),P(9),P(10),P(11),P(9),P(13),P(2),P(2)};
#undef P
    if(page_==Page::Matu) return destination==(savedEntry_?Page::SaveB:Page::Mat);
    return uint8_t(destination)<17&&(flashValue(targets+uint8_t(page_))&(1UL<<uint8_t(destination)));
}
Status Controller::saveIdentity() {
    Record record(repo_,Kind::User,0);
    char value[65]; TRY(record.text(Field::Operator,value,65)); TRY(record.text(Field::Project,value,65)); TRY(record.text(Field::Date,value,65));
    page_=Page::Main; ++view_; return Status::Ok;
}
Status Controller::reconcileGap(const char* a,const char* b,const uint64_t& op) {
    Record record(repo_,Kind::Session,session_);
    Status result;
        if(!CM_EQ(a,"1")) return Status::ConfirmRequired;
        if(!*b || !safeText(b,65)) return Status::Invalid;
        Average current; TRY(getAverage(current)); if(!clock_.now().valid||inGap_) return Status::Gap;
        uint64_t beginGap=0,endGap=0; TRY(record.time(Field::GapStart,beginGap)); TRY(record.time(Field::GapEnd,endGap));
        if(!endGap || endGap<beginGap) return Status::NoClock;
        uint32_t max; TRY(record.integer(Field::MaxRow,max)); bool before=false,after=false;
        for(uint32_t i=1;i<=max;++i) { Point p; TRY(repo_.point(Kind::Session,session_,i,p)); if(p.source==PointSource::Manual) { if(p.atMs<=beginGap) before=true; if(p.atMs>=endGap) after=true; } }
        if(!before||!after||max<2) return Status::Invalid;
        TRY(begin(op)); Status saved=record.putInteger(Field::Gap,0);
        if(saved==Status::Ok) saved=record.putText(Field::ClockIssue,b,65);
        result=finish(saved); if(result==Status::Ok) { gapLatched_=false; health_=Status::Ok; }
    return result;
}
Status Controller::dispatch(const char* verb,const char* a,const char* b,const char* c,const uint64_t& op) {
    Status result=Status::Invalid;
    const Command command=commandFromText(verb);
    if(op) {
        Key first; Status s=repo_.journal().findOperation(op,first);
        if(s==Status::Ok) {
            if(first.field==Field::Exists) {
                if(first.kind==Kind::Baseline) { selected_=first.object; page_=Page::SaveB; }
                if(first.kind==Kind::Result) { history_=first.object; page_=Page::Hist; }
                if(first.kind==Kind::Session) { if(session_>first.object) return status_=Status::Conflict; session_=first.object; SessionState ss; TRY(state(ss)); page_=ss==SessionState::Suspended?Page::SelB:Page::RT; }
                cursor_=0; ++view_;
            }
            return status_=Status::Ok;
        }
        if(s!=Status::Missing) return status_=s;
    }
    if(command==Command::STORAGE_RESCAN) return boot();
    if(!mounted_&&command!=Command::PAGE_READY&&command!=Command::NAV) return health_==Status::Ok?Status::Absent:health_;
    if(!allowedPage(command,uint8_t(page_))) return status_=Status::Invalid;
    uint32_t n=0;
    switch(command) {
        case Command::PAGE_READY: ++view_; result=Status::Ok; break;
        case Command::NAV: {
            if(CM_EQ(a,"BACK")) {
                static const uint8_t back[] CM_ROM={1,1,2,2,3,4,5,6,3,2,9,10,11,9,13,2,2};
                n=(page_==Page::Matu&&savedEntry_)?8:flashValue(back+uint8_t(page_));
            } else TRY(parseU32(a,n));
            if(n>16||!validNavigation(Page(n))) return status_=Status::Invalid;
            page_=Page(n); cursor_=0; ++view_; result=Status::Ok; break;
        }
        case Command::USER_SAVE: result=saveIdentity(); break;
        case Command::FIELD_SET: {
            bool userField=CM_EQ(a,"operator")||CM_EQ(a,"project")||CM_EQ(a,"date");
            if(userField==(page_==Page::User)) result=setField(a,b,op);
            break;
        }
        case Command::BASE_NEW: result=newBaseline(op); break;
        case Command::ROW_ADD_EARLY: case Command::ROW_ADD_LAB: result=addRow(command==Command::ROW_ADD_EARLY,op); break;
        case Command::ROW_FILL_EARLY: result=fillEarly(op); break;
        case Command::ROW_SET: case Command::ROW_SENSOR: case Command::ROW_DELETE: case Command::ROW_FOCUS: case Command::ROW_SCHEDULE: {
            TRY(parseU32(a,n)); Row row; TRY(rowAt(n,row));
            if(command==Command::ROW_SET) result=editRow(row.id,b,c,op);
            else if(command==Command::ROW_SENSOR) result=captureRow(row.id,op);
            else if(command==Command::ROW_DELETE) result=deleteRow(row.id,CM_EQ(b,"1"),op);
            else { focusedRow_=row.id; ++view_; result=Status::Ok; }
            break;
        }
        case Command::BASE_GENERATE: result=generate(op); break;
        case Command::BASE_SAVE: result=saveBaseline(op); break;
        case Command::BASE_PICK: { TRY(parseU32(a,n)); uint32_t id; TRY(baselineAt(n,id)); result=select(id); break; }
        case Command::BASE_OPEN: result=openBaseline(selected_,op); break;
        case Command::BASE_DELETE: result=deleteBaseline(selected_,CM_EQ(a,"1"),op); break;
        case Command::MEASURE_START: result=start(CM_EQ(a,"1"),op); break;
        case Command::CHECK_ADD: { Real day; TRY(parseReal(a,day)); result=addCheckpoint(day,op); break; }
        case Command::CHECK_SET: { TRY(parseU32(a,n)); Point point; TRY(pointAt(n,point)); result=editCheckpoint(point.id,b,c,op); break; }
        case Command::RESULT_PREPARE: result=prepareResult(op); break;
        case Command::RESULT_SAVE: result=saveResult(op); break;
        case Command::HISTORY_PICK: TRY(parseU32(a,n)); TRY(historyAt(n,history_)); page_=Page::HistD; cursor_=0; ++view_; result=Status::Ok; break;
        case Command::PAGE_ROWS:
            if(CM_EQ(a,"NEXT")) { if(cursor_>UINT32_MAX-6) return Status::Capacity; cursor_+=6; }
            else if(CM_EQ(a,"PREV")) cursor_=cursor_>=6?cursor_-6:0;
            else return Status::Invalid;
            ++view_; result=Status::Ok; break;
        case Command::SETTINGS_SET: result=setting(a,b,op); break;
        case Command::SETTINGS_STEP: {
            bool brightness=CM_EQ(a,"brightness");
            if(brightness?!(CM_EQ(b,"5")||CM_EQ(b,"-5")):!(CM_EQ(b,"1")||CM_EQ(b,"-1"))) return Status::Invalid;
            int value=0,max=59,step=brightness?5:1;
            if(brightness) { value=settings_.brightness; max=100; }
            else if(CM_EQ(a,"hour")) { value=int(settings_.intervalSeconds/3600); max=23; }
            else if(CM_EQ(a,"minute")) value=int(settings_.intervalSeconds/60%60);
            else if(CM_EQ(a,"second")) value=int(settings_.intervalSeconds%60);
            else return Status::Invalid;
            value+=b[0]=='-'?-step:step; if(value<0) value=0; if(value>max) value=max;
            char text[8]; CM_FMT(text,sizeof(text),"%u",unsigned(value)); result=setting(a,text,op); break;
        }
        case Command::SETTINGS_TOGGLE:
            if(CM_EQ(a,"sound")) result=setting(a,settings_.sound?"0":"1",op);
            else if(CM_EQ(a,"autoSave")) result=setting(a,settings_.autoSave?"0":"1",op);
            break;
        case Command::SETTINGS_SAVE: page_=Page::Main; ++view_; result=Status::Ok; break;
        case Command::SESSION_RESUME: {
            SessionState ss; TRY(state(ss)); if(ss!=SessionState::Suspended) return Status::Invalid;
            TRY(begin(op)); result=finish(repo_.putInteger(Key(Kind::Session,session_,Field::State),uint32_t(SessionState::Active)));
            if(result==Status::Ok) { sampleKnown_=false; page_=Page::RT; }
            break;
        }
        case Command::GAP_RECONCILE: result=reconcileGap(a,b,op); break;
        default: break;
    }
    if(result!=Status::Ok) repo_.journal().abort();
    return status_=result;
}
#undef PUT
#undef TRY
}
