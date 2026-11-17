#include "../core/Flash.h"
#include "Repository.h"
#include "RecordCodec.h"
#include <string.h>
namespace conmt {
Status Record::number(Field f,Real& out) { return repo_.number(field(f),out); }
Status Record::integer(Field f,uint32_t& out) { return repo_.integer(field(f),out); }
Status Record::time(Field f,uint64_t& out) { return repo_.time(field(f),out); }
Status Record::text(Field f,char* out,uint16_t capacity) { return repo_.text(field(f),out,capacity); }
Status Record::putNumber(Field f,Real value) { return repo_.putNumber(field(f),value); }
Status Record::putInteger(Field f,uint32_t value) { return repo_.putInteger(field(f),value); }
Status Record::putTime(Field f,uint64_t value) { return repo_.putTime(field(f),value); }
Status Record::putText(Field f,const char* value,uint16_t capacity) { return repo_.putText(field(f),value,capacity); }
Status Record::erase(Field f) { return repo_.journal().erase(field(f)); }
Status Record::get(Field f,uint8_t* out,uint16_t& size) { return repo_.journal().get(field(f),out,size); }
Status Record::put(Field f,const uint8_t* value,uint16_t size) { return repo_.journal().put(field(f),value,size); }
Status Repository::number(const Key& k,Real& v) {
    uint8_t b[8]; uint16_t n=8; Status s=journal_.get(k,b,n); if(s!=Status::Ok) return s;
    if(n!=8) return Status::Corrupt;
    v=getReal(b); return finite(v)?Status::Ok:Status::Corrupt;
}
Status Repository::integer(const Key& k,uint32_t& v) {
    uint8_t b[4]; uint16_t n=4; Status s=journal_.get(k,b,n); if(s!=Status::Ok) return s;
    if(n!=4) return Status::Corrupt;
    v=get32(b); return Status::Ok;
}
Status Repository::time(const Key& k,uint64_t& v) {
    uint8_t b[8]; uint16_t n=8; Status s=journal_.get(k,b,n); if(s!=Status::Ok) return s;
    if(n!=8) return Status::Corrupt;
    v=get64(b); return Status::Ok;
}
Status Repository::text(const Key& k,char* v,uint16_t capacity) {
    if(!capacity) return Status::Capacity;
    uint16_t n=capacity-1; Status s=journal_.get(k,reinterpret_cast<uint8_t*>(v),n);
    if(s!=Status::Ok) { v[0]=0; return s; }
    v[n]=0; return safeText(v,capacity)?Status::Ok:Status::Corrupt;
}
Status Repository::putNumber(const Key& k,Real v) {
    if(!finite(v)) return Status::Invalid;
    uint8_t b[8]; putReal(b,v); return journal_.put(k,b,8);
}
Status Repository::putInteger(const Key& k,uint32_t v) { uint8_t b[4]; put32(b,v); return journal_.put(k,b,4); }
Status Repository::putTime(const Key& k,uint64_t v) { uint8_t b[8]; put64(b,v); return journal_.put(k,b,8); }
Status Repository::putText(const Key& k,const char* v,uint16_t cap) {
    if(!safeText(v,cap)) return Status::Invalid;
    if(!*v) return journal_.erase(k);
    return journal_.put(k,reinterpret_cast<const uint8_t*>(v),uint16_t(strlen(v)));
}
Status Repository::row(Kind k,uint32_t o,uint32_t id,Row& r) {
    Status s=readRecord(journal_,Key(k,o,Field::Row,id),RecordType::Row,&r); if(s!=Status::Ok) return s;
    r.id=id;
    if(!finite(r.day)||r.day<0||!finite(r.timeH)||r.timeH<0||(r.hasTemp&&!finite(r.temp))||(r.hasFc&&!finite(r.fc))) return Status::Corrupt;
    return Status::Ok;
}
Status Repository::putRow(Kind k,uint32_t o,const Row& r) {
    if(!r.id||!finite(r.day)||r.day<0||!finite(r.timeH)||r.timeH<0||(r.hasTemp&&!finite(r.temp))||(r.hasFc&&(!finite(r.fc)||r.fc<0))) return Status::Invalid;
    return writeRecord(journal_,Key(k,o,Field::Row,r.id),RecordType::Row,&r);
}
Status Repository::point(Kind k,uint32_t o,uint32_t id,Point& p) {
    Status s=readRecord(journal_,Key(k,o,Field::Row,id),RecordType::Point,&p); if(s!=Status::Ok) return s;
    if(uint8_t(p.source)>2||(p.validMask&~uint8_t(7))) return Status::Corrupt;
    p.id=id;
    return finite(p.day)&&p.day>=0&&finite(p.temp)?Status::Ok:Status::Corrupt;
}
Status Repository::putPoint(Kind k,uint32_t o,const Point& p) {
    if(!p.id||!finite(p.day)||p.day<0||!finite(p.temp)||(p.validMask&~uint8_t(7))||uint8_t(p.source)>2) return Status::Invalid;
    return writeRecord(journal_,Key(k,o,Field::Row,p.id),RecordType::Point,&p);
}
Status Repository::model(Kind k,uint32_t o,Fit& f) {
    Status s=readRecord(journal_,Key(k,o,Field::Model),RecordType::Model,&f); if(s!=Status::Ok) return s;
    f.valid=finite(f.a)&&finite(f.b)&&finite(f.r2)&&f.r2>=0&&f.r2<=1&&f.n>=2;
    return f.valid?Status::Ok:Status::NoModel;
}
Status Repository::putModel(Kind k,uint32_t o,const Fit& f) {
    if(!f.valid) return Status::NoModel;
    if(!finite(f.a)||!finite(f.b)||!finite(f.r2)||f.r2<0||f.r2>1||f.n<2) return Status::Invalid;
    return writeRecord(journal_,Key(k,o,Field::Model),RecordType::Model,&f);
}
Status Repository::result(Kind kind,uint32_t id,Result& r) {
    Status st=readRecord(journal_,Key(kind,id,Field::Result),RecordType::Result,&r); if(st!=Status::Ok) return st;
    if(r.rawM<0||r.prediction.maturity<0||r.prediction.fc<0||r.prediction.factor<=0||r.prediction.referenceDay<0) return Status::Corrupt;
    return finite(r.rawM)&&finite(r.prediction.maturity)&&finite(r.prediction.raw)&&finite(r.prediction.factor)&&finite(r.prediction.fc)&&finite(r.prediction.referenceDay)&&finite(r.initialTemp)&&finite(r.lastTemp)?Status::Ok:Status::Corrupt;
}
Status Repository::putResult(Kind kind,uint32_t id,const Result& result) {
    return writeRecord(journal_,Key(kind,id,Field::Result),RecordType::Result,&result);
}
Status Repository::putSensors(Kind k,uint32_t o,const SensorFrame& f,const Average& a,const Time& t,Field destination) {
    uint32_t age=t.monoMs-f.sampledMonoMs;
    if(!t.valid||t.wallMs<age) return Status::NoClock;
    if(!a.mask||(a.mask&~uint8_t(7))||(a.mask&~f.validMask)||!finite(a.raw)||!finite(a.operational)) return Status::Invalid;
    for(uint8_t i=0;i<3;++i) if((a.mask&(1u<<i))&&!finite(f.channel[i])) return Status::Invalid;
    Time sampled={f.sampledMonoMs,t.wallMs-age,true};
    Status st=journal_.startValue(Key(k,o,destination),53);
    if(st==Status::Ok) st=appendRecord(journal_,RecordType::SampleTime,&sampled);
    if(st==Status::Ok) st=appendRecord(journal_,RecordType::Channels,&f);
    if(st==Status::Ok) st=appendRecord(journal_,RecordType::Average,&a);
    return st;
}
Status Repository::copyScalar(const Key& from,const Key& to,uint16_t expected) {
    return journal_.copy(from,to,expected);
}
Status Repository::copy(Kind from,uint32_t src,Kind to,uint32_t dst) {
    for(uint8_t f=uint8_t(Field::Exists);f<=uint8_t(Field::ClockAdjustment);++f) {
        if(Field(f)==Field::Row||Field(f)==Field::DayInput||Field(f)==Field::TempInput||Field(f)==Field::FcInput) continue;
        Status s=journal_.copy(Key(from,src,Field(f)),Key(to,dst,Field(f)));
        if(s==Status::Missing) continue;
        if(s!=Status::Ok) return s;
    }
    uint32_t max=0; Status st=integer(Key(from,src,Field::MaxRow),max);
    if(st!=Status::Ok && st!=Status::Missing) return st;
    for(uint32_t i=1;i<=max;++i) {
        st=journal_.copy(Key(from,src,Field::Row,i),Key(to,dst,Field::Row,i));
        if(st==Status::Missing) continue;
        if(st!=Status::Ok) return st;
        if(from==Kind::Draft||from==Kind::Baseline) {
            for(uint8_t field=uint8_t(Field::DayInput);field<=uint8_t(Field::FcInput);++field) {
                st=journal_.copy(Key(from,src,Field(field),i),Key(to,dst,Field(field),i));
                if(st==Status::Missing) continue;
                if(st!=Status::Ok) return st;
            }
        }
    }
    return Status::Ok;
}
Status Repository::list(Kind k,uint32_t after,uint32_t& id) {
    uint32_t max=0; Status st=journal_.maxObject(k,max); if(st!=Status::Ok) return st;
    for(uint32_t i=after?(after>max?max:after-1):max;i;--i) {
        uint32_t exists=0; st=integer(Key(k,i,Field::Exists),exists);
        if(st==Status::Ok && exists) { id=i; return Status::Ok; }
        if(st!=Status::Missing && st!=Status::Ok) return st;
    }
    return Status::Missing;
}
StoredRows::StoredRows(Repository& r,Kind k,uint32_t o,bool displayOrder) : repo_(r),kind_(k),object_(o),max_(0),lastId_(0),lastH_(0),lastDay_(0),first_(true),displayOrder_(displayOrder) { reset(); }
void StoredRows::reset() { max_=0; lastId_=0; lastH_=lastDay_=0; first_=true; }
Status StoredRows::next(Row& out) {
    Status st=repo_.integer(Key(kind_,object_,Field::MaxRow),max_); if(st!=Status::Ok) return st;
    bool found=false; Row candidate;
    for(uint32_t id=1;id<=max_;++id) {
        Row r; st=repo_.row(kind_,object_,id,r); if(st==Status::Missing) continue;
        if(st!=Status::Ok) return st;
        if(!first_ && (displayOrder_&&r.day!=lastDay_?r.day<lastDay_:(r.timeH<lastH_ || (r.timeH==lastH_ && r.id<=lastId_)))) continue;
        if(!found || (displayOrder_&&r.day!=candidate.day?r.day<candidate.day:(r.timeH<candidate.timeH || (r.timeH==candidate.timeH && r.id<candidate.id)))) { candidate=r; found=true; }
    }
    if(!found) return Status::Missing;
    out=candidate; lastH_=out.timeH; lastDay_=out.day; lastId_=out.id; first_=false; return Status::Ok;
}
Status nextPoint(Repository& r,Kind k,uint32_t o,const Point* after,Point& out) {
    uint32_t max=0; Status st=r.integer(Key(k,o,Field::MaxRow),max); if(st!=Status::Ok) return st;
    bool found=false; Point candidate;
    for(uint32_t id=1;id<=max;++id) {
        Point p; st=r.point(k,o,id,p); if(st==Status::Missing) continue;
        if(st!=Status::Ok) return st;
        if(after && (p.atMs<after->atMs || (p.atMs==after->atMs && p.id<=after->id))) continue;
        if(!found || p.atMs<candidate.atMs || (p.atMs==candidate.atMs && p.id<candidate.id)) { candidate=p; found=true; }
    }
    if(!found) return Status::Missing;
    out=candidate; return Status::Ok;
}
Status replayPoints(Repository& r,Kind k,uint32_t o,Real datum,Real& m,Point& last) {
    Point p,previous; bool first=true; uint64_t start=0; Real lastDay=0;
    Accumulator acc; Status st;
    while((st=nextPoint(r,k,o,first?nullptr:&previous,p))==Status::Ok) {
        if(!first && p.day<lastDay) return Status::Invalid;
        if(first) start=p.atMs;
        st=acc.add(Real(p.atMs-start)/Real(3600000),p.temp,datum); if(st!=Status::Ok) return st;
        last=previous=p; lastDay=p.day; first=false;
    }
    m=acc.maturity(); return st==Status::Missing?(first?Status::Missing:Status::Ok):st;
}
}
