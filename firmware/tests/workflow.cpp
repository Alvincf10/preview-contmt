#include "app/Controller.h"
#include "hmi/Transport.h"
#include "HostPorts.h"
#include <vector>
#include <deque>
#include <string>
#include <sstream>
#include <cstring>
#include <iostream>
#include <cstdlib>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__FILE__<<":"<<__LINE__<<" "<<#x<<"\n"; std::exit(1); } } while(0)
#define OK(x) CHECK((x)==Status::Ok)
struct Rig {
    host::MemoryStorage io; Journal journal; Repository repo;
    host::FakeClock clock; host::RecordedSensor sensors; host::Devices devices; Controller app;
    Rig() : journal(io),repo(journal),app(repo,clock,sensors,devices) { OK(app.boot()); }
    void baseline() {
        OK(app.setField("operator","OP-1")); OK(app.setField("project","ConMT")); OK(app.setField("date","2026-11-16"));
        OK(app.dispatch("USER_SAVE")); OK(app.dispatch("NAV","3")); OK(app.newBaseline());
        OK(app.setField("name","Mix A")); OK(app.setField("target","30"));
        OK(app.editRow(2,"day","1")); OK(app.editRow(3,"day","2"));
        OK(app.editRow(1,"temp","20")); OK(app.editRow(2,"temp","20")); OK(app.editRow(3,"temp","20"));
        OK(app.editRow(2,"fc","10")); OK(app.editRow(3,"fc","20"));
        OK(app.generate()); OK(app.saveBaseline()); CHECK(app.selectedId()==1);
    }
};
static void workflows() {
    Rig t; CHECK(t.app.selectedId()==0); uint32_t id=0; CHECK(t.repo.list(Kind::Baseline,0,id)==Status::Missing);
    t.baseline(); Fit fit; OK(t.repo.model(Kind::Baseline,1,fit)); CHECK(fit.n==2);
    CHECK(t.app.deleteRow(1,true)==Status::Invalid);
    OK(t.app.openBaseline(1)); CHECK(t.app.page()==Page::Matu); OK(t.app.dispatch("NAV","BACK")); CHECK(t.app.page()==Page::SaveB);
    OK(t.app.openBaseline(1)); CHECK(t.app.editRow(2,"temp","")==Status::Ok); CHECK(t.app.generate()==Status::Invalid);
    OK(t.app.editRow(2,"temp","20")); OK(t.app.generate()); OK(t.app.saveBaseline(123)); CHECK(t.app.selectedId()==2);
    OK(t.app.dispatch("BASE_SAVE","","","",123)); uint32_t max=0; OK(t.journal.maxObject(Kind::Baseline,max)); CHECK(max==2);
    OK(t.app.select(1)); OK(t.app.start()); CHECK(t.app.sessionId()==1); Point p; OK(t.repo.point(Kind::Session,1,1,p)); CHECK(p.day==0&&p.temp==20);
    CHECK(t.app.start()==Status::ConfirmRequired);
    OK(t.app.prepareResult()); Result first; OK(t.app.readResult(Kind::Session,1,first)); CHECK(first.rawM==0&&first.prediction.fc==0);
    t.clock.advance(86400000ULL); t.sensors.poll(t.clock.value.monoMs); OK(t.app.addCheckpoint(1));
    OK(t.app.prepareResult()); Result before; OK(t.app.readResult(Kind::Session,1,before)); CHECK(before.rawM==960); // (20 - -20)*24
    CHECK(before.endMs==t.clock.value.wallMs); CHECK(before.prediction.referenceDay==1); CHECK(fabs(before.prediction.fc-10)<Real(.001));
    t.clock.advance(60000); t.sensors.poll(t.clock.value.monoMs); OK(t.app.prepareResult()); Result result; OK(t.app.readResult(Kind::Session,1,result)); CHECK(result.endMs==before.endMs);
    OK(t.app.saveResult(456)); OK(t.app.saveResult(456)); OK(t.repo.list(Kind::Result,0,id)); CHECK(id==1); CHECK(t.repo.list(Kind::Result,1,id)==Status::Missing);
    OK(t.app.deleteBaseline(1,true)); OK(t.app.readResult(Kind::Result,1,result)); CHECK(result.prediction.fc==before.prediction.fc);
    Controller restarted(t.repo,t.clock,t.sensors,t.devices); OK(restarted.boot()); OK(restarted.readResult(Kind::Result,1,result)); CHECK(result.rawM==960); CHECK(restarted.bootToken()!=t.app.bootToken());
    OK(restarted.dispatch("BASE_SAVE","","","",123)); CHECK(restarted.selectedId()==2&&restarted.page()==Page::SaveB);
    OK(restarted.dispatch("RESULT_SAVE","","","",456)); CHECK(restarted.historyId()==1&&restarted.page()==Page::Hist);
    OK(t.app.select(2)); OK(t.app.start()); t.clock.advance(1000); t.sensors.frame.validMask=0; CHECK(t.app.tick()==Status::NoSensor);
    CHECK(t.app.prepareResult()==Status::Gap); t.sensors.frame.validMask=7;
    Controller resume(t.repo,t.clock,t.sensors,t.devices); OK(resume.boot()); SessionState ss; OK(resume.state(ss)); CHECK(ss==SessionState::Suspended);
    CHECK(resume.prepareResult()==Status::Invalid);
    std::cout<<"baseline/session/history/recovery PASS\n";
}
static void failures() {
    host::MemoryStorage base; Journal j(base); Repository r(j); OK(j.mount()); OK(j.begin()); OK(r.putNumber(Key(Kind::Settings,0,Field::Target),7)); OK(j.commit());
    auto committed=base.bytes;
    for(int cut=0;cut<100;++cut) {
        host::MemoryStorage io; io.bytes=committed; Journal current(io); Repository rr(current); OK(current.mount()); io.writeBudget=cut;
        Status s=current.begin(999); if(s==Status::Ok) s=rr.putNumber(Key(Kind::Settings,0,Field::Target),99); if(s==Status::Ok) s=current.commit();
        io.writeBudget=-1; Journal recovered(io); Repository read(recovered); OK(recovered.mount()); Real value=0; OK(read.number(Key(Kind::Settings,0,Field::Target),value));
        CHECK(value==7||value==99); if(s==Status::Ok) CHECK(value==99);
        OK(recovered.begin()); OK(read.putNumber(Key(Kind::Settings,0,Field::Target),100)); OK(recovered.commit()); OK(read.number(Key(Kind::Settings,0,Field::Target),value)); CHECK(value==100);
    }
    host::MemoryStorage absent; Journal a(absent); absent.absent=true; CHECK(a.mount()==Status::Absent);
    host::MemoryStorage full; Journal f(full); Repository fr(f); OK(f.mount()); OK(f.begin()); full.full=true; CHECK(fr.putNumber(Key(Kind::User,0,Field::Target),1)==Status::Full);
    std::cout<<"100 power-cut budgets, absent/full storage PASS\n";
}
class Wire : public UartPort {
public:
    std::deque<uint8_t> rx; std::string tx; uint16_t credit=17;
    int read() override { if(rx.empty()) return -1; int b=rx.front(); rx.pop_front(); return b; }
    uint16_t writable() override { return credit; }
    uint16_t write(const uint8_t* b,uint16_t n) override { tx.append(reinterpret_cast<const char*>(b),n); return n; }
    void input(const std::string& s) { for(unsigned char c:s) rx.push_back(c); }
};
static void protocol() {
    Parser p; Frame f; std::string text="CM1|1|2|6|3|ROW_SET|0|temp|36.5\r\n";
    Status s=Status::Busy;
    for(char c:text) s=p.feed(uint8_t(c),0,f);
    OK(s); CHECK(f.boot==1&&f.seq==2&&f.page==6&&f.view==3&&!strcmp(f.args[2],"36.5"));
    std::string maxFrame="CM1|1|2|6|3|FIELD_SET|project|";
    maxFrame.resize(191,'A');
    for(char c:maxFrame) CHECK(p.feed(uint8_t(c),0,f)==Status::Busy);
    OK(p.feed('\n',0,f));
    CHECK(f.argc==2&&std::strlen(f.args[1])==191-maxFrame.find_last_of('|')-1);
    for(char c:maxFrame) CHECK(p.feed(uint8_t(c),0,f)==Status::Busy);
    CHECK(p.feed('A',0,f)==Status::Busy);
    CHECK(p.feed('\n',0,f)==Status::Invalid);
    for(int i=0;i<250;++i) p.feed('A',1,f); CHECK(p.feed('\n',1,f)==Status::Invalid);
    for(char c:text) s=p.feed(uint8_t(c),2,f); OK(s);
    p.feed('C',0,f); p.expire(3000); for(char c:text) s=p.feed(uint8_t(c),3001,f); OK(s);
    Rig rig; Wire wire; Transport panel(rig.app,wire);
    wire.input("CM1|0|0|1|0|PAGE_READY|2\n");
    for(unsigned i=0;i<1000;++i) panel.poll(0);
    CHECK(wire.tx.find("pInit.vBoot.val=")!=std::string::npos); CHECK(wire.tx.find("tOp.txt=")!=std::string::npos); CHECK(wire.tx.find("pInit.vRender.val=0")!=std::string::npos);
    std::ostringstream request; request<<"CM1|"<<rig.app.bootToken()<<"|1|1|"<<rig.app.view()<<"|FIELD_SET|operator|WIRE\n";
    wire.input(request.str()); for(unsigned i=0;i<1000;++i) panel.poll(1);
    char value[33]; OK(rig.repo.text(Key(Kind::User,0,Field::Operator),value,33)); CHECK(!strcmp(value,"WIRE"));
    wire.input(request.str()); for(unsigned i=0;i<1000;++i) panel.poll(2);
    CHECK(wire.tx.find("pInit.vStatus.val=0")!=std::string::npos);
    std::cout<<"parser, fragmentation, overflow, handshake, idempotency PASS\n";
}

static void corruptionAndTime() {
    Rig t; t.baseline(); OK(t.app.start());
    t.clock.advance(1000); OK(t.app.tick());
    t.sensors.fresh=false; Real before=t.app.liveMaturity();
    t.clock.advance(1000); OK(t.app.tick()); CHECK(t.app.liveMaturity()==before);
    t.clock.advance(6000); CHECK(t.app.tick()==Status::Stale); CHECK(t.app.prepareResult()==Status::Gap);
    host::MemoryStorage io; Journal j(io); Repository r(j); OK(j.mount());
    OK(j.begin()); OK(r.putNumber(Key(Kind::User,0,Field::Target),3)); OK(j.commit());
    io.bytes[45]^=1; Real n; CHECK(r.number(Key(Kind::User,0,Field::Target),n)==Status::Corrupt);
    host::MemoryStorage sync; Journal sj(sync); Repository sr(sj); OK(sj.mount()); OK(sj.begin()); OK(sr.putNumber(Key(Kind::User,0,Field::Target),3)); sync.failSync=true;
    CHECK(sj.commit()==Status::IoError); sync.failSync=false; CHECK(sj.begin()==Status::IoError); OK(sj.mount());
    uint8_t b[8]; Real values[]={0,Real(-0.0),Real(-20.25),Real(1e-20),Real(1e20)};
    for(Real v:values) { putReal(b,v); CHECK(getReal(b)==v); }
    uint32_t u; CHECK(parseU32("4294967295",u)==Status::Ok&&u==UINT32_MAX); CHECK(parseU32("4294967296",u)==Status::Invalid);
    uint64_t at; OK(parseDate("2026-12-31",at)); char date[12],clock[12]; calendarText(at+86400000ULL,date,sizeof(date),clock,sizeof(clock)); CHECK(!strcmp(date,"2027-01-01"));
    std::cout<<"stale sensor, corruption, sync uncertainty, codec, calendar PASS\n";
}

int main() { workflows(); failures(); protocol(); corruptionAndTime(); }
