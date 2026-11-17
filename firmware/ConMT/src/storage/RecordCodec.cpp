#include "RecordCodec.h"
#include "../core/Flash.h"
namespace conmt {
namespace {
enum Wire : uint8_t { RealValue, Integer, TimeValue, Byte, Boolean, RowFlags };
struct Member { Wire type; uint8_t offset,extra; };
#define M(type,record,member) {type,offsetof(record,member),0}
static const Member row[] CM_ROM={M(Integer,Row,revision),M(RealValue,Row,day),M(RealValue,Row,timeH),M(RealValue,Row,temp),M(RealValue,Row,fc),{RowFlags,offsetof(Row,hasTemp),offsetof(Row,hasFc)}};
static const Member point[] CM_ROM={M(Integer,Point,revision),M(TimeValue,Point,atMs),M(RealValue,Point,day),M(RealValue,Point,temp),M(Byte,Point,validMask),M(Byte,Point,source)};
static const Member model[] CM_ROM={M(RealValue,Fit,a),M(RealValue,Fit,b),M(RealValue,Fit,r2),M(Integer,Fit,n)};
#define P(member) {RealValue,offsetof(Result,prediction)+offsetof(Prediction,member),0}
static const Member result[] CM_ROM={M(RealValue,Result,rawM),P(maturity),P(raw),P(factor),P(fc),P(referenceDay),M(TimeValue,Result,endMs),M(RealValue,Result,initialTemp),M(RealValue,Result,lastTemp),{Boolean,offsetof(Result,prediction)+offsetof(Prediction,hasReference),0}};
static const Member sampleTime[] CM_ROM={M(TimeValue,Time,wallMs),M(Integer,Time,monoMs)};
static const Member channels[] CM_ROM={{RealValue,offsetof(SensorFrame,channel),0},{RealValue,offsetof(SensorFrame,channel)+sizeof(Real),0},{RealValue,offsetof(SensorFrame,channel)+2*sizeof(Real),0}};
static const Member averageFields[] CM_ROM={M(Byte,Average,mask),M(RealValue,Average,raw),M(RealValue,Average,operational)};
#undef P
#undef M
struct Layout { const Member* members; uint8_t count,size; };
static const Layout layouts[] CM_ROM={{row,6,37},{point,6,30},{model,4,28},{result,10,73},{sampleTime,2,12},{channels,3,24},{averageFields,3,17}};
static_assert(sizeof(Row)<256&&sizeof(Point)<256&&sizeof(Fit)<256&&sizeof(Result)<256,"Record member offsets must fit uint8");
static_assert(sizeof(PointSource)==1,"Point source wire member is one byte");
static Status transfer(Journal& journal,ValueReader* reader,RecordType type,void* record) {
    if(uint8_t(type)>=sizeof(layouts)/sizeof(*layouts)||!record) return Status::Invalid;
    Layout layout=flashValue(layouts+uint8_t(type));
    Status st=Status::Ok;
    uint8_t bytes[8]; uint8_t* native=static_cast<uint8_t*>(record);
    for(uint8_t i=0;i<layout.count;++i) {
        Member member=flashValue(layout.members+i); uint8_t* value=native+member.offset;
        uint8_t size=member.type==RealValue||member.type==TimeValue?8:(member.type==Integer?4:1);
        if(!reader) {
            switch(member.type) {
                case RealValue: { Real v; memcpy(&v,value,sizeof(v)); putReal(bytes,v); break; }
                case Integer: { uint32_t v; memcpy(&v,value,4); put32(bytes,v); break; }
                case TimeValue: { uint64_t v; memcpy(&v,value,8); put64(bytes,v); break; }
                case Byte: bytes[0]=*value; break;
                case Boolean: bytes[0]=*reinterpret_cast<bool*>(value)?1:0; break;
                case RowFlags: bytes[0]=(*reinterpret_cast<bool*>(value)?1:0)|(*reinterpret_cast<bool*>(native+member.extra)?2:0); break;
            }
            st=journal.appendValue(bytes,size);
        } else {
            st=reader->read(bytes,size); if(st!=Status::Ok) return st;
            switch(member.type) {
                case RealValue: { Real v=getReal(bytes); memcpy(value,&v,sizeof(v)); break; }
                case Integer: { uint32_t v=get32(bytes); memcpy(value,&v,4); break; }
                case TimeValue: { uint64_t v=get64(bytes); memcpy(value,&v,8); break; }
                case Byte: *value=bytes[0]; break;
                case Boolean: if(bytes[0]>1) return Status::Corrupt; *reinterpret_cast<bool*>(value)=bytes[0]!=0; break;
                case RowFlags:
                    if(bytes[0]&~uint8_t(3)) return Status::Corrupt;
                    *reinterpret_cast<bool*>(value)=bytes[0]&1; *reinterpret_cast<bool*>(native+member.extra)=bytes[0]&2; break;
            }
        }
        if(st!=Status::Ok) return st;
    }
    return Status::Ok;
}
}
Status readRecord(Journal& journal,const Key& key,RecordType type,void* record) {
    if(uint8_t(type)>=sizeof(layouts)/sizeof(*layouts)) return Status::Invalid;
    ValueReader reader; Status st=journal.openValue(key,flashValue(layouts+uint8_t(type)).size,reader);
    return st==Status::Ok?transfer(journal,&reader,type,record):st;
}
Status writeRecord(Journal& journal,const Key& key,RecordType type,const void* record) {
    if(uint8_t(type)>=sizeof(layouts)/sizeof(*layouts)) return Status::Invalid;
    Status st=journal.startValue(key,flashValue(layouts+uint8_t(type)).size);
    return st==Status::Ok?appendRecord(journal,type,record):st;
}
Status appendRecord(Journal& journal,RecordType type,const void* record) { return transfer(journal,nullptr,type,const_cast<void*>(record)); }
}
