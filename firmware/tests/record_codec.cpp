#include "storage/Repository.h"
#include "storage/RecordCodec.h"
#include "HostPorts.h"
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <limits>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
#define OK(x) CHECK((x)==Status::Ok)
static void u32(std::vector<uint8_t>& b,uint32_t value) { for(unsigned i=0;i<4;++i) b.push_back(uint8_t(value>>(8*i))); }
static void u64(std::vector<uint8_t>& b,uint64_t value) { for(unsigned i=0;i<8;++i) b.push_back(uint8_t(value>>(8*i))); }
static void number(std::vector<uint8_t>& b,Real value) { double v=value; uint64_t bits; std::memcpy(&bits,&v,8); u64(b,bits); }
static void equal(Journal& journal,const Key& key,const std::vector<uint8_t>& expected) {
    uint8_t actual[128]; uint16_t size=sizeof(actual); OK(journal.get(key,actual,size));
    CHECK(size==expected.size()&&!std::memcmp(actual,expected.data(),size));
}
struct Values {
    Row row; Point point; Fit fit; Result result;
    SensorFrame frame; Average average; Time time;
    Values() {
        row.id=7; row.revision=0xfedcba98UL; row.day=4.125; row.timeH=99.1234567; row.temp=-0.0; row.fc=32.987654; row.hasFc=row.hasTemp=true;
        point.id=9; point.revision=123; point.atMs=7258118399999ULL; point.day=26; point.temp=-12.125; point.validMask=5; point.source=PointSource::Import;
        fit.a=-29.128726; fit.b=6.527225; fit.r2=.935766; fit.n=41; fit.valid=true;
        result.rawM=12345.6789; result.initialTemp=-0.0; result.lastTemp=36.5; result.endMs=7258118399123ULL;
        result.prediction.maturity=12346; result.prediction.raw=-.112345; result.prediction.factor=1.012; result.prediction.fc=31.123456; result.prediction.referenceDay=28; result.prediction.hasReference=true;
        frame.channel[0]=20.125; frame.channel[1]=30.5; frame.channel[2]=-0.0; frame.validMask=7; frame.sampledMonoMs=1500;
        average={10.0625,10.1,5}; time={2000,7258118399123ULL,true};
    }
    Status write(Repository& r) const {
        Status st=r.putRow(Kind::Draft,1,row);
        if(st==Status::Ok) st=r.putPoint(Kind::Session,1,point);
        if(st==Status::Ok) st=r.putModel(Kind::Baseline,1,fit);
        if(st==Status::Ok) st=r.putResult(Kind::Result,1,result);
        if(st==Status::Ok) st=r.putSensors(Kind::Result,1,frame,average,time);
        return st;
    }
};
static void layouts(bool indexed) {
    host::MemoryStorage io,index; if(indexed) io.sidecar=&index;
    Journal j(io); Repository repo(j); Values v; OK(j.mount()); OK(j.begin(123)); OK(v.write(repo)); OK(j.commit());
    std::vector<uint8_t> row,point,model,result,sensors;
    u32(row,v.row.revision); for(Real n:{v.row.day,v.row.timeH,v.row.temp,v.row.fc}) number(row,n); row.push_back(3);
    u32(point,v.point.revision); u64(point,v.point.atMs); number(point,v.point.day); number(point,v.point.temp); point.push_back(5); point.push_back(2);
    for(Real n:{v.fit.a,v.fit.b,v.fit.r2}) number(model,n); u32(model,v.fit.n);
    for(Real n:{v.result.rawM,v.result.prediction.maturity,v.result.prediction.raw,v.result.prediction.factor,v.result.prediction.fc,v.result.prediction.referenceDay}) number(result,n);
    u64(result,v.result.endMs); number(result,v.result.initialTemp); number(result,v.result.lastTemp); result.push_back(1);
    u64(sensors,v.time.wallMs-500); u32(sensors,1500);
    for(Real n:v.frame.channel) number(sensors,n);
    sensors.push_back(5); number(sensors,v.average.raw); number(sensors,v.average.operational);
    equal(j,Key(Kind::Draft,1,Field::Row,7),row); equal(j,Key(Kind::Session,1,Field::Row,9),point);
    equal(j,Key(Kind::Baseline,1,Field::Model),model); equal(j,Key(Kind::Result,1,Field::Result),result);
    equal(j,Key(Kind::Result,1,Field::Sensors),sensors);
    Row rr; Point pp; Fit ff; Result resultRead;
    OK(repo.row(Kind::Draft,1,7,rr)); CHECK(rr.day==v.row.day&&rr.timeH==v.row.timeH&&std::signbit(rr.temp));
    OK(repo.point(Kind::Session,1,9,pp)); CHECK(pp.atMs==v.point.atMs&&pp.source==v.point.source);
    OK(repo.model(Kind::Baseline,1,ff)); CHECK(ff.a==v.fit.a&&ff.r2==v.fit.r2&&ff.n==41);
    OK(repo.result(Kind::Result,1,resultRead)); CHECK(resultRead.rawM==v.result.rawM&&resultRead.prediction.raw==v.result.prediction.raw&&resultRead.endMs==v.result.endMs);
    for(unsigned flags:{4u,128u,255u}) {
        row.back()=uint8_t(flags); OK(j.begin()); OK(j.put(Key(Kind::Draft,1,Field::Row,7),row.data(),uint16_t(row.size()))); OK(j.commit());
        CHECK(repo.row(Kind::Draft,1,7,rr)==Status::Corrupt);
    }
    result.back()=2; OK(j.begin()); OK(j.put(Key(Kind::Result,1,Field::Result),result.data(),uint16_t(result.size()))); OK(j.commit());
    CHECK(repo.result(Kind::Result,1,resultRead)==Status::Corrupt);
    ValueReader reader; CHECK(j.openValue(Key(Kind::Result,1,Field::Result),72,reader)==Status::Corrupt);
    uint8_t bytes[8]; CHECK(reader.read(bytes,1)==Status::Invalid);
}
static void atomicCuts(bool indexed) {
    Values v;
    for(int cut=0;cut<400;++cut) {
        host::MemoryStorage io,index; if(indexed) io.sidecar=&index;
        Journal j(io); Repository repo(j); OK(j.mount()); OK(j.begin()); OK(repo.putInteger(Key(Kind::User,0),99)); OK(j.commit());
        io.writeBudget=cut; Status st=j.begin(123);
        if(st==Status::Ok) st=v.write(repo);
        if(st==Status::Ok) st=j.commit(); else j.abort();
        io.writeBudget=-1; Journal reboot(io); Repository recovered(reboot); OK(reboot.mount());
        Row r; Point p; Fit f; Result result;
        bool committed=recovered.row(Kind::Draft,1,7,r)==Status::Ok;
        CHECK((recovered.point(Kind::Session,1,9,p)==Status::Ok)==committed);
        CHECK((recovered.model(Kind::Baseline,1,f)==Status::Ok)==committed);
        CHECK((recovered.result(Kind::Result,1,result)==Status::Ok)==committed);
        uint8_t sensors[53]; uint16_t size=sizeof(sensors); CHECK((reboot.get(Key(Kind::Result,1,Field::Sensors),sensors,size)==Status::Ok)==committed);
        if(st==Status::Ok) CHECK(committed);
        uint32_t retained; OK(recovered.integer(Key(Kind::User,0),retained)); CHECK(retained==99);
        Key first; CHECK((reboot.findOperation(123,first)==Status::Ok)==committed);
    }
}
static void incomplete() {
    host::MemoryStorage io; Journal j(io); OK(j.mount()); OK(j.begin()); OK(j.startValue(Key(Kind::User,0),8));
    uint8_t bytes[4]={1,2,3,4}; OK(j.appendValue(bytes,4)); CHECK(j.commit()==Status::Invalid);
    OK(j.begin()); OK(j.startValue(Key(Kind::User,0),2)); CHECK(j.appendValue(bytes,4)==Status::Capacity); CHECK(j.commit()==Status::Invalid);
    OK(j.begin()); OK(j.put(Key(Kind::User,0),bytes,4)); OK(j.commit());
    ValueReader first,second; OK(j.openValue(Key(Kind::User,0),4,first)); OK(j.openValue(Key(Kind::User,0),4,second));
    uint8_t out[4]; CHECK(first.read(out,5)==Status::Capacity); OK(first.read(out,2)); CHECK(out[0]==1&&out[1]==2);
    OK(second.read(out,4)); CHECK(out[3]==4); OK(first.read(out,2)); CHECK(out[0]==3&&out[1]==4);
}
static bool integerField(Field f) {
    return f==Field::Exists||f==Field::MaxRow||f==Field::BaselineRef||f==Field::State||f==Field::Gap||
           f==Field::Interval||f==Field::Brightness||f==Field::Sound||f==Field::AutoSave;
}
static bool timeField(Field f) { return f==Field::Pour||f==Field::Created||f==Field::Start||f==Field::GapStart||f==Field::GapEnd; }
static bool textField(Field f) {
    return f==Field::Name||f==Field::Operator||f==Field::Project||f==Field::Date||f==Field::RetarderBrand||
           f==Field::AcceleratorBrand||f==Field::FlyAshBrand||f==Field::ClockIssue||
           f==Field::DayInput||f==Field::TempInput||f==Field::FcInput;
}
static void allFieldsAndExtremes() {
    host::MemoryStorage io,index; io.sidecar=&index; Journal journal(io); Repository repo(journal); OK(journal.mount());
    const uint32_t object=UINT32_MAX,indexId=UINT32_MAX;
    const Real reals[]={-0.0,std::numeric_limits<Real>::denorm_min(),-std::numeric_limits<Real>::min(),std::numeric_limits<Real>::max(),-std::numeric_limits<Real>::max()};
    const uint64_t times[]={0,1,7258118399999ULL,0x8000000000000000ULL,UINT64_MAX};
    const uint32_t integers[]={0,1,0x7fffffffUL,0x80000000UL,UINT32_MAX};
    const char* texts[]={"0","3.012500e1","Lab raw: 4.123456789012345678901234567890","2026-11-17","A B ! # $ % & ( ) + , - . / : ; < = > ? @ [ ] ^ _ ` { } ~"};
    for(unsigned edge=0;edge<5;++edge) {
        OK(journal.mount());
        uint64_t operation=UINT64_MAX-edge; OK(journal.begin(operation));
        for(unsigned kind=unsigned(Kind::User);kind<=unsigned(Kind::System);++kind) {
            for(unsigned field=unsigned(Field::Exists);field<=unsigned(Field::ClockAdjustment);++field) {
                Field f=Field(field); Key key(Kind(kind),object,f,indexId);
                if(integerField(f)) OK(repo.putInteger(key,integers[edge]));
                else if(timeField(f)) OK(repo.putTime(key,times[edge]));
                else if(textField(f)) OK(repo.putText(key,texts[edge],65));
                else if(f==Field::Row||f==Field::Model||f==Field::Result||f==Field::Sensors||f==Field::PreviewSensors||f==Field::ClockAdjustment) {
                    uint8_t bytes[128]; for(unsigned i=0;i<sizeof(bytes);++i) bytes[i]=uint8_t(i+edge);
                    OK(journal.put(key,bytes,f==Field::Row?37:(f==Field::Model?28:(f==Field::Result?73:(f==Field::ClockAdjustment?21:53)))));
                } else OK(repo.putNumber(key,reals[edge]));
            }
        }
        OK(journal.commit()); CHECK(get16(io.bytes.data()+4)==1&&get16(io.bytes.data()+6)==1);
        Journal restart(io); Repository recovered(restart); OK(restart.mount());
        Key first; OK(restart.findOperation(operation,first)); CHECK(first.kind==Kind::User&&first.object==object&&first.index==indexId);
        for(unsigned kind=unsigned(Kind::User);kind<=unsigned(Kind::System);++kind) {
            for(unsigned field=unsigned(Field::Exists);field<=unsigned(Field::ClockAdjustment);++field) {
                Field f=Field(field); Key key(Kind(kind),object,f,indexId);
                if(integerField(f)) { uint32_t n; OK(recovered.integer(key,n)); CHECK(n==integers[edge]); }
                else if(timeField(f)) { uint64_t n; OK(recovered.time(key,n)); CHECK(n==times[edge]); }
                else if(textField(f)) { char text[65]; OK(recovered.text(key,text,sizeof(text))); CHECK(!std::strcmp(text,texts[edge])); }
                else if(f==Field::Row||f==Field::Model||f==Field::Result||f==Field::Sensors||f==Field::PreviewSensors||f==Field::ClockAdjustment) {
                    uint8_t bytes[128]; uint16_t size=sizeof(bytes); OK(restart.get(key,bytes,size));
                    CHECK(size==(f==Field::Row?37:(f==Field::Model?28:(f==Field::Result?73:(f==Field::ClockAdjustment?21:53)))));
                    for(unsigned i=0;i<size;++i) CHECK(bytes[i]==uint8_t(i+edge));
                } else { Real number; OK(recovered.number(key,number)); CHECK(number==reals[edge]&&std::signbit(number)==std::signbit(reals[edge])); }
            }
        }
        uint32_t max; OK(restart.maxObject(Kind::Result,max)); CHECK(max==UINT32_MAX);
    }
}
int main() { layouts(false); layouts(true); atomicCuts(false); atomicCuts(true); incomplete(); allFieldsAndExtremes(); std::cout<<"Schema1 byte layouts, all41fields across7kinds, native numeric extremes, invalid flags, bounded value I/O and800multi-record write cuts PASS\n"; }
