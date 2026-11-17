#include "../core/Flash.h"
#include "Transport.h"
#include <stdio.h>
#include <string.h>
namespace conmt {
void Parser::expire(uint32_t now) { if((used_||dropping_)&&uint32_t(now-lastAt_)>2000) { used_=0; dropping_=false; } }
Status Parser::feed(uint8_t b,uint32_t now,Frame& out) {
    expire(now); lastAt_=now;
    if(b=='\n') {
        if(dropping_) { dropping_=false; used_=0; return Status::Invalid; }
        if(used_&&buffer_[used_-1]=='\r') --used_;
        buffer_[used_]=0; used_=0;
        char* fields[9]; uint8_t count=1; fields[0]=buffer_;
        for(char* p=buffer_;*p;++p) if(*p=='|') { if(count==9) return Status::Invalid; *p=0; fields[count++]=p+1; }
        if(count<6 || !CM_EQ(fields[0],"CM1")) return Status::Invalid;
        uint32_t page;
        if(parseU32(fields[1],out.boot)!=Status::Ok||parseU32(fields[2],out.seq)!=Status::Ok||parseU32(fields[3],page)!=Status::Ok||parseU32(fields[4],out.view)!=Status::Ok||page>16||!*fields[5]) return Status::Invalid;
        out.page=uint8_t(page); out.argc=count-6; out.verb=fields[5];
        for(uint8_t i=0;i<3;++i) out.args[i]=i+6<count?fields[i+6]:"";
        return Status::Ok;
    }
    if(dropping_) return Status::Busy;
    if((b<32&&b!='\r')||b>126||used_>=sizeof(buffer_)-1) { dropping_=true; used_=0; return Status::Busy; }
    buffer_[used_++]=char(b); return Status::Busy;
}
Transport::Transport(Controller& app,UartPort& uart) : app_(app),uart_(uart),txSize_(0),txAt_(0),phase_(0),actualPage_(255),field_(0),seq_(0),ackBoot_(0),viewSent_(0),lastRefresh_(0),renderView_(0),lastRequestCrc_(0),lastOperation_(0),sensorCache_{0,0,0},averageCache_(0),sensorMask_(0),sensorStatus_(Status::NoSensor),lastAck_(Status::Ok),ack_(Status::Ok),dirty_(true),ackPending_(false),compatible_(false),full_(true),seenConnection_(false) {}
Status Transport::encode(const char* component,const char* value) {
    if(txSize_) return Status::Busy;
    if(!safeText(value,80)) return Status::Invalid;
    int n=CM_FMT(tx_,sizeof(tx_)-3,"%s.txt=\"%s\"",component,value);
    if(n<0 || n>int(sizeof(tx_)-4)) return Status::Capacity;
    txSize_=uint8_t(n+3); txAt_=0; for(uint8_t i=0;i<3;++i) tx_[n+i]=char(255); return Status::Ok;
}
Status Transport::numeric(const char* component,uint32_t value) {
    if(txSize_) return Status::Busy;
    int n=CM_FMT(tx_,sizeof(tx_)-3,"%s.val=%lu",component,(unsigned long)value);
    if(n<0||n>int(sizeof(tx_)-4)) return Status::Capacity;
    txSize_=uint8_t(n+3); txAt_=0; for(uint8_t i=0;i<3;++i) tx_[n+i]=char(255); return Status::Ok;
}
void Transport::flush() {
    if(!txSize_) return;
    uint16_t n=uart_.writable(),remaining=uint16_t(txSize_-txAt_); if(n>remaining) n=remaining;
    if(!n) return;
    uint16_t sent=uart_.write(reinterpret_cast<uint8_t*>(tx_+txAt_),n); if(sent>n) sent=n;
    txAt_+=uint8_t(sent); if(txAt_==txSize_) txAt_=txSize_=0;
}
static bool arity(const Frame& f) {
#define IS(v) CM_EQ(f.verb,v)
    if(IS("MEASURE_START")) return f.argc<=1;
    if(IS("FIELD_SET")||IS("SETTINGS_SET")||IS("SETTINGS_STEP")||IS("ROW_DELETE")||IS("GAP_RECONCILE")) return f.argc==2;
    if(IS("ROW_SET")||IS("CHECK_SET")) return f.argc==3;
    if(IS("SETTINGS_TOGGLE")||IS("NAV")||IS("ROW_FOCUS")||IS("ROW_SENSOR")||IS("ROW_SCHEDULE")||IS("BASE_PICK")||IS("BASE_DELETE")||IS("CHECK_ADD")||IS("HISTORY_PICK")||IS("PAGE_ROWS")) return f.argc==1;
    if(IS("USER_SAVE")||IS("BASE_NEW")||IS("ROW_ADD_EARLY")||IS("ROW_ADD_LAB")||IS("ROW_FILL_EARLY")||IS("BASE_GENERATE")||IS("BASE_SAVE")||IS("BASE_OPEN")||IS("RESULT_PREPARE")||IS("RESULT_SAVE")||IS("SETTINGS_SAVE")||IS("SESSION_RESUME")||IS("STORAGE_RESCAN")) return f.argc==0;
    return false;
#undef IS
}
static uint32_t requestCrc(const Frame& f) {
    uint32_t c=crc32(0xffffffffUL,reinterpret_cast<const uint8_t*>(f.verb),strlen(f.verb));
    for(uint8_t i=0;i<f.argc;++i) { const uint8_t separator='|'; c=crc32(c,&separator,1); c=crc32(c,reinterpret_cast<const uint8_t*>(f.args[i]),strlen(f.args[i])); }
    return c;
}
void Transport::accept(const Frame& f) {
    if(CM_EQ(f.verb,"PAGE_READY")) {
        actualPage_=f.page;
        uint32_t version=0; compatible_=f.argc==1&&parseU32(f.args[0],version)==Status::Ok&&version==HmiContractVersion;
        if(!compatible_) ack_=Status::Version;
        else if(f.boot==0&&seenConnection_) { Status s=app_.newConnection(); if(s!=Status::Ok) ack_=s; seenConnection_=false; }
        else if(!ackPending_) ack_=Status::Ok;
        if(f.boot&&f.boot==app_.bootToken()) seenConnection_=true;
        if(!ackPending_) seq_=0;
        dirty_=full_=true; phase_=0; field_=0; return;
    }
    if(ackPending_) return;
    seq_=f.seq; ackBoot_=f.boot;
    uint64_t operation=(uint64_t(f.boot)<<32)|f.seq;
    uint32_t fingerprint=requestCrc(f);
    if(!compatible_) ack_=Status::Version;
    else if(!arity(f)) ack_=Status::Invalid;
    else if(operation&&operation==lastOperation_) ack_=fingerprint==lastRequestCrc_?lastAck_:Status::Conflict;
    else if(CM_EQ(f.verb,"STORAGE_RESCAN")&&f.page==uint8_t(app_.page())&&f.seq) ack_=app_.dispatch(f.verb);
    else {
        Key previous; Status duplicate=f.boot&&f.seq?app_.repository().journal().findOperation(operation,previous):Status::Missing;
        if(duplicate==Status::Ok) ack_=app_.dispatch(f.verb,f.args[0],f.args[1],f.args[2],operation);
        else if(duplicate!=Status::Missing) ack_=duplicate;
        else if(f.boot!=app_.bootToken()||!f.seq) ack_=Status::Conflict;
        else if(f.page!=uint8_t(app_.page())||(f.view!=app_.view()&&!(CM_EQ(f.verb,"NAV")&&CM_EQ(f.args[0],"BACK")))) ack_=Status::Stale;
        else ack_=app_.dispatch(f.verb,f.args[0],f.args[1],f.args[2],operation);
    }
    if(f.boot&&f.boot==app_.bootToken()) seenConnection_=true;
    if(operation) { lastOperation_=operation; lastRequestCrc_=fingerprint; lastAck_=ack_; }
    dirty_=full_=true; phase_=0; field_=0; ackPending_=true;
}
static void rowText(Repository& repo,uint32_t draft,const Row& row,Field field,Real numeric,char* out,size_t capacity) {
    Status st=repo.text(Key(Kind::Draft,draft,field,row.id),out,uint16_t(capacity));
    Real parsed;
    if(st==Status::Ok&&parseReal(out,parsed)==Status::Ok&&parsed==numeric) return;
    formatReal(out,capacity,numeric,6);
    char* dot=strchr(out,'.');
    if(dot) { size_t n=strlen(out); while(n&&out[n-1]=='0') out[--n]=0; if(n&&out[n-1]=='.') out[--n]=0; }
    if(CM_EQ(out,"-0")) CM_COPY(out,"0");
}
bool Transport::renderField(uint16_t i,char* component,size_t cc,char* value,size_t vc) {
    Repository& r=app_.repository(); uint32_t object=app_.draftId(); Kind kind=Kind::Draft; Page page=app_.page();
    value[0]=0;
    if(i==0) { char date[12]; Time now=app_.clock().now(); if(now.valid) calendarText(now.wallMs,date,sizeof(date),value,vc); else CM_TEXT(value,vc,"--"); CM_TEXT(component,cc,"tClock"); return true; }
    if(i==1) { uint8_t battery; Status s=app_.devices().battery(battery); if(s==Status::Ok) CM_FMT(value,vc,"%u%%",unsigned(battery)); else CM_TEXT(value,vc,"--"); CM_TEXT(component,cc,"tBatt"); return true; }
    if(i==2) { CM_FMT(value,vc,"%s",statusName(ack_==Status::Ok?app_.status():ack_)); CM_TEXT(component,cc,"tMsg"); return true; }
    i-=3;
    Field field=Field::Name; bool isText=false; uint8_t digits=1;
    if(page==Page::User) {
        if(i>2) return false;
        static const Field fields[]={Field::Operator,Field::Project,Field::Date};
        static const char names[][6] CM_ROM={"tOp","tProj","tDate"};
        field=fields[i]; CM_FMT(component,cc,"%s",flashText(names[i])); kind=Kind::User; object=0; isText=true;
    } else if(page==Page::NewB) {
        if(i>4) return false;
        if(i==3||i==4) { uint64_t at; char date[12],clock[12]; if(r.time(Key(kind,object,Field::Pour),at)==Status::Ok) calendarText(at,date,sizeof(date),clock,sizeof(clock)); else { CM_COPY(date,"--"); CM_COPY(clock,"--"); } CM_FMT(component,cc,"%s",i==3?"tPDate":"tPClock"); CM_FMT(value,vc,"%s",i==3?date:clock); return true; }
        static const Field fields[]={Field::Name,Field::Target,Field::Datum};
        static const char names[][6] CM_ROM={"tName","tFc","tTemp"}; field=fields[i]; CM_FMT(component,cc,"%s",flashText(names[i])); isText=i==0;
    } else if(page==Page::Mat||(page==Page::BaseR&&i>=8&&i<19)) {
        if(page==Page::BaseR) i-=8;
        if(i>10) return false;
        if(i==10) { Real w,c; CM_TEXT(component,cc,"tWC"); if(r.number(Key(kind,object,Field::Water),w)==Status::Ok&&r.number(Key(kind,object,Field::Cement),c)==Status::Ok&&c>0) formatReal(value,vc,w/c,2); else CM_TEXT(value,vc,"--"); return true; }
        static const Field fields[]={Field::Cement,Field::Water,Field::Coarse,Field::Fine,Field::RetarderPct,Field::RetarderBrand,Field::AcceleratorPct,Field::AcceleratorBrand,Field::FlyAshPct,Field::FlyAshBrand};
        static const char names[][6] CM_ROM={"tCem","tWat","tCoa","tFin","tRetP","tRetB","tAccP","tAccB","tFlyP","tFlyB"};
        field=fields[i]; CM_FMT(component,cc,"%s",flashText(names[i])); isText=i==5||i==7||i==9; digits=2;
    } else if(page==Page::Matu) {
        if(i==30) {
            CM_TEXT(component,cc,"tHint"); Row selected; uint64_t pour;
            if(!app_.focusedRow()||r.row(kind,object,app_.focusedRow(),selected)!=Status::Ok||r.time(Key(kind,object,Field::Pour),pour)!=Status::Ok) CM_TEXT(value,vc,"Select row for schedule");
            else { char date[12],clock[12]; uint64_t at; if(scheduleTime(pour,selected.timeH,at)==Status::Ok) { calendarText(at,date,sizeof(date),clock,sizeof(clock)); CM_FMT(value,vc,"%s %s",date,clock); } else CM_TEXT(value,vc,"--"); }
            return true;
        }
        if(i>30) return false;
        uint8_t slot=uint8_t(i/5),col=uint8_t(i%5); Row row; Status s=app_.rowAt(slot,row);
        static const char names[][5] CM_ROM={"tDay","tTim","tFc","tT","tRid"}; CM_FMT(component,cc,"%s%u",flashText(names[col]),unsigned(slot));
        if(s!=Status::Ok) { CM_TEXT(value,vc,"--"); return true; }
        if(col==4) CM_FMT(value,vc,"%lu",(unsigned long)row.id);
        else if(col==0) rowText(r,object,row,Field::DayInput,row.day,value,vc);
        else if(col==1) { uint64_t pour,at; char date[12]; if(r.time(Key(kind,object,Field::Pour),pour)==Status::Ok&&scheduleTime(pour,row.timeH,at)==Status::Ok) calendarText(at,date,sizeof(date),value,vc); else CM_TEXT(value,vc,"--"); }
        else if(col==2) { if(row.hasFc) rowText(r,object,row,Field::FcInput,row.fc,value,vc); }
        else if(row.hasTemp) rowText(r,object,row,Field::TempInput,row.temp,value,vc);
        return true;
    } else if(page==Page::BaseR) {
        if(i==7) { CM_TEXT(component,cc,"tEq"); Fit fit; if(r.model(kind,object,fit)==Status::Ok) { char a[28],b[28]; formatReal(a,sizeof(a),fit.a,3); formatReal(b,sizeof(b),fabs(fit.b),4); CM_FMT(value,vc,"fc = %s %c %s ln(M)",a,fit.b<0?'-':'+',b); } else CM_TEXT(value,vc,"--"); return true; }
        if(i>=19&&i<=21) { static const Field context[]={Field::Operator,Field::Project,Field::Date}; static const char names[][6] CM_ROM={"tOp","tProj","tDate"}; CM_FMT(component,cc,"%s",flashText(names[i-19])); if(r.text(Key(Kind::User,0,context[i-19]),value,uint16_t(vc))!=Status::Ok) CM_TEXT(value,vc,"--"); return true; }
        if(i>6) return false;
        static const char names[][8] CM_ROM={"tName","tTarget","tDatum","tA","tB","tR2","tCount"}; CM_FMT(component,cc,"%s",flashText(names[i]));
        if(i<3) { field=i==0?Field::Name:(i==1?Field::Target:Field::Datum); isText=i==0; }
        else { Fit fit; Status s=r.model(kind,object,fit); if(s!=Status::Ok) CM_TEXT(value,vc,"--"); else if(i==6) CM_FMT(value,vc,"%lu",(unsigned long)fit.n); else formatCoeff(value,vc,i==3?fit.a:(i==4?fit.b:fit.r2),4); return true; }
    } else if(page==Page::SaveB||page==Page::SelB||page==Page::Hist) {
        bool history=page==Page::Hist;
        if(!history&&i>=18) {
            if(i>23) return false;
            static const char names[][9] CM_ROM={"tSelName","tSelFc","tSelT","tSelR2","tSelId","tSelDate"};
            uint8_t item=uint8_t(i-18); CM_FMT(component,cc,"%s",flashText(names[item]));
            uint32_t id=app_.selectedId(); if(!id) { CM_TEXT(value,vc,"--"); return true; }
            if(item==0) { if(r.text(Key(Kind::Baseline,id,Field::Name),value,uint16_t(vc))!=Status::Ok) CM_TEXT(value,vc,"--"); }
            if(item==1||item==2) { Real number; if(r.number(Key(Kind::Baseline,id,item==1?Field::Target:Field::Datum),number)==Status::Ok) formatReal(value,vc,number,1); else CM_TEXT(value,vc,"--"); }
            if(item==3) { Fit fit; if(r.model(Kind::Baseline,id,fit)==Status::Ok) formatCoeff(value,vc,fit.r2,4); else CM_TEXT(value,vc,"--"); }
            if(item==4) CM_FMT(value,vc,"%lu",(unsigned long)id);
            if(item==5) { uint64_t at; char clock[12]; if(r.time(Key(Kind::Baseline,id,Field::Created),at)==Status::Ok) calendarText(at,value,vc,clock,sizeof(clock)); else CM_TEXT(value,vc,"--"); }
            return true;
        }
        uint8_t columns=history?5:3;
        if(i>=uint16_t(6*columns)) return false;
        uint8_t slot=uint8_t(i/columns),col=uint8_t(i%columns); uint32_t id=0;
        Status s=history?app_.historyAt(slot,id):app_.baselineAt(slot,id);
        static const char names[][7] CM_ROM={"tId","tName","tVal","tDate","tCount"}; CM_FMT(component,cc,"%s%u",flashText(names[col]),unsigned(slot));
        if(s!=Status::Ok) { CM_TEXT(value,vc,"--"); return true; }
        if(col==0) CM_FMT(value,vc,"%lu",(unsigned long)id);
        else if(col==1) r.text(Key(history?Kind::Result:Kind::Baseline,id,Field::Name),value,uint16_t(vc));
        else if(col==2) { if(history) { Result result; if(app_.readResult(Kind::Result,id,result)==Status::Ok) formatReal(value,vc,result.prediction.fc,1); } else { Real target; if(r.number(Key(Kind::Baseline,id,Field::Target),target)==Status::Ok) formatReal(value,vc,target,1); } }
        else if(col==3) { if(r.text(Key(Kind::Result,id,Field::Date),value,uint16_t(vc))!=Status::Ok) CM_TEXT(value,vc,"--"); }
        else { uint32_t count; if(r.integer(Key(Kind::Result,id,Field::MaxRow),count)==Status::Ok) CM_FMT(value,vc,"%lu",(unsigned long)count); else CM_TEXT(value,vc,"--"); }
        return true;
    } else if(page==Page::RT||page==Page::Str||page==Page::HistD) {
        kind=page==Page::HistD?Kind::Result:Kind::Session; object=page==Page::HistD?app_.historyId():app_.sessionId();
        if(page==Page::RT && i<6) {
            if(i>=4) { char date[12],clock[12]; Time t=app_.clock().now(); if(t.valid) calendarText(t.wallMs,date,sizeof(date),clock,sizeof(clock)); else { CM_COPY(date,"--"); CM_COPY(clock,"--"); } CM_FMT(component,cc,"%s",i==4?"tNowD":"tNowT"); CM_FMT(value,vc,"%s",i==4?date:clock); return true; }
            snprintf(component,cc,i==3?"tAvg":"tS%u",unsigned(i+1));
            if(sensorStatus_!=Status::Ok || (i<3&&!(sensorMask_&(1u<<i)))) CM_TEXT(value,vc,"--"); else formatReal(value,vc,i==3?averageCache_:sensorCache_[i],1);
            return true;
        }
        uint16_t base=page==Page::RT?6:0; if(i<base) return false; i-=base;
        if(i<3) { static const char names[][8] CM_ROM={"tBase","tTarget","tDatum"}; CM_FMT(component,cc,"%s",flashText(names[i])); field=i==0?Field::Name:(i==1?Field::Target:Field::Datum); isText=i==0; }
        else if(i<6) {
            static const char names[][10] CM_ROM={"tPDate","tPour","tInitTemp"}; CM_FMT(component,cc,"%s",flashText(names[i-3]));
            if(i==5) { Real t; if(r.number(Key(kind,object,Field::InitialTemp),t)==Status::Ok) formatReal(value,vc,t,1); }
            else { uint64_t at; char date[12],clock[12]; if(r.time(Key(kind,object,Field::Start),at)==Status::Ok) { calendarText(at,date,sizeof(date),clock,sizeof(clock)); CM_FMT(value,vc,"%s",i==3?date:clock); } }
            return true;
        } else if(i<11) {
            static const char names[][9] CM_ROM={"tM","tFc","tPct","tElapsed","tRefDay"}; CM_FMT(component,cc,"%s",flashText(names[i-6]));
            Result result; Status s=page==Page::RT?app_.checkpointResult(kind,object,0,result):app_.readResult(kind,object,result);
            if(s!=Status::Ok) { CM_TEXT(value,vc,"--"); return true; }
            if(i==6) formatReal(value,vc,result.prediction.maturity,0);
            if(i==7) formatReal(value,vc,result.prediction.fc,1);
            if(i==8) { Real target; if(r.number(Key(kind,object,Field::Target),target)==Status::Ok) formatReal(value,vc,achievement(result.prediction.fc,target),0); }
            if(i==9) { uint64_t start; if(r.time(Key(kind,object,Field::Start),start)==Status::Ok) { uint64_t sec=(result.endMs-start)/1000; CM_FMT(value,vc,"%lu:%02u:%02u",(unsigned long)(sec/3600),unsigned(sec/60%60),unsigned(sec%60)); } }
            if(i==10) formatReal(value,vc,result.prediction.referenceDay,1);
            return true;
        } else {
            i-=11;
            if(page==Page::HistD&&i>=30) {
                uint8_t extra=uint8_t(i-30); if(extra>9) return false;
                static const char names[][9] CM_ROM={"tOp","tProj","tDate","tSavedAt","tLastT","tStatus","tS1","tS2","tS3","tCount"}; CM_FMT(component,cc,"%s",flashText(names[extra]));
                if(extra<3) { static const Field context[]={Field::Operator,Field::Project,Field::Date}; if(r.text(Key(kind,object,context[extra]),value,uint16_t(vc))!=Status::Ok) CM_TEXT(value,vc,"--"); }
                if(extra==3) { uint64_t at; char date[12],clock[12]; if(r.time(Key(kind,object,Field::Created),at)==Status::Ok) { calendarText(at,date,sizeof(date),clock,sizeof(clock)); CM_FMT(value,vc,"%s %s",date,clock); } else CM_TEXT(value,vc,"--"); }
                if(extra==4) { Result result; if(app_.readResult(kind,object,result)==Status::Ok) formatReal(value,vc,result.lastTemp,1); else CM_TEXT(value,vc,"--"); }
                if(extra==5) { uint32_t state; if(r.integer(Key(kind,object,Field::State),state)==Status::Ok&&state==uint32_t(SessionState::Completed)) CM_TEXT(value,vc,"COMPLETED"); else CM_TEXT(value,vc,"--"); }
                if(extra>=6&&extra<=8) { uint8_t frame[53]; uint16_t n=53; if(r.journal().get(Key(kind,object,Field::Sensors),frame,n)==Status::Ok&&n==53&&(frame[36]&(1u<<(extra-6)))) formatReal(value,vc,getReal(frame+12+8*(extra-6)),1); else CM_TEXT(value,vc,"--"); }
                if(extra==9) { uint32_t count; if(r.integer(Key(kind,object,Field::MaxRow),count)==Status::Ok) CM_FMT(value,vc,"%lu",(unsigned long)count); else CM_TEXT(value,vc,"--"); }
                return true;
            }
            if(page==Page::Str||i>=30) return false;
            uint8_t slot=uint8_t(i/5),col=uint8_t(i%5); Point p; Status s=app_.pointAt(slot,p);
            static const char names[][5] CM_ROM={"tDay","tAt","tTmp","tCm","tCf"}; CM_FMT(component,cc,"%s%u",flashText(names[col]),unsigned(slot));
            if(s!=Status::Ok) { CM_TEXT(value,vc,"--"); return true; }
            if(col==0) formatReal(value,vc,p.day,1);
            if(col==1) { char date[12],clock[12]; calendarText(p.atMs,date,sizeof(date),clock,sizeof(clock)); CM_FMT(value,vc,"%s %s",date,clock); }
            if(col==2) formatReal(value,vc,p.temp,1);
            if(col>=3) {
                Result result; Status metrics=app_.checkpointResult(kind,object,p.id,result);
                if(metrics!=Status::Ok) { CM_TEXT(value,vc,"--"); return true; }
                formatReal(value,vc,col==3?result.rawM:result.prediction.fc,col==3?0:1);
            }
            return true;
        }
    } else if(page==Page::Set) {
        if(i>6) return false;
        if(i>=4) { const Settings& s=app_.settings(); uint32_t v=i==4?s.intervalSeconds/3600:(i==5?s.intervalSeconds/60%60:s.intervalSeconds%60); CM_FMT(component,cc,"%s",i==4?"tHour":(i==5?"tMin":"tSec")); CM_FMT(value,vc,"%02u",unsigned(v)); return true; }
        static const char names[][10] CM_ROM={"tInterval","tBright","tSound","tAuto"}; CM_FMT(component,cc,"%s",flashText(names[i]));
        const Settings& s=app_.settings(); if(i==0) { CM_FMT(value,vc,"%02u:%02u:%02u",unsigned(s.intervalSeconds/3600),unsigned(s.intervalSeconds/60%60),unsigned(s.intervalSeconds%60)); return true; } CM_FMT(value,vc,"%lu",(unsigned long)(i==0?s.intervalSeconds:(i==1?s.brightness:(i==2?s.sound:s.autoSave)))); return true;
    } else if(page==Page::Dev) {
        if(i>2) return false;
        static const char names[][10] CM_ROM={"tVersion","tMcu","tProtocol"}; static const char values[][18] CM_ROM={"ConMT 1.0 schema1","ATmega328P","CM1 contract2"}; CM_FMT(component,cc,"%s",flashText(names[i])); CM_FMT(value,vc,"%s",flashText(values[i])); return true;
    } else return false;
    Status s;
    if(isText) s=r.text(Key(kind,object,field),value,uint16_t(vc));
    else { Real v; s=r.number(Key(kind,object,field),v); if(s==Status::Ok) formatReal(value,vc,v,digits); }
    if(s!=Status::Ok) CM_TEXT(value,vc,"--");
    return true;
}
void Transport::poll(uint32_t now) {
    Frame f;
    for(uint8_t i=0;i<48&&!ackPending_;++i) { int byte=uart_.read(); if(byte<0) break; Status st=parser_.feed(uint8_t(byte),now,f); if(st==Status::Ok) accept(f); }
    parser_.expire(now); flush(); if(txSize_) return;
    if(uint32_t(now-lastRefresh_)>=1000) { lastRefresh_=now; dirty_=true; }
    if(!dirty_&&!ackPending_&&viewSent_==app_.view()) return;
    if(phase_&&renderView_!=app_.view()) { phase_=0; field_=0; full_=true; }
    if(viewSent_!=app_.view()) full_=true;
    if(phase_==0) {
        renderView_=app_.view();
        if(app_.page()==Page::RT) { SensorFrame frame; Average avg; sensorStatus_=app_.getAverage(avg,&frame); sensorMask_=avg.mask; averageCache_=avg.operational; for(uint8_t i=0;i<3;++i) sensorCache_[i]=frame.channel[i]; }
        numeric("pInit.vRender",1); ++phase_; return;
    }
    if(phase_==1) { numeric("pInit.vBoot",app_.bootToken()); ++phase_; return; }
    if(phase_==2) {
        if(actualPage_!=uint8_t(app_.page())) {
            int n=CM_FMT(tx_,sizeof(tx_)-3,"page %u",unsigned(app_.page())); for(uint8_t i=0;i<3;++i) tx_[n+i]=char(255); txAt_=0; txSize_=uint8_t(n+3); actualPage_=uint8_t(app_.page());
        }
        ++phase_; return;
    }
    if(phase_==3) {
        char component[18],value[80];
        if((full_||field_<(app_.page()==Page::RT?9:3))&&renderField(field_,component,sizeof(component),value,sizeof(value))) { Status s=encode(component,value); if(s!=Status::Ok) ack_=s; ++field_; return; }
        ++phase_;
    }
    if(phase_==4) { numeric("pInit.vView",renderView_); ++phase_; return; }
    if(phase_==5) { numeric("pInit.vStatus",uint32_t(ack_)); ++phase_; return; }
    if(phase_==6) { if(ackPending_) numeric("pInit.vAckBoot",ackBoot_); ++phase_; return; }
    if(phase_==7) { if(ackPending_) { numeric("pInit.vAck",seq_); ackPending_=false; } ++phase_; return; }
    if(phase_==8) { numeric("pInit.vRender",0); ++phase_; return; }
    phase_=0; field_=0; dirty_=false; full_=false; ackPending_=false; viewSent_=renderView_;
}
}
