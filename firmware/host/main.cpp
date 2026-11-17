#include "app/Controller.h"
#include "HostPorts.h"
#include <iostream>
#include <sstream>
#include <string>
using namespace conmt;
int main(int argc,char** argv) {
    if(argc!=2) { std::cerr<<"usage: conmt_sim /path/to/CMT.JRN < commands\n"; return 2; }
    host::FileStorage io(argv[1]); Journal journal(io); Repository repo(journal);
    host::FakeClock clock; host::RecordedSensor sensors; host::Devices devices; Controller app(repo,clock,sensors,devices);
    Status boot=app.boot(); std::cout<<"BOOT "<<statusName(boot)<<'\n'; if(boot!=Status::Ok) return 1;
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream input(line); std::string cmd,a,b,c; input>>cmd>>a>>b>>c;
        Status st;
        if(cmd=="ADVANCE") { uint32_t ms; st=parseU32(a.c_str(),ms); if(st==Status::Ok) { clock.advance(ms); st=app.tick(); } }
        else if(cmd=="SENSOR") { Real value; st=parseReal(a.c_str(),value); if(st==Status::Ok) { for(unsigned i=0;i<3;++i) sensors.frame.channel[i]=value; sensors.poll(clock.value.monoMs); } }
        else st=app.dispatch(cmd.c_str(),a.c_str(),b.c_str(),c.c_str());
        std::cout<<cmd<<' '<<statusName(st)<<" page="<<unsigned(app.page())<<" view="<<app.view()<<" session="<<app.sessionId()<<'\n';
    }
}
