#include "hmi/Transport.h"
#include "HostPorts.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
#define OK(x) CHECK((x)==Status::Ok)
class Wire : public UartPort {
public:
    std::string bytes;
    int read() override { return -1; }
    uint16_t writable() override { return 13; }
    uint16_t write(const uint8_t* data,uint16_t size) override { bytes.append(reinterpret_cast<const char*>(data),size); return size; }
};
int main(int argc,char** argv) {
    host::MemoryStorage io,index; io.sidecar=&index;
    Journal journal(io); Repository repo(journal); host::FakeClock clock;
    host::RecordedSensor sensors; host::Devices devices;
    Controller app(repo,clock,sensors,devices); Wire wire; Transport panel(app,wire);
    std::ostringstream output;
    auto capture=[&](const char* label) {
        panel.refresh(); wire.bytes.clear();
        for(unsigned i=0;i<3000;++i) panel.poll(0);
        output<<label<<" page="<<unsigned(app.page())<<'\n';
        size_t at=0,end; const std::string terminator(3,char(255));
        while((end=wire.bytes.find(terminator,at))!=std::string::npos) {
            std::string command=wire.bytes.substr(at,end-at);
            if(command.find(".txt=")!=std::string::npos) output<<command<<'\n';
            at=end+3;
        }
        CHECK(at==wire.bytes.size());
    };
    capture("initial"); OK(app.boot()); capture("empty identity");
    OK(app.setField("operator","OP-1")); OK(app.setField("project","ConMT")); OK(app.setField("date","2026-11-16")); capture("identity");
    OK(app.dispatch("USER_SAVE")); capture("main"); OK(app.dispatch("NAV","3")); capture("baseline menu");
    OK(app.newBaseline()); OK(app.setField("name","Mix A")); OK(app.setField("target","30")); capture("new baseline");
    OK(app.dispatch("NAV","5"));
    OK(app.setField("cement","350")); OK(app.setField("water","175")); OK(app.setField("coarse","1000")); OK(app.setField("fine","700"));
    OK(app.setField("retarderPct","1.25")); OK(app.setField("retarderBrand","R-A"));
    OK(app.setField("acceleratorPct","0.50")); OK(app.setField("acceleratorBrand","A-B"));
    OK(app.setField("flyAshPct","12.5")); OK(app.setField("flyAshBrand","F-C")); capture("materials");
    OK(app.dispatch("NAV","6")); capture("empty laboratory rows");
    OK(app.editRow(2,"day","1")); OK(app.editRow(3,"day","2"));
    for(uint32_t id=1;id<=3;++id) OK(app.editRow(id,"temp","20.00"));
    OK(app.editRow(2,"fc","10.00")); OK(app.editRow(3,"fc","20.00"));
    OK(app.dispatch("ROW_FOCUS","1")); capture("laboratory input");
    OK(app.generate()); capture("baseline result"); OK(app.saveBaseline()); capture("saved baseline list");
    OK(app.dispatch("NAV","BACK")); OK(app.dispatch("NAV","BACK")); OK(app.dispatch("NAV","9")); capture("strength menu");
    OK(app.dispatch("NAV","10")); capture("selected baseline"); OK(app.start()); capture("session day zero");
    clock.advance(86400000ULL); sensors.frame.channel[0]=30; sensors.frame.channel[1]=31; sensors.frame.channel[2]=32; sensors.poll(clock.value.monoMs);
    OK(app.addCheckpoint(1)); capture("checkpoint"); OK(app.prepareResult()); capture("result preview");
    OK(app.saveResult()); capture("history list"); OK(app.dispatch("HISTORY_PICK","0")); capture("history detail");
    OK(app.dispatch("NAV","BACK")); OK(app.dispatch("NAV","BACK")); OK(app.dispatch("NAV","BACK"));
    OK(app.dispatch("NAV","15")); capture("settings default");
    OK(app.dispatch("SETTINGS_SET","hour","2")); OK(app.dispatch("SETTINGS_SET","minute","3")); OK(app.dispatch("SETTINGS_SET","second","4"));
    OK(app.dispatch("SETTINGS_TOGGLE","sound")); OK(app.dispatch("SETTINGS_TOGGLE","autoSave")); capture("settings edited");
    OK(app.dispatch("SETTINGS_SAVE")); OK(app.dispatch("NAV","16")); capture("device info");
    if(argc==3&&std::string(argv[1])=="--capture") { std::ofstream file(argv[2]); file<<output.str(); CHECK(bool(file)); return 0; }
    std::ifstream file(CONMT_HMI_FIXTURE); CHECK(bool(file)); std::ostringstream expected; expected<<file.rdbuf();
    if(expected.str()!=output.str()) { std::cerr<<"HMI snapshot differs\n"<<output.str(); return 1; }
    std::cout<<"All 17 pages: populated/empty fields, laboratory text, frozen history and settings match wire snapshot\n";
}
