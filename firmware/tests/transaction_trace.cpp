#include "app/Controller.h"
#include "HostPorts.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
#define OK(x) CHECK((x)==Status::Ok)
static std::ostringstream traceOutput;
struct Rig {
    host::MemoryStorage io,index; Journal journal; Repository repo;
    host::FakeClock clock; host::RecordedSensor sensor; host::Devices devices; Controller app;
    Rig(bool indexed) : journal(io),repo(journal),app(repo,clock,sensor,devices) {
        if(indexed) io.sidecar=&index;
        OK(app.boot()); OK(app.setField("operator","ConMT Operator")); OK(app.setField("project","Project trace")); OK(app.setField("date","2026-11-17"));
    }
    void baseline() {
        OK(app.newBaseline()); OK(app.setField("name","B trace")); OK(app.setField("target","35"));
        for(const char* key:{"cement","water","coarse","fine","retarderPct","acceleratorPct","flyAshPct"}) OK(app.setField(key,"1.23456789e1"));
        for(const char* key:{"retarderBrand","acceleratorBrand","flyAshBrand"}) OK(app.setField(key,"Brand trace"));
        OK(app.setField("pourDate","2026-11-17")); OK(app.setField("pourClock","00:00:00"));
        OK(app.editRow(2,"day","1")); OK(app.editRow(3,"day","2"));
        for(uint32_t id=1;id<=3;++id) OK(app.editRow(id,"temp","3.012500e1"));
        OK(app.editRow(2,"fc","10.11234567")); OK(app.editRow(3,"fc","22.3456789")); OK(app.generate());
    }
    void snapshot(const char* name,Status status) {
        traceOutput<<name<<' '<<unsigned(status)<<' '<<unsigned(app.page())<<' '<<app.view()<<' '<<app.selectedId()<<' '<<app.sessionId()<<' '<<app.historyId()<<' '<<journal.sequence()<<' '<<journal.committedBytes()<<' '<<io.bytes.size()<<' ';
        traceOutput<<(crc32(0xffffffffUL,io.bytes.data(),io.bytes.size())^0xffffffffUL)<<' '<<unsigned(devices.light)<<' '<<devices.audible<<' '<<app.settings().intervalSeconds<<'\n';
    }
};
static void flows(bool indexed) {
    Rig t(indexed); t.snapshot("identity",Status::Ok); t.baseline(); t.snapshot("generated",Status::Ok);
    for(const char* key:{"operator","project","retarderBrand","name"}) {
        std::string text(key==std::string("operator")||key==std::string("retarderBrand")?32:64,'A');
        t.snapshot(key,t.app.setField(key,text.c_str())); text.push_back('X'); t.snapshot("too-long",t.app.setField(key,text.c_str()));
    }
    for(const char* value:{"-20","-10","0","10","-15","20"}) t.snapshot("datum",t.app.setField("datum",value));
    OK(t.app.setField("datum","-20")); OK(t.app.generate()); OK(t.app.saveBaseline(101)); t.snapshot("save-baseline",Status::Ok);
    OK(t.app.setField("name","B trace revision")); OK(t.app.generate()); OK(t.app.saveBaseline(102)); t.snapshot("save-as-new",Status::Ok);
    OK(t.app.select(1)); OK(t.app.start(false,201)); t.snapshot("start",Status::Ok);
    for(unsigned i=0;i<2;++i) { t.clock.advance(1000); OK(t.app.tick()); }
    OK(t.app.addCheckpoint(1,202)); OK(t.app.prepareResult(203)); t.snapshot("next",Status::Ok);
    for(unsigned i=0;i<3;++i) t.sensor.frame.channel[i]=36.5;
    OK(t.app.setField("project","changed after NEXT")); OK(t.app.saveResult(204)); t.snapshot("save-result",Status::Ok);
    OK(t.app.saveResult(204)); t.snapshot("retry-save",Status::Ok); OK(t.app.boot());
    OK(t.app.dispatch("USER_SAVE")); OK(t.app.dispatch("NAV","15"));
    for(const char* key:{"hour","minute","second","brightness","sound","autoSave"}) {
        const char* value=std::string(key)=="brightness"?"50":"1";
        t.snapshot(key,t.app.dispatch("SETTINGS_SET",key,value));
    }
    t.snapshot("invalid-minute",t.app.dispatch("SETTINGS_SET","minute","60"));
    t.io.full=true; t.snapshot("setting-full",t.app.dispatch("SETTINGS_SET","brightness","90")); t.io.full=false;
}
static void failures(bool indexed) {
    for(unsigned action=0;action<4;++action) {
        for(int cut:{0,1,11,12,31,32,33,43,44,64,127,255,511,1024,4096}) {
            Rig t(indexed);
            if(action<3) { t.baseline(); if(action) OK(t.app.saveBaseline()); if(action==2) { OK(t.app.start()); OK(t.app.prepareResult()); } }
            else { OK(t.app.dispatch("USER_SAVE")); OK(t.app.dispatch("NAV","15")); }
            t.io.writeBudget=cut; Status st;
            if(action==0) st=t.app.saveBaseline(999);
            else if(action==1) st=t.app.start(false,999);
            else if(action==2) st=t.app.saveResult(999);
            else st=t.app.dispatch("SETTINGS_SET","brightness","50","",999);
            traceOutput<<"cut "<<indexed<<' '<<action<<' '<<cut<<' '; t.snapshot("state",st);
            t.io.writeBudget=-1; Journal reopened(t.io); st=reopened.mount();
            traceOutput<<"recovery "<<unsigned(st)<<' '<<reopened.sequence()<<' '<<reopened.committedBytes()<<'\n';
        }
    }
}
int main(int argc,char** argv) {
    flows(false); flows(true); failures(false); failures(true);
    if(argc==2) { std::ifstream input(argv[1]); CHECK(input.good()); std::ostringstream expected; expected<<input.rdbuf(); CHECK(expected.str()==traceOutput.str()); std::cout<<"Checkpoint public workflow and120fault traces match baseline PASS\n"; }
    else std::cout<<traceOutput.str();
}
