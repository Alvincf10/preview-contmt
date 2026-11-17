#include "../core/Flash.h"
#include "Journal.h"
#include <string.h>
namespace conmt {
Key::Key(Kind k,uint32_t o,Field f,uint32_t i) : kind(k),object(o),field(f),index(i) {}
static Key operationKey(uint64_t operation) { return Key(Kind(0),uint32_t(operation>>32),Field(0),uint32_t(operation)); }
void put16(uint8_t* p,uint16_t n) { for(uint8_t i=0;i<2;++i) p[i]=uint8_t(n>>(i*8)); }
void put32(uint8_t* p,uint32_t n) { for(uint8_t i=0;i<4;++i) p[i]=uint8_t(n>>(i*8)); }
void put64(uint8_t* p,uint64_t n) { for(uint8_t i=0;i<8;++i) p[i]=uint8_t(n>>(i*8)); }
uint16_t get16(const uint8_t* p) { return uint16_t(p[0])|uint16_t(p[1])<<8; }
uint32_t get32(const uint8_t* p) { uint32_t n=0; for(uint8_t i=0;i<4;++i) n|=uint32_t(p[i])<<(8*i); return n; }
uint64_t get64(const uint8_t* p) { uint64_t n=0; for(uint8_t i=0;i<8;++i) n|=uint64_t(p[i])<<(8*i); return n; }
void putReal(uint8_t* bytes,Real value) {
    static_assert(sizeof(Real)==4||sizeof(Real)==8,"IEEE binary32/binary64 required");
    if(sizeof(Real)==8) {
        uint64_t bits=0; if(finite(value)) memcpy(&bits,&value,sizeof(Real));
        else if(signbit(value)) bits=1ULL<<63;
        put64(bytes,bits); return;
    }
    uint32_t bits=0; memcpy(&bits,&value,4);
    uint16_t exponent=uint16_t((bits>>23)&255); uint32_t fraction=bits&0x7fffffUL;
    memset(bytes,0,8); bytes[7]=uint8_t(bits>>24)&128;
    if(exponent==255||(!exponent&&!fraction)) return;
    if(exponent) exponent+=896;
    else {
        exponent=897;
        while(!(fraction&0x800000UL)) { fraction<<=1; --exponent; }
        fraction&=0x7fffffUL;
    }
    bytes[3]=uint8_t(fraction<<5); bytes[4]=uint8_t(fraction>>3); bytes[5]=uint8_t(fraction>>11);
    bytes[6]=uint8_t((fraction>>19)|(exponent<<4)); bytes[7]|=uint8_t(exponent>>4);
}
Real getReal(const uint8_t* bytes) {
    uint16_t exponent=(uint16_t(bytes[7]&127)<<4)|(bytes[6]>>4);
    if(exponent==2047) return NAN;
    if(sizeof(Real)==8) { uint64_t bits=get64(bytes); Real value; memcpy(&value,&bits,sizeof(Real)); return value; }
    uint32_t sign=uint32_t(bytes[7]&128)<<24, result=sign;
    int shift=1023+(-126)-int(exponent);
    if(exponent&&shift<=24) {
        uint32_t mantissa=0x800000UL|(uint32_t(bytes[6]&15)<<19)|(uint32_t(bytes[5])<<11)|(uint32_t(bytes[4])<<3)|(bytes[3]>>5);
        bool roundUp;
        if(shift>0) {
            uint32_t discarded=mantissa&((1UL<<shift)-1),half=1UL<<(shift-1);
            mantissa>>=shift;
            bool tail=(bytes[3]&31)||bytes[2]||bytes[1]||bytes[0];
            roundUp=discarded>half||(discarded==half&&(tail||(mantissa&1)));
            exponent=0;
        } else {
            roundUp=(bytes[3]&16)&&((bytes[3]&15)||bytes[2]||bytes[1]||bytes[0]||(mantissa&1));
            exponent-=896;
        }
        if(roundUp) ++mantissa;
        if(!exponent) result|=mantissa;
        else {
            if(mantissa==0x1000000UL) { mantissa>>=1; ++exponent; }
            result|=exponent>=255?0x7f800000UL:(uint32_t(exponent)<<23)|(mantissa&0x7fffffUL);
        }
    }
    Real value; memcpy(&value,&result,4); return value;
}
Status Journal::verify(uint32_t at,uint32_t limit,uint32_t& next,uint32_t& seq,uint64_t& op,bool footer) {
    if(at>limit || limit-at<32) return Status::Corrupt;
    uint8_t h[32]; Status s=io_.read(at,h,32); if(s!=Status::Ok) return s;
    if(memcmp(h,"CMT1",4)!=0) return Status::Corrupt;
    if((crc32(0xffffffffUL,h,28)^0xffffffffUL)!=get32(h+28)) return Status::Corrupt;
    if(get16(h+4)!=1 || get16(h+6)!=1) return Status::Version;
    uint32_t len=get32(h+20), records=get32(h+24);
    if(len>limit-at-32 || (footer && limit-at-32-len<8)) return Status::Corrupt;
    uint32_t pos=at+32, left=len, crc=0xffffffffUL, n=0;
    uint8_t scratch[32];
    while(left) {
        if(left<12) return Status::Corrupt;
        s=io_.read(pos,scratch,12); if(s!=Status::Ok) return s;
        if(!scratch[0] || !scratch[1]) return Status::Corrupt;
        uint16_t v=get16(scratch+10);
        if(v>MaxValue || uint32_t(v)+12>left) return Status::Corrupt;
        crc=crc32(crc,scratch,12); pos+=12; left-=12; ++n;
        while(v) {
            uint16_t chunk=v>32?32:v;
            s=io_.read(pos,scratch,chunk); if(s!=Status::Ok) return s;
            crc=crc32(crc,scratch,chunk); pos+=chunk; left-=chunk; v-=chunk;
        }
    }
    if(n!=records) return Status::Corrupt;
    if(footer) {
        s=io_.read(pos,scratch,8); if(s!=Status::Ok) return s;
        if(get32(scratch)!=(crc^0xffffffffUL)||memcmp(scratch+4,"DONE",4)!=0) return Status::Corrupt;
    } else if((crc^0xffffffffUL)!=(payloadCrc_^0xffffffffUL)) return Status::Corrupt;
    next=at+32+len+(footer?8:0); seq=get32(h+8); op=get64(h+12); return Status::Ok;
}
Status Journal::mount() {
    mounted_=false; Status st=scan();
    mounted_=st==Status::Ok; if(!mounted_) uncertain_=true;
    return st;
}
Status Journal::scan() {
    writing_=false; uncertain_=false; end_=sequence_=0; tail_=false;
    indexed_=false;
    Status open=io_.reopen(); if(open!=Status::Ok) return open;
    uint32_t size; Status st=io_.size(size); if(st!=Status::Ok) return st;
    indexed_=index_.reset(io_.indexStorage())==Status::Ok;
    while(end_<size) {
        uint32_t next,seq; uint64_t op;
        st=verify(end_,size,next,seq,op,true);
        if(st==Status::Version) return st;
        if(st==Status::Corrupt) {
            if(size-end_>=32) {
                uint8_t header[32]; Status read=io_.read(end_,header,32); if(read!=Status::Ok) return read;
                if(memcmp(header,"CMT1",4)==0) {
                    uint32_t length=get32(header+20);
                    bool validHeader=(crc32(0xffffffffUL,header,28)^0xffffffffUL)==get32(header+28);
                    if(size-end_>=40&&length<=size-end_-40) {
                        uint32_t complete=end_+40+length;
                        uint8_t footer[8]; read=io_.read(complete-8,footer,8); if(read!=Status::Ok) return read;
                        if((validHeader&&complete<size)||(memcmp(footer+4,"DONE",4)==0&&(validHeader||complete==size))) return Status::Corrupt;
                    }
                }
            }
            tail_=true; break;
        }
        if(st!=Status::Ok) return st;
        if(seq!=sequence_+1) return Status::Corrupt;
        if(indexed_ && indexTransaction(end_,next)!=Status::Ok) indexed_=false;
        end_=next; sequence_=seq;
    }
    return Status::Ok;
}
Status Journal::indexTransaction(uint32_t at,uint32_t next) {
    uint8_t bytes[12];
    for(uint32_t pos=at+32;pos<next-8;) {
        Status st=io_.read(pos,bytes,12); if(st!=Status::Ok) return st;
        Key key(Kind(bytes[0]),get32(bytes+2),Field(bytes[1]),get32(bytes+6));
        uint16_t size=get16(bytes+10);
        if(size>MaxValue || next-8-pos<12 || size>next-8-pos-12) return Status::Corrupt;
        st=index_.put(key,pos,at); if(st!=Status::Ok) return st;
        pos+=12+size;
    }
    if(next>at+40) {
        Status st=io_.read(at+12,bytes,8); if(st!=Status::Ok) return st;
        uint64_t operation=get64(bytes);
        if(operation) return index_.put(operationKey(operation),at+32,at);
    }
    return Status::Ok;
}
Status Journal::begin(uint64_t op) {
    if(!mounted_) return Status::Invalid;
    if(writing_) return Status::Busy;
    if(uncertain_) return Status::IoError;
    if(sequence_==UINT32_MAX || end_>UINT32_MAX-4096) return Status::Capacity;
    if(op) { Key k; Status st=findOperation(op,k); if(st==Status::Ok) return Status::Conflict; if(st!=Status::Missing) return st; }
    Status st=io_.truncate(end_); if(st!=Status::Ok) return st;
    uint8_t h[32]={0}; st=io_.write(end_,h,32); if(st!=Status::Ok) return st;
    writing_=true; writeAt_=end_+32; payloadCrc_=0xffffffffUL; count_=0; operation_=op; return Status::Ok;
}
Status Journal::put(const Key& k,const uint8_t* value,uint16_t n) {
    if(!writing_) return Status::Invalid;
    if(!uint8_t(k.kind) || !uint8_t(k.field)) return Status::Invalid;
    if(n>MaxValue || (n && !value) || writeAt_>UINT32_MAX-uint32_t(n)-20) return Status::Capacity;
    uint8_t h[12]; h[0]=uint8_t(k.kind); h[1]=uint8_t(k.field); put32(h+2,k.object); put32(h+6,k.index); put16(h+10,n);
    Status st=io_.write(writeAt_,h,12); if(st!=Status::Ok) { abort(); return st; }
    payloadCrc_=crc32(payloadCrc_,h,12); writeAt_+=12;
    if(n) { st=io_.write(writeAt_,value,n); if(st!=Status::Ok) { abort(); return st; } payloadCrc_=crc32(payloadCrc_,value,n); writeAt_+=n; }
    ++count_; return Status::Ok;
}
Status Journal::commit() {
    if(!writing_) return Status::Invalid;
    uint8_t h[32]; memcpy(h,"CMT1",4); put16(h+4,1); put16(h+6,1); put32(h+8,sequence_+1);
    put64(h+12,operation_); put32(h+20,writeAt_-end_-32); put32(h+24,count_); put32(h+28,crc32(0xffffffffUL,h,28)^0xffffffffUL);
    Status st=io_.write(end_,h,32);
    if(st==Status::Ok) st=io_.sync();
    uint32_t next=0,seq=0; uint64_t op;
    if(st==Status::Ok) st=verify(end_,writeAt_,next,seq,op,false);
    if(st==Status::Ok) {
        put32(h,payloadCrc_^0xffffffffUL); memcpy(h+4,"DONE",4);
        st=io_.write(writeAt_,h,8);
    }
    if(st==Status::Ok) st=io_.sync();
    if(st==Status::Ok) st=verify(end_,writeAt_+8,next,seq,op,true);
    writing_=false; uncertain_=st!=Status::Ok;
    if(st==Status::Ok) {
        if(indexed_ && indexTransaction(end_,next)!=Status::Ok) indexed_=false;
        end_=next; sequence_=seq; tail_=false;
    }
    return st;
}
Status Journal::get(const Key& wanted,uint8_t* out,uint16_t& capacity) {
    uint32_t at; uint16_t size;
    Status st=locate(wanted,at,size); if(st!=Status::Ok) return st;
    if(capacity<size) return Status::Capacity;
    capacity=size; return io_.read(at,out,size);
}
Status Journal::locate(const Key& wanted,uint32_t& valueAt,uint16_t& valueLength) {
    if(!uint8_t(wanted.kind) || !uint8_t(wanted.field)) return Status::Invalid;
    if(indexed_) {
        uint32_t entry,transaction; Status st=index_.get(wanted,entry,transaction);
        if(st==Status::Missing) return st;
        if(st==Status::Ok && transaction<end_ && entry>=transaction && entry-transaction>=32) {
            uint32_t next,seq; uint64_t op;
            st=verify(transaction,end_,next,seq,op,true);
            if(st!=Status::Ok) return st;
            uint8_t bytes[12];
            if(entry<=next-8 && next-8-entry>=12) {
                st=io_.read(entry,bytes,12); if(st!=Status::Ok) return st;
                Key found(Kind(bytes[0]),get32(bytes+2),Field(bytes[1]),get32(bytes+6));
                uint16_t size=get16(bytes+10);
                if(found==wanted && size<=MaxValue && size<=next-8-entry-12) {
                    if(!size) return Status::Missing;
                    valueAt=entry+12; valueLength=size; return Status::Ok;
                }
            }
        }
        indexed_=false;
    }
    bool found=false; valueLength=0; valueAt=0;
    for(uint32_t at=0;at<end_;) {
        uint32_t verifiedEnd,verifiedSeq; uint64_t verifiedOp;
        Status verified=verify(at,end_,verifiedEnd,verifiedSeq,verifiedOp,true); if(verified!=Status::Ok) return verified;
        uint8_t h[32]; Status s=io_.read(at,h,32); if(s!=Status::Ok) return s;
        uint32_t until=at+32+get32(h+20);
        if(until>end_ || until<at+32) return Status::Corrupt;
        for(uint32_t p=at+32;p<until;) {
            s=io_.read(p,h,12); if(s!=Status::Ok) return s;
            uint16_t len=get16(h+10); if(len>MaxValue || len>until-p-12) return Status::Corrupt;
            Key k(Kind(h[0]),get32(h+2),Field(h[1]),get32(h+6));
            if(k==wanted) { found=len!=0; valueAt=p+12; valueLength=len; }
            p+=12+len;
        }
        at=until+8;
    }
    if(!found) return Status::Missing;
    return Status::Ok;
}
Status Journal::copy(const Key& from,const Key& to,uint16_t expected) {
    if(!writing_) return Status::Invalid;
    if(!uint8_t(to.kind) || !uint8_t(to.field)) return Status::Invalid;
    uint32_t at; uint16_t size; Status st=locate(from,at,size); if(st!=Status::Ok) return st;
    if(expected&&size!=expected) return Status::Corrupt;
    if(writeAt_>UINT32_MAX-uint32_t(size)-20) return Status::Capacity;
    uint8_t bytes[32]; bytes[0]=uint8_t(to.kind); bytes[1]=uint8_t(to.field);
    put32(bytes+2,to.object); put32(bytes+6,to.index); put16(bytes+10,size);
    st=io_.write(writeAt_,bytes,12); if(st!=Status::Ok) { abort(); return st; }
    payloadCrc_=crc32(payloadCrc_,bytes,12); writeAt_+=12;
    while(size) {
        uint16_t chunk=size>32?32:size;
        st=io_.read(at,bytes,chunk);
        if(st==Status::Ok) st=io_.write(writeAt_,bytes,chunk);
        if(st!=Status::Ok) { abort(); return st; }
        payloadCrc_=crc32(payloadCrc_,bytes,chunk); writeAt_+=chunk; at+=chunk; size-=chunk;
    }
    ++count_; return Status::Ok;
}
Status Journal::findOperation(uint64_t op,Key& first) {
    if(!op) return Status::Missing;
    if(indexed_) {
        uint32_t entry,transaction; Status st=index_.get(operationKey(op),entry,transaction);
        if(st==Status::Missing) return st;
        if(st==Status::Ok && transaction<end_ && end_-transaction>=40 && entry==transaction+32) {
            uint32_t next,seq; uint64_t saved;
            st=verify(transaction,end_,next,seq,saved,true); if(st!=Status::Ok) return st;
            if(saved==op && next-entry>=20) {
                uint8_t bytes[12]; st=io_.read(entry,bytes,12); if(st!=Status::Ok) return st;
                first=Key(Kind(bytes[0]),get32(bytes+2),Field(bytes[1]),get32(bytes+6)); return Status::Ok;
            }
        }
        indexed_=false;
    }
    for(uint32_t at=0;at<end_;) {
        uint32_t verifiedEnd,verifiedSeq; uint64_t verifiedOp;
        Status verified=verify(at,end_,verifiedEnd,verifiedSeq,verifiedOp,true); if(verified!=Status::Ok) return verified;
        uint8_t h[32]; Status st=io_.read(at,h,32); if(st!=Status::Ok) return st;
        if(get64(h+12)==op && get32(h+24)>0) {
            st=io_.read(at+32,h,12); if(st!=Status::Ok) return st;
            first=Key(Kind(h[0]),get32(h+2),Field(h[1]),get32(h+6)); return Status::Ok;
        }
        uint32_t next=at+40+get32(h+20); if(next<=at || next>end_) return Status::Corrupt; at=next;
    }
    return Status::Missing;
}
Status Journal::maxObject(Kind kind,uint32_t& out) {
    out=0;
    for(uint32_t at=0;at<end_;) {
        uint32_t verifiedEnd,verifiedSeq; uint64_t verifiedOp;
        Status verified=verify(at,end_,verifiedEnd,verifiedSeq,verifiedOp,true); if(verified!=Status::Ok) return verified;
        uint8_t h[32]; Status st=io_.read(at,h,32); if(st!=Status::Ok) return st;
        uint32_t until=at+32+get32(h+20);
        if(until>end_ || until<at+32) return Status::Corrupt;
        for(uint32_t p=at+32;p<until;) {
            st=io_.read(p,h,12); if(st!=Status::Ok) return st;
            uint16_t n=get16(h+10); if(n>MaxValue || n>until-p-12) return Status::Corrupt;
            if(h[0]==uint8_t(kind) && get32(h+2)>out) out=get32(h+2);
            p+=12+n;
        }
        at=until+8;
    }
    return Status::Ok;
}
}
