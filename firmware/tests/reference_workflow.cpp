#include "app/Controller.h"
#include "HostPorts.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <cstdlib>
#include <iomanip>
using namespace conmt;
#define CHECK(x) do{if(!(x)){std::cerr<<__LINE__<<" "<<#x<<'\n';std::exit(1);}}while(0)
#define OK(x) CHECK((x)==Status::Ok)
int main(int argc,char**){
    host::MemoryStorage io,index; if(argc>1) io.sidecar=&index;
    Journal journal(io);Repository repo(journal);host::FakeClock clock;host::RecordedSensor sensors;host::Devices devices;
    Controller app(repo,clock,sensors,devices);OK(app.boot());
    if(argc>1) CHECK(journal.indexed());
    OK(app.setField("operator","OP-EXCEL"));OK(app.setField("project","Client reference"));OK(app.setField("date","2026-11-16"));
    OK(app.newBaseline());OK(app.setField("name","Baseline from explicit lab input"));OK(app.setField("target","30"));
    std::ifstream fixture(CONMT_FIXTURE_PATH);CHECK(bool(fixture));
    Real a,b,r2;uint32_t n;fixture>>a>>b>>r2>>n;
    std::vector<Row> inputs;Real day,h,temp,fc,m,computed;
    while(fixture>>day>>h>>temp>>fc>>m>>computed){Row row;row.id=uint32_t(inputs.size()+1);row.revision=1;row.day=day;row.timeH=h;row.temp=temp;row.fc=fc;row.hasTemp=true;row.hasFc=fc>0;inputs.push_back(row);}
    CHECK(inputs.size()==41);
    OK(journal.begin());for(const Row& row:inputs)OK(repo.putRow(Kind::Draft,app.draftId(),row));OK(repo.putInteger(Key(Kind::Draft,app.draftId(),Field::MaxRow),41));OK(journal.commit());
    OK(app.generate());Fit fit;OK(repo.model(Kind::Draft,app.draftId(),fit));
    Real eps=sizeof(Real)==4?Real(.0001):Real(1e-10);CHECK(fabs(fit.a-a)<eps&&fabs(fit.b-b)<eps&&fabs(fit.r2-r2)<eps&&fit.n==n);
    OK(app.saveBaseline());OK(app.openBaseline(1));OK(app.dispatch("PAGE_ROWS","NEXT"));Row visible;OK(app.rowAt(0,visible));CHECK(visible.id==7);OK(app.captureRow(visible.id));
    Row original;OK(repo.row(Kind::Baseline,1,visible.id,original));CHECK(original.temp==inputs[6].temp);
    OK(app.addRow(false));uint32_t count;OK(repo.integer(Key(Kind::Draft,app.draftId(),Field::MaxRow),count));CHECK(count==42);while(app.cursor()<36)OK(app.dispatch("PAGE_ROWS","NEXT"));OK(app.rowAt(5,visible));CHECK(visible.id==42&&visible.day==29);
    OK(app.dispatch("NAV","BACK"));CHECK(app.page()==Page::SaveB);OK(app.dispatch("NAV","BACK"));OK(app.dispatch("NAV","BACK"));OK(app.dispatch("NAV","9"));OK(app.dispatch("NAV","10"));OK(app.dispatch("BASE_PICK","0"));OK(app.dispatch("MEASURE_START"));
    const unsigned days[]={4,6,26};const Real temperatures[]={30,40,10};const unsigned expectedRef[]={5,7,28};const Real expectedM[]={4320,6960,28560};
    unsigned priorDay=0;std::cout<<std::setprecision(12);
    for(unsigned i=0;i<3;++i){
        clock.advance(uint64_t(days[i]-priorDay)*86400000ULL);priorDay=days[i];for(unsigned ch=0;ch<3;++ch)sensors.frame.channel[ch]=temperatures[i];sensors.poll(clock.value.monoMs);
        OK(app.dispatch("CHECK_ADD",std::to_string(days[i]).c_str()));OK(app.dispatch("RESULT_PREPARE"));Result result;OK(app.readResult(Kind::Session,app.sessionId(),result));
        CHECK(fabs(result.rawM-expectedM[i])<Real(.01));CHECK(result.prediction.referenceDay==expectedRef[i]);
        if(i<2)CHECK(result.prediction.factor==1);else CHECK(fabs(result.prediction.factor-Real(.9942636037491221))<Real(.000001));
        CHECK(fabs(result.prediction.fc-predict(expectedM[i],fit.a,fit.b,result.prediction.factor))<Real(.001));
        std::cout<<"day="<<days[i]<<" ref="<<result.prediction.referenceDay<<" M="<<result.rawM<<" factor="<<result.prediction.factor<<" Fc="<<result.prediction.fc<<'\n';
        if(i<2)OK(app.dispatch("NAV","BACK"));
    }
    OK(app.dispatch("RESULT_SAVE"));Result saved;OK(app.readResult(Kind::Result,1,saved));CHECK(fabs(saved.prediction.fc-Real(38.7033333333))>Real(.5));
    OK(app.deleteBaseline(1,true));Controller reboot(repo,clock,sensors,devices);OK(reboot.boot());Result recovered;OK(reboot.readResult(Kind::Result,1,recovered));CHECK(recovered.prediction.fc==saved.prediction.fc&&recovered.rawM==saved.rawM);
    Fit snapshot;OK(repo.model(Kind::Result,1,snapshot));CHECK(snapshot.a==fit.a&&snapshot.b==fit.b);
    CHECK(achievement(saved.prediction.fc,35)!=achievement(saved.prediction.fc,30));
    std::cout<<"Full41row baseline, viewport, client days4/6/26, save/reboot/delete snapshot PASS\n";
}
