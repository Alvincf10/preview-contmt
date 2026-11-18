#include "../core/Flash.h"
#include "Transport.h"
#include "Presenter.h"
#include "../core/Command.h"
#include "../core/Text.h"
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
Transport::Transport(Controller& app,UartPort& uart) : app_(app),uart_(uart),componentSize_(0),valueSize_(0),txMode_(0),txSize_(0),txAt_(0),phase_(0),actualPage_(255),field_(0),seq_(0),ackBoot_(0),viewSent_(0),lastRefresh_(0),renderView_(0),lastRequestCrc_(0),lastOperation_(0),sensorCache_{0,0,0},averageCache_(0),sensorMask_(0),sensorStatus_(Status::NoSensor),lastAck_(Status::Ok),ack_(Status::Ok),dirty_(true),ackPending_(false),compatible_(false),full_(true),seenConnection_(false) {}
Status Transport::encode() {
    if(txSize_) return Status::Busy;
    if(!safeText(value_,sizeof(value_))) return Status::Invalid;
    componentSize_=uint8_t(strlen(component_)); valueSize_=uint8_t(strlen(value_)); txMode_=0;
    txAt_=0; txSize_=uint8_t(componentSize_+valueSize_+10); return Status::Ok;
}
Status Transport::numeric(const char* component,uint32_t value) {
    if(txSize_) return Status::Busy;
    copyFlash(component_,sizeof(component_),component);
    formatUnsigned(value_,sizeof(value_),value);
    componentSize_=uint8_t(strlen(component_)); valueSize_=uint8_t(strlen(value_)); txMode_=1;
    txAt_=0; txSize_=uint8_t(componentSize_+valueSize_+8); return Status::Ok;
}
void Transport::flush() {
    if(!txSize_) return;
    uint16_t n=uart_.writable(),remaining=uint16_t(txSize_-txAt_);
    if(n>remaining) n=remaining;
    uint8_t bytes[16]; if(n>sizeof(bytes)) n=sizeof(bytes); if(!n) return;
    static const char suffix[][7] CM_ROM={".txt=\"",".val="," "};
    uint8_t suffixSize=txMode_==0?6:(txMode_==1?5:1);
    for(uint8_t i=0;i<n;++i) {
        uint8_t at=uint8_t(txAt_+i);
        if(at<componentSize_) bytes[i]=uint8_t(component_[at]);
        else if((at-=componentSize_)<suffixSize) bytes[i]=uint8_t(flashValue(suffix[txMode_]+at));
        else if((at-=suffixSize)<valueSize_) bytes[i]=uint8_t(value_[at]);
        else bytes[i]=txMode_==0&&at==valueSize_?'\"':255;
    }
    uint16_t sent=uart_.write(bytes,n); if(sent>n) sent=n;
    txAt_+=uint8_t(sent); if(txAt_==txSize_) txAt_=txSize_=0;
}
static uint32_t requestCrc(const Frame& f) {
    uint32_t c=crc32(0xffffffffUL,reinterpret_cast<const uint8_t*>(f.verb),strlen(f.verb));
    for(uint8_t i=0;i<f.argc;++i) { const uint8_t separator='|'; c=crc32(c,&separator,1); c=crc32(c,reinterpret_cast<const uint8_t*>(f.args[i]),strlen(f.args[i])); }
    return c;
}
void Transport::accept(const Frame& f) {
    const Command command=commandFromText(f.verb);
    if((command==Command::PAGE_READY)) {
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
    else if(!validArguments(command,f.argc)) ack_=Status::Invalid;
    else if(operation&&operation==lastOperation_) ack_=fingerprint==lastRequestCrc_?lastAck_:Status::Conflict;
    else if(command==Command::STORAGE_RESCAN&&f.page==uint8_t(app_.page())&&f.seq) ack_=app_.boot();
    else {
        Status admission=Status::Ok;
        if(f.boot!=app_.bootToken()||!f.seq) admission=Status::Conflict;
        else if(f.page!=uint8_t(app_.page())||(f.view!=app_.view()&&!(command==Command::NAV&&CM_EQ(f.args[0],"BACK")))) admission=Status::Stale;
        bool canRetry=f.boot&&f.seq;
        ack_=canRetry||admission==Status::Ok?app_.dispatch(command,f.args,operation,admission,!canRetry):admission;
    }
    if(f.boot&&f.boot==app_.bootToken()) seenConnection_=true;
    if(operation) { lastOperation_=operation; lastRequestCrc_=fingerprint; lastAck_=ack_; }
    dirty_=full_=true; phase_=0; field_=0; ackPending_=true;
}
static void formatPanelTime(ClockPort& clock,char* value,size_t capacity,bool date) {
    const Time now=clock.now();
    if(!now.valid) CM_TEXT(value,capacity,"--");
    else if(date) calendarText(now.wallMs,value,capacity,nullptr,0);
    else calendarText(now.wallMs,nullptr,0,value,capacity);
}
bool Transport::renderField(uint16_t i,char* component,size_t cc,char* value,size_t vc) {
    value[0]=0;
    if(i==0) {
        formatPanelTime(app_.clock(),value,vc,false);
        CM_TEXT(component,cc,"tClock");
        return true;
    }
    if(i==1) { uint8_t battery; Status s=app_.devices().battery(battery); if(s==Status::Ok) Text(value,vc).number(battery).character('%'); else CM_TEXT(value,vc,"--"); CM_TEXT(component,cc,"tBatt"); return true; }
    if(i==2) { formatStatus(value,vc,ack_==Status::Ok?app_.status():ack_); CM_TEXT(component,cc,"tMsg"); return true; }
    i-=3;
    if(app_.page()==Page::RT) {
        if(i<4) {
            static const char names[][5] CM_ROM={"tS1","tS2","tS3","tAvg"}; copyFlash(component,cc,names[i]);
            if(sensorStatus_!=Status::Ok||(i<3&&!(sensorMask_&(1u<<i)))) CM_TEXT(value,vc,"--"); else formatReal(value,vc,i==3?averageCache_:sensorCache_[i],1);
            return true;
        }
        if(i<6) {
            const bool date=i==4;
            formatPanelTime(app_.clock(),value,vc,date);
            copyFlash(component,cc,date?CM_LITERAL("tNowD"):CM_LITERAL("tNowT"));
            return true;
        }
        i-=6;
    }
    Presenter presenter(app_); return presenter.field(i,component,cc,value,vc);
}
void Transport::receive(uint32_t now) {
    Frame f;
    for(uint8_t i=0;i<48&&!ackPending_;++i) { int byte=uart_.read(); if(byte<0) break; Status st=parser_.feed(uint8_t(byte),now,f); if(st==Status::Ok) accept(f); }
    parser_.expire(now);
}
bool Transport::renderNext() {
    if((full_||field_<(app_.page()==Page::RT?9:3))&&renderField(field_,component_,sizeof(component_),value_,sizeof(value_))) {
        Status st=encode(); if(st!=Status::Ok) ack_=st;
        ++field_; return true;
    }
    return false;
}

void Transport::poll(uint32_t now) {
    receive(now); flush(); if(txSize_) return;
    if(uint32_t(now-lastRefresh_)>=1000) { lastRefresh_=now; dirty_=true; }
    if(!dirty_&&!ackPending_&&viewSent_==app_.view()) return;
    if(phase_&&renderView_!=app_.view()) { phase_=0; field_=0; full_=true; }
    if(viewSent_!=app_.view()) full_=true;
    if(phase_==0) {
        renderView_=app_.view();
        if(app_.page()==Page::RT) { SensorFrame frame; Average avg; sensorStatus_=app_.getAverage(avg,&frame); sensorMask_=avg.mask; averageCache_=avg.operational; for(uint8_t i=0;i<3;++i) sensorCache_[i]=frame.channel[i]; }
        numeric(CM_LITERAL("pInit.vRender"),1); ++phase_; return;
    }
    if(phase_==1) { numeric(CM_LITERAL("pInit.vBoot"),app_.bootToken()); ++phase_; return; }
    if(phase_==2) {
        if(actualPage_!=uint8_t(app_.page())) {
            CM_COPY(component_,"page"); formatUnsigned(value_,sizeof(value_),uint8_t(app_.page()));
            componentSize_=4; valueSize_=uint8_t(strlen(value_)); txMode_=2; txAt_=0; txSize_=uint8_t(componentSize_+valueSize_+4); actualPage_=uint8_t(app_.page());
        }
        ++phase_; return;
    }
    if(phase_==3) {
        if(renderNext()) return;
        ++phase_;
    }
    if(phase_==4) { numeric(CM_LITERAL("pInit.vView"),renderView_); ++phase_; return; }
    if(phase_==5) { numeric(CM_LITERAL("pInit.vStatus"),uint32_t(ack_)); ++phase_; return; }
    if(phase_==6) { if(ackPending_) numeric(CM_LITERAL("pInit.vAckBoot"),ackBoot_); ++phase_; return; }
    if(phase_==7) { if(ackPending_) { numeric(CM_LITERAL("pInit.vAck"),seq_); ackPending_=false; } ++phase_; return; }
    if(phase_==8) { numeric(CM_LITERAL("pInit.vRender"),0); ++phase_; return; }
    phase_=0; field_=0; dirty_=false; full_=false; ackPending_=false; viewSent_=renderView_;
}
}
