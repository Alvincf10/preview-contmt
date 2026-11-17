#include "Presenter.h"
#include "../core/Flash.h"
#include <string.h>
namespace conmt {
namespace {
enum Op : uint8_t {
    Text, Number1, Number2, Integer, Date, Clock, Stamp, DateBlank, ClockBlank, NumberBlank,
    ModelA, ModelB, ModelR2, ModelCount, Equation, WaterCement, ObjectId,
    Maturity, Strength, Percent, Elapsed, ReferenceDay, LastTemp, Completed,
    Sensor1, Sensor2, Sensor3, SettingInterval, SettingBrightness, SettingSound,
    SettingAuto, SettingHour, SettingMinute, SettingSecond, Version, Mcu, Protocol, TextBlank
};
struct Descriptor { char name[10]; Op op; Field field; };
#define D(name,op,field) {name,op,Field::field}
static const Descriptor user[] CM_ROM={D("tOp",Text,Operator),D("tProj",Text,Project),D("tDate",Text,Date)};
static const Descriptor newBase[] CM_ROM={D("tName",Text,Name),D("tFc",Number1,Target),D("tTemp",Number1,Datum),D("tPDate",Date,Pour),D("tPClock",Clock,Pour)};
static const Descriptor materials[] CM_ROM={
    D("tCem",Number2,Cement),D("tWat",Number2,Water),D("tCoa",Number2,Coarse),D("tFin",Number2,Fine),
    D("tRetP",Number2,RetarderPct),D("tRetB",Text,RetarderBrand),D("tAccP",Number2,AcceleratorPct),D("tAccB",Text,AcceleratorBrand),
    D("tFlyP",Number2,FlyAshPct),D("tFlyB",Text,FlyAshBrand),D("tWC",WaterCement,Water)
};
static const Descriptor model[] CM_ROM={D("tName",Text,Name),D("tTarget",Number1,Target),D("tDatum",Number1,Datum),D("tA",ModelA,Model),D("tB",ModelB,Model),D("tR2",ModelR2,Model),D("tCount",ModelCount,Model),D("tEq",Equation,Model)};
static const Descriptor selected[] CM_ROM={D("tSelName",Text,Name),D("tSelFc",Number1,Target),D("tSelT",Number1,Datum),D("tSelR2",ModelR2,Model),D("tSelId",ObjectId,Exists),D("tSelDate",Date,Created)};
static const Descriptor list[] CM_ROM={D("tId",ObjectId,Exists),D("tName",TextBlank,Name),D("tVal",NumberBlank,Target),D("tDate",Text,Date),D("tCount",Integer,MaxRow)};
static const Descriptor measurement[] CM_ROM={
    D("tBase",Text,Name),D("tTarget",Number1,Target),D("tDatum",Number1,Datum),D("tPDate",DateBlank,Start),D("tPour",ClockBlank,Start),D("tInitTemp",NumberBlank,InitialTemp),
    D("tM",Maturity,Result),D("tFc",Strength,Result),D("tPct",Percent,Result),D("tElapsed",Elapsed,Result),D("tRefDay",ReferenceDay,Result)
};
static const Descriptor history[] CM_ROM={D("tOp",Text,Operator),D("tProj",Text,Project),D("tDate",Text,Date),D("tSavedAt",Stamp,Created),D("tLastT",LastTemp,Result),D("tStatus",Completed,State),D("tS1",Sensor1,Sensors),D("tS2",Sensor2,Sensors),D("tS3",Sensor3,Sensors),D("tCount",Integer,MaxRow)};
static const Descriptor settings[] CM_ROM={D("tInterval",SettingInterval,Interval),D("tBright",SettingBrightness,Brightness),D("tSound",SettingSound,Sound),D("tAuto",SettingAuto,AutoSave),D("tHour",SettingHour,Interval),D("tMin",SettingMinute,Interval),D("tSec",SettingSecond,Interval)};
static const Descriptor device[] CM_ROM={D("tVersion",Version,Exists),D("tMcu",Mcu,Exists),D("tProtocol",Protocol,Exists)};
#undef D
static void missing(char* value,size_t capacity) { CM_TEXT(value,capacity,"--"); }
static void integerText(char* value,size_t capacity,uint32_t number) { CM_FMT(value,capacity,"%lu",(unsigned long)number); }
static void calendar(uint64_t at,Op op,char* value,size_t capacity) __attribute__((noinline));
static void calendar(uint64_t at,Op op,char* value,size_t capacity) {
    char date[12],clock[12]; calendarText(at,date,sizeof(date),clock,sizeof(clock));
    if(op==Stamp) CM_FMT(value,capacity,"%s %s",date,clock);
    else CM_FMT(value,capacity,"%s",op==Date||op==DateBlank?date:clock);
}
static Status modelText(Repository& repo,Kind kind,uint32_t object,Op op,char* value,size_t capacity) __attribute__((noinline));
static Status modelText(Repository& repo,Kind kind,uint32_t object,Op op,char* value,size_t capacity) {
    Fit fit; Status st=repo.model(kind,object,fit); if(st!=Status::Ok) return st;
    if(op==ModelCount) integerText(value,capacity,fit.n);
    else if(op==Equation) {
        char a[28],b[28]; formatReal(a,sizeof(a),fit.a,3); formatReal(b,sizeof(b),fabs(fit.b),4);
        CM_FMT(value,capacity,"fc = %s %c %s ln(M)",a,fit.b<0?'-':'+',b);
    } else formatCoeff(value,capacity,op==ModelA?fit.a:(op==ModelB?fit.b:fit.r2),4);
    return Status::Ok;
}
static Status metric(Controller& app,Kind kind,uint32_t object,uint32_t point,Op op,char* value,size_t capacity) __attribute__((noinline));
static Status metric(Controller& app,Kind kind,uint32_t object,uint32_t point,Op op,char* value,size_t capacity) {
    Result result;
    Status st=point||app.page()==Page::RT?app.checkpointResult(kind,object,point,result):app.readResult(kind,object,result);
    if(st!=Status::Ok) return st;
    Real number=result.prediction.fc; uint8_t digits=1;
    switch(op) {
        case Maturity: number=point?result.rawM:result.prediction.maturity; digits=0; break;
        case ReferenceDay: number=result.prediction.referenceDay; break;
        case LastTemp: number=result.lastTemp; break;
        case Percent: {
            Real target; st=app.repository().number(Key(kind,object,Field::Target),target); if(st!=Status::Ok) return Status::Ok;
            number=achievement(number,target); digits=0; break;
        }
        case Elapsed: {
            uint64_t start; st=app.repository().time(Key(kind,object,Field::Start),start); if(st!=Status::Ok) return Status::Ok;
            uint64_t sec=(result.endMs-start)/1000;
            CM_FMT(value,capacity,"%lu:%02u:%02u",(unsigned long)(sec/3600),unsigned(sec/60%60),unsigned(sec%60)); return Status::Ok;
        }
        default: break;
    }
    formatReal(value,capacity,number,digits); return Status::Ok;
}
static Status sensorText(Repository& repo,Kind kind,uint32_t object,uint8_t channel,char* value,size_t capacity) __attribute__((noinline));
static Status sensorText(Repository& repo,Kind kind,uint32_t object,uint8_t channel,char* value,size_t capacity) {
    uint8_t frame[53]; uint16_t n=sizeof(frame); Status st=repo.journal().get(Key(kind,object,Field::Sensors),frame,n);
    if(st!=Status::Ok||n!=sizeof(frame)||!(frame[36]&(1u<<channel))) return Status::Missing;
    formatReal(value,capacity,getReal(frame+12+8*channel),1); return Status::Ok;
}
static void settingText(const Settings& settings,Op op,char* value,size_t capacity) {
    uint32_t h=settings.intervalSeconds/3600,m=settings.intervalSeconds/60%60,s=settings.intervalSeconds%60;
    if(op==SettingInterval) CM_FMT(value,capacity,"%02u:%02u:%02u",unsigned(h),unsigned(m),unsigned(s));
    else if(op>=SettingHour) CM_FMT(value,capacity,"%02u",unsigned(op==SettingHour?h:(op==SettingMinute?m:s)));
    else integerText(value,capacity,op==SettingBrightness?settings.brightness:(op==SettingSound?settings.sound:settings.autoSave));
}
static void scalar(Controller& app,Kind kind,uint32_t object,Op op,Field field,char* value,size_t capacity) {
    Repository& repo=app.repository(); Status st=Status::Ok;
    if(op==Text||op==TextBlank) st=repo.text(Key(kind,object,field),value,uint16_t(capacity));
    else if(op==Number1||op==Number2||op==NumberBlank) {
        Real number; st=repo.number(Key(kind,object,field),number); if(st==Status::Ok) formatReal(value,capacity,number,op==Number2?2:1);
    } else if(op==Integer||op==Completed) {
        uint32_t number; st=repo.integer(Key(kind,object,field),number);
        if(st==Status::Ok) { if(op==Integer) integerText(value,capacity,number); else if(number==uint32_t(SessionState::Completed)) CM_TEXT(value,capacity,"COMPLETED"); else st=Status::Missing; }
    } else if(op>=Date&&op<=ClockBlank) {
        uint64_t at; st=repo.time(Key(kind,object,field),at); if(st==Status::Ok) calendar(at,op,value,capacity);
    } else if(op>=ModelA&&op<=Equation) st=modelText(repo,kind,object,op,value,capacity);
    else if(op==ObjectId) integerText(value,capacity,object);
    else if(op==WaterCement) {
        Real water,cement; st=repo.number(Key(kind,object,Field::Water),water);
        if(st==Status::Ok) st=repo.number(Key(kind,object,Field::Cement),cement);
        if(st==Status::Ok&&cement>0) formatReal(value,capacity,water/cement,2); else st=Status::Missing;
    } else if(op>=Maturity&&op<=LastTemp) st=metric(app,kind,object,0,op,value,capacity);
    else if(op>=Sensor1&&op<=Sensor3) st=sensorText(repo,kind,object,uint8_t(op-Sensor1),value,capacity);
    else if(op>=SettingInterval&&op<=SettingSecond) settingText(app.settings(),op,value,capacity);
    else {
        static const char texts[][18] CM_ROM={"ConMT 1.0 schema1","ATmega328P","CM1 contract2"}; copyFlash(value,capacity,texts[op-Version]);
    }
    if(st!=Status::Ok&&op!=TextBlank&&op!=NumberBlank&&op!=DateBlank&&op!=ClockBlank) missing(value,capacity);
}
static void rowText(Repository& repo,uint32_t draft,const Row& row,Field field,Real numeric,char* out,size_t capacity) {
    Status st=repo.text(Key(Kind::Draft,draft,field,row.id),out,uint16_t(capacity)); Real parsed;
    if(st==Status::Ok&&parseReal(out,parsed)==Status::Ok&&parsed==numeric) return;
    formatReal(out,capacity,numeric,6); char* dot=strchr(out,'.');
    if(dot) { size_t n=strlen(out); while(n&&out[n-1]=='0') out[--n]=0; if(n&&out[n-1]=='.') out[--n]=0; }
    if(CM_EQ(out,"-0")) CM_COPY(out,"0");
}
}
bool Presenter::rows(uint8_t i,char* component,size_t cc,char* value,size_t vc) {
    Repository& repo=app_.repository(); uint32_t object=app_.draftId();
    if(i==30) {
        CM_TEXT(component,cc,"tHint"); Row row; uint64_t pour,at;
        if(!app_.focusedRow()||repo.row(Kind::Draft,object,app_.focusedRow(),row)!=Status::Ok||repo.time(Key(Kind::Draft,object,Field::Pour),pour)!=Status::Ok) CM_TEXT(value,vc,"Select row for schedule");
        else if(scheduleTime(pour,row.timeH,at)==Status::Ok) calendar(at,Stamp,value,vc); else missing(value,vc);
        return true;
    }
    if(i>30) return false;
    uint8_t slot=i/5,col=i%5; static const char names[][5] CM_ROM={"tDay","tTim","tFc","tT","tRid"}; indexedName(component,cc,names[col],slot);
    Row row; if(app_.rowAt(slot,row)!=Status::Ok) { missing(value,vc); return true; }
    if(col==4) integerText(value,vc,row.id);
    else if(col==1) {
        uint64_t pour,at; if(repo.time(Key(Kind::Draft,object,Field::Pour),pour)==Status::Ok&&scheduleTime(pour,row.timeH,at)==Status::Ok) calendar(at,Clock,value,vc); else missing(value,vc);
    } else if(col==0||(col==2&&row.hasFc)||(col==3&&row.hasTemp)) rowText(repo,object,row,col==0?Field::DayInput:(col==2?Field::FcInput:Field::TempInput),col==0?row.day:(col==2?row.fc:row.temp),value,vc);
    return true;
}
bool Presenter::points(uint8_t i,char* component,size_t cc,char* value,size_t vc) {
    if(i>=30) return false;
    uint8_t slot=i/5,col=i%5; static const char names[][5] CM_ROM={"tDay","tAt","tTmp","tCm","tCf"}; indexedName(component,cc,names[col],slot);
    Point point; if(app_.pointAt(slot,point)!=Status::Ok) { missing(value,vc); return true; }
    if(col==0||col==2) formatReal(value,vc,col==0?point.day:point.temp,1);
    else if(col==1) calendar(point.atMs,Stamp,value,vc);
    else if(metric(app_,app_.page()==Page::HistD?Kind::Result:Kind::Session,app_.page()==Page::HistD?app_.historyId():app_.sessionId(),point.id,col==3?Maturity:Strength,value,vc)!=Status::Ok) missing(value,vc);
    return true;
}
bool Presenter::field(uint16_t i,char* component,size_t cc,char* value,size_t vc) {
    const Descriptor* descriptors=nullptr; uint8_t count=0; Kind kind=Kind::Draft; uint32_t object=app_.draftId(); Page page=app_.page();
    switch(page) {
        case Page::User: descriptors=user; count=3; kind=Kind::User; object=0; break;
        case Page::NewB: descriptors=newBase; count=5; break;
        case Page::Mat: descriptors=materials; count=11; break;
        case Page::Matu: return rows(uint8_t(i),component,cc,value,vc);
        case Page::BaseR:
            if(i<8) { descriptors=model; count=8; }
            else if(i<19) { descriptors=materials; i-=8; count=11; }
            else { descriptors=user; i-=19; count=3; kind=Kind::User; object=0; }
            break;
        case Page::SaveB: case Page::SelB: case Page::Hist: {
            bool isHistory=page==Page::Hist; uint8_t columns=isHistory?5:3;
            kind=isHistory?Kind::Result:Kind::Baseline;
            if(!isHistory&&i>=18) {
                i-=18; if(i>=6) return false;
                object=app_.selectedId(); descriptors=selected; count=6;
                if(!object) { copyFlash(component,cc,descriptors[i].name); missing(value,vc); return true; }
                break;
            }
            if(i>=6*columns) return false;
            uint8_t slot=uint8_t(i/columns),col=uint8_t(i%columns); descriptors=list;
            indexedName(component,cc,descriptors[col].name,slot);
            Status st=isHistory?app_.historyAt(slot,object):app_.baselineAt(slot,object);
            if(st!=Status::Ok) { missing(value,vc); return true; }
            Descriptor d=flashValue(descriptors+col);
            if(isHistory&&col==2) { if(metric(app_,kind,object,0,Strength,value,vc)!=Status::Ok) value[0]=0; }
            else scalar(app_,kind,object,d.op,d.field,value,vc);
            return true;
        }
        case Page::RT: case Page::Str: case Page::HistD:
            kind=page==Page::HistD?Kind::Result:Kind::Session; object=page==Page::HistD?app_.historyId():app_.sessionId();
            if(i<11) { descriptors=measurement; count=11; }
            else if(page==Page::Str) return false;
            else if(i<41) return points(uint8_t(i-11),component,cc,value,vc);
            else if(page==Page::HistD) { descriptors=history; i-=41; count=10; }
            break;
        case Page::Set: descriptors=settings; count=7; break;
        case Page::Dev: descriptors=device; count=3; break;
        default: return false;
    }
    if(i>=count) return false;
    Descriptor d=flashValue(descriptors+i); copyFlash(component,cc,descriptors[i].name);
    scalar(app_,kind,object,d.op,d.field,value,vc); return true;
}
}
