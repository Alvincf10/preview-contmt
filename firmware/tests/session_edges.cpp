#include "hmi/Transport.h"
#include "HostPorts.h"
#include <deque>
#include <sstream>
#include <iostream>
#include <cstdlib>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
#define OK(x) CHECK((x)==Status::Ok)
struct Rig {
    host::MemoryStorage io,index; Journal journal; Repository repo;
    host::FakeClock clock; host::RecordedSensor sensors; host::Devices devices; Controller app;
    Rig() : journal(io),repo(journal),app(repo,clock,sensors,devices) {
        io.sidecar=&index; OK(app.boot()); OK(app.newBaseline()); OK(app.setField("name","Edges")); OK(app.setField("target","30"));
        OK(app.editRow(2,"day","1")); OK(app.editRow(3,"day","2"));
        for(unsigned i=1;i<=3;++i) OK(app.editRow(i,"temp","20"));
        OK(app.editRow(2,"fc","10")); OK(app.editRow(3,"fc","20")); OK(app.generate()); OK(app.saveBaseline()); OK(app.start());
    }
};
struct Wire : UartPort {
    std::deque<uint8_t> rx; std::string tx; uint16_t credit=13;
    int read() override { if(rx.empty()) return -1; int result=rx.front(); rx.pop_front(); return result; }
    uint16_t writable() override { return credit; }
    uint16_t write(const uint8_t* bytes,uint16_t size) override { tx.append(reinterpret_cast<const char*>(bytes),size); return size; }
    void input(const std::string& value) { for(uint8_t byte:value) rx.push_back(byte); }
};
static void drain(Transport& panel) { for(unsigned i=0;i<2000;++i) panel.poll(0); }
static void dayZero() {
    Rig t; t.clock.advance(1000); OK(t.app.tick()); OK(t.app.editCheckpoint(1,"temp","40"));
    t.clock.advance(1000); OK(t.app.tick());
    CHECK(std::fabs(t.app.liveMaturity()-Real(100)/3600)<Real(1e-7));
    OK(t.app.editCheckpoint(1,"clock","00:00:01")); OK(t.app.tick());
    CHECK(std::fabs(t.app.liveMaturity()-Real(50)/3600)<Real(1e-7));
    uint32_t gap; OK(t.repo.integer(Key(Kind::Session,1,Field::Gap),gap)); CHECK(!gap);
    Result result; OK(t.app.checkpointResult(Kind::Session,1,0,result)); CHECK(result.rawM==0&&result.initialTemp==40);
    t.clock.advance(1000); OK(t.app.tick()); CHECK(std::fabs(t.app.liveMaturity()-Real(90)/3600)<Real(1e-7));
    Point old; OK(t.repo.point(Kind::Session,1,1,old)); t.io.full=true;
    CHECK(t.app.editCheckpoint(1,"temp","80")==Status::Full); t.io.full=false;
    Point retained; OK(t.repo.point(Kind::Session,1,1,retained)); CHECK(retained.temp==old.temp&&retained.revision==old.revision);
    t.clock.advance(1000); OK(t.app.tick()); CHECK(std::fabs(t.app.liveMaturity()-Real(130)/3600)<Real(1e-7));
}
static void clockEvents() {
    for(ClockCause cause:{ClockCause::Backward,ClockCause::Forward,ClockCause::Invalid}) {
        Rig t; const uint64_t before=t.clock.value.wallMs; t.clock.advance(1000);
        if(cause==ClockCause::Backward) t.clock.value.wallMs-=60000;
        if(cause==ClockCause::Forward) t.clock.value.wallMs+=60000;
        if(cause==ClockCause::Invalid) t.clock.value.valid=false;
        CHECK(t.app.tick()==Status::NoClock); CHECK(t.app.liveMaturity()==0);
        uint8_t event[21]; uint16_t size=sizeof(event); OK(t.journal.get(Key(Kind::Session,1,Field::ClockAdjustment),event,size));
        CHECK(size==sizeof(event)&&event[0]==uint8_t(cause)&&get64(event+1)==before);
        CHECK(get64(event+9)==(t.clock.value.valid?t.clock.value.wallMs:before));
        CHECK(get32(event+17)==1000); CHECK(t.app.prepareResult()==Status::Gap);
        uint64_t start,end; OK(t.repo.time(Key(Kind::Session,1,Field::GapStart),start)); OK(t.repo.time(Key(Kind::Session,1,Field::GapEnd),end)); CHECK(start<=end);
        Journal reboot(t.io); OK(reboot.mount()); size=sizeof(event); OK(reboot.get(Key(Kind::Session,1,Field::ClockAdjustment),event,size)); CHECK(event[0]==uint8_t(cause));
    }
}
static void lostAckReset() {
    Rig t; OK(t.app.prepareResult()); uint32_t oldBoot=t.app.bootToken();
    std::ostringstream request; request<<"CM1|"<<oldBoot<<"|77|12|"<<t.app.view()<<"|RESULT_SAVE\n";
    {
        Wire wire; Transport panel(t.app,wire); wire.input("CM1|0|0|12|0|PAGE_READY|2\n"); drain(panel); wire.tx.clear(); wire.credit=0;
        wire.input(request.str()); for(unsigned i=0;i<100&&t.app.page()!=Page::Hist;++i) panel.poll(0);
        CHECK(t.app.page()==Page::Hist&&wire.tx.empty());
    }
    Result saved; OK(t.app.readResult(Kind::Result,1,saved));
    Controller reboot(t.repo,t.clock,t.sensors,t.devices); OK(reboot.boot()); CHECK(reboot.bootToken()!=oldBoot);
    Wire wire; Transport panel(reboot,wire); wire.input("CM1|0|0|1|0|PAGE_READY|2\n"); drain(panel); wire.tx.clear();
    wire.input(request.str()); drain(panel); CHECK(reboot.page()==Page::Hist&&reboot.historyId()==1);
    uint32_t count; OK(t.journal.maxObject(Kind::Result,count)); CHECK(count==1);
    CHECK(wire.tx.find("pInit.vAck.val=77")!=std::string::npos);
    CHECK(wire.tx.find("pInit.vAckBoot.val="+std::to_string(oldBoot))!=std::string::npos);
    Result recovered; OK(reboot.readResult(Kind::Result,1,recovered)); CHECK(recovered.rawM==saved.rawM&&recovered.prediction.fc==saved.prediction.fc);
}
static void sharedReplay() {
    host::MemoryStorage io; Journal journal(io); Repository repo(journal); OK(journal.mount());
    OK(journal.begin()); OK(repo.putInteger(Key(Kind::Session,1,Field::MaxRow),3));
    for(uint32_t id=1;id<=3;++id) { Point p; p.id=id; p.day=id-1; p.atMs=uint64_t(id-1)*3600000; p.temp=Real(20*id-10); OK(repo.putPoint(Kind::Session,1,p)); }
    OK(journal.commit());
    Point last; Real maturity; OK(replayPoints(repo,Kind::Session,1,0,maturity,last)); CHECK(maturity==60&&last.id==3);
    OK(replayPoints(repo,Kind::Session,1,0,maturity,last,2,true)); CHECK(maturity==20&&last.id==2&&last.temp==30);
    CHECK(replayPoints(repo,Kind::Session,1,0,maturity,last,99,true)==Status::Missing);
    last=Point(); OK(nextPoint(repo,Kind::Session,1,nullptr,last)); OK(nextPoint(repo,Kind::Session,1,&last,last)); CHECK(last.id==2);
    OK(journal.begin()); Point invalidOrder; OK(repo.point(Kind::Session,1,2,invalidOrder)); invalidOrder.day=3; OK(repo.putPoint(Kind::Session,1,invalidOrder)); OK(journal.commit());
    OK(replayPoints(repo,Kind::Session,1,0,maturity,last,2,true)); CHECK(maturity==20);
    CHECK(replayPoints(repo,Kind::Session,1,0,maturity,last)==Status::Invalid);
    CHECK(replayPoints(repo,Kind::Session,1,0,maturity,last,99,true)==Status::Invalid);
}
int main() { dayZero(); clockEvents(); lostAckReset(); sharedReplay(); std::cout<<"Day0, clock, UART retry and shared replay endpoint/alias/ordering PASS\n"; }
