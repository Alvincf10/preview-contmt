#include "core/Math.h"
#include "core/Chart.h"
#include "core/Calendar.h"
#include "storage/Journal.h"
#include <vector>
#include <iostream>
#include <cstdlib>
#include <limits>
#include <cstring>
using namespace conmt;
#define REQUIRE(x) do{if(!(x)){std::cerr<<__LINE__<<" "<<#x<<'\n';std::exit(1);}}while(0)
struct Rows:RowSource {
    std::vector<Row> rows;size_t pos=0;
    void reset() override{pos=0;}
    Status next(Row& r) override{if(pos==rows.size())return Status::Missing;r=rows[pos++];return Status::Ok;}
    void add(Real h,Real temp,Real fc,Real day=1){Row r;r.id=uint32_t(rows.size()+1);r.revision=1;r.timeH=h;r.temp=temp;r.fc=fc;r.day=day;r.hasTemp=true;r.hasFc=true;rows.push_back(r);}
};
int main(){
    Real nan=std::numeric_limits<Real>::quiet_NaN();
    REQUIRE(interval(10,20,0,0)==0&&interval(10,20,0,-1)==0&&interval(nan,20,0,1)==0);
    REQUIRE(interval(40,40,10,1)==30);REQUIRE(locked(36,Real(36.97),-20,1800)==Real(28.2425));
    Accumulator a;REQUIRE(a.add(2,10,0)==Status::Ok&&a.maturity()==0);REQUIRE(a.add(3,10,0)==Status::Ok&&a.maturity()==10);REQUIRE(a.add(3,50,0)==Status::Ok&&a.maturity()==10);
    Rows constant;constant.add(0,20,0);constant.add(1,20,10);constant.add(2,20,10);Fit fit;REQUIRE(fitRows(constant,0,fit)==Status::Ok);REQUIRE(fit.a==10&&fit.b==0&&fit.r2==1&&fit.n==2);
    Rows same;same.add(0,20,0);same.add(1,20,10);same.add(1,20,20);REQUIRE(fitRows(same,0,fit)==Status::NoModel);
    Rows noLab;noLab.add(0,20,0);noLab.add(1,20,-1);REQUIRE(fitRows(noLab,0,fit)==Status::NoModel);
    REQUIRE(fabs(fkzFromError(Real(.2))-Real(1)/Real(1.2))<Real(.000001));REQUIRE(fkzFromError(0)==1&&fkzFromError(Real(-.099))==1&&fkzFromError(Real(-.1))==1);REQUIRE(fabs(fkzFromError(Real(-.2))-Real(1.1))<Real(.000001));
    Fit calibrated;calibrated.a=10;calibrated.b=0;calibrated.r2=1;calibrated.n=2;calibrated.valid=true;
    Rows table;table.add(0,20,0,0);table.add(1,20,9,5);table.add(2,20,Real(12.5),7);Selection selected;
    REQUIRE(lookupRows(table,0,calibrated,6,selected)==Status::Ok&&selected.day==7&&fabs(selected.factor-Real(1.1))<Real(.000001));
    REQUIRE(lookupRows(table,0,calibrated,100,selected)==Status::Ok&&selected.day==7);
    table.rows[1].day=table.rows[2].day=1;REQUIRE(lookupRows(table,0,calibrated,1,selected)==Status::Ok&&fabs(selected.factor-Real(1.1))<Real(.000001));
    REQUIRE(lookupRows(table,0,calibrated,nan,selected)==Status::Ok&&selected.factor==1&&!selected.found);
    REQUIRE(lookupRows(noLab,0,calibrated,4,selected)==Status::Ok&&selected.factor==1&&!selected.found);
    REQUIRE(predict(0,1,2)==0&&predict(1,-10,2)==0&&predict(1,nan,2)==0&&predict(1,10,2,nan)==10);
    char text[32];formatCoeff(text,sizeof(text),Real(-.000001),4);REQUIRE(!strcmp(text,"0.0000"));formatReal(text,sizeof(text),achievement(Real(38.7033333333),30),0);REQUIRE(!strcmp(text,"129"));
    SensorFrame frame;frame.validMask=1;frame.channel[0]=0;Average avg;REQUIRE(average(frame,0,5000,avg)==Status::Ok&&avg.operational==0&&avg.mask==1);
    frame.validMask=3;frame.channel[1]=Real(1.25);REQUIRE(average(frame,0,5000,avg)==Status::Ok&&avg.operational==Real(.6));frame.validMask=0;REQUIRE(average(frame,0,5000,avg)==Status::NoSensor);
    frame.validMask=1;frame.sampledMonoMs=UINT32_MAX-500;REQUIRE(average(frame,499,5000,avg)==Status::Ok);
    for(const char* value:{"36.5x","36,5","NaN","Infinity","1e9999"}){Real result;REQUIRE(parseReal(value,result)==Status::Invalid);}
    REQUIRE(!safeText("a|b",65)&&!safeText("a\"b",65)&&!safeText("a\\b",65));
    uint32_t clock;Real hours;REQUIRE(parseClock("00:00",clock)==Status::Ok);REQUIRE(clockToHours(84600,clock,1,hours)==Status::Ok&&hours==Real(24.5));
    uint64_t date;REQUIRE(parseDate("2100-02-29",date)==Status::Invalid&&parseDate("2000-02-29",date)==Status::Ok);REQUIRE(scheduleTime(date,Real(1e20),date)==Status::Capacity);
    char d[20],c[20];REQUIRE(calendarText(UINT64_MAX,d,sizeof(d),c,sizeof(c))==Status::Invalid&&!strcmp(d,"--")&&!strcmp(c,"--"));
    Fit curveFit;curveFit.a=-29;curveFit.b=6.5;curveFit.r2=1;curveFit.n=10;curveFit.valid=true;ChartCurve curve(curveFit,Real(33738.1425));REQUIRE(curve.maximum()==35000);ChartSample sample;
    for(unsigned i=0;i<=64;++i){REQUIRE(curve.sample(uint8_t(i),sample));REQUIRE(fabs(sample.fc-(curveFit.a+curveFit.b*log(sample.maturity)))<Real(.0001));}REQUIRE(!curve.sample(65,sample));
    std::cout<<"N02/N03/N06/N08/N12-N20/N23/N30 V02/V03 S03/S04 T02/T03/T06 mathematical edge cases PASS\n";
}
