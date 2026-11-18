#include "../core/Flash.h"
#include "Journal.h"
#include <string.h>
namespace conmt {
Key::Key(Kind k,uint32_t o,Field f,uint32_t i) : kind(k),object(o),field(f),index(i) {}
static Key operationKey(const uint64_t& operation) { return Key(Kind(0),uint32_t(operation>>32),Field(0),uint32_t(operation)); }
static Key entryKey(const uint8_t* header) {
    return Key(Kind(header[0]),get32(header+2),Field(header[1]),get32(header+6));
}
static bool validEntryLength(uint16_t length,uint32_t available) {
    return length<=Journal::MaxValue && uint16_t(12+length)<=available;
}
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
inline __attribute__((always_inline)) Status Journal::readEntry(uint32_t at,uint32_t available,uint8_t* header,uint16_t& length) {
    if(available<12) return Status::Corrupt;
    Status st=io_.read(at,header,12);
    if(st!=Status::Ok) return st;
    length=get16(header+10);
    return validEntryLength(length,available)&&header[0]&&header[1]?Status::Ok:Status::Corrupt;
}
Status Journal::verify(uint32_t at,uint32_t limit,uint32_t& next,uint32_t& seq,uint64_t& op,bool footer) {
    if(at>limit || limit-at<32) return Status::Corrupt;
    uint8_t h[32]; Status s=io_.read(at,h,32); if(s!=Status::Ok) return s;
    if(memcmp(h,"CMT1",4)!=0) return Status::Corrupt;
    if((crc32(0xffffffffUL,h,28)^0xffffffffUL)!=get32(h+28)) return Status::Corrupt;
    if(get16(h+4)!=1 || get16(h+6)!=1) return Status::Version;
    uint32_t len=get32(h+20), records=get32(h+24);
    if(len>limit-at-32 || (footer && limit-at-32-len<8)) return Status::Corrupt;
    // Callers consume these provisional outputs only after Status::Ok.
    next=at+32+len+(footer?8:0); seq=get32(h+8); op=get64(h+12);
    uint32_t pos=at+32, left=len, crc=0xffffffffUL, n=0;
    while(left) {
        uint16_t v;
        s=readEntry(pos,left,h,v); if(s!=Status::Ok) return s;
        crc=crc32(crc,h,12); pos+=12; left-=12; ++n;
        while(v) {
            uint16_t chunk=v>32?32:v;
            s=io_.read(pos,h,chunk); if(s!=Status::Ok) return s;
            crc=crc32(crc,h,chunk); pos+=chunk; left-=chunk; v-=chunk;
        }
    }
    if(n!=records) return Status::Corrupt;
    if(footer) {
        s=io_.read(pos,h,8); if(s!=Status::Ok) return s;
        if(get32(h)!=(crc^0xffffffffUL)||memcmp(h+4,"DONE",4)!=0) return Status::Corrupt;
    } else if((crc^0xffffffffUL)!=(payloadCrc_^0xffffffffUL)) return Status::Corrupt;
    return Status::Ok;
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
        if(indexed_ && indexTransaction(end_,next,op)!=Status::Ok) indexed_=false;
        end_=next; sequence_=seq;
    }
    return Status::Ok;
}
Status Journal::indexTransaction(uint32_t at,uint32_t next,const uint64_t& operation) {
    uint8_t bytes[12];
    for(uint32_t pos=at+32;pos<next-8;) {
        uint16_t size;
        Status st=readEntry(pos,next-8-pos,bytes,size); if(st!=Status::Ok) return st;
        const Key key=entryKey(bytes);
        st=index_.put(key,pos,at); if(st!=Status::Ok) return st;
        Key maximum(Kind(0),uint8_t(key.kind),Field::Exists);
        uint32_t previous,transaction; st=index_.get(maximum,previous,transaction);
        bool replace=st==Status::Missing;
        if(st==Status::Ok) {
            if(previous<32||previous>pos||transaction>previous-32) return Status::Corrupt;
            uint8_t entry[6]; st=io_.read(previous,entry,sizeof(entry)); if(st!=Status::Ok) return st;
            if(entry[0]!=uint8_t(key.kind)) return Status::Corrupt;
            replace=key.object>get32(entry+2);
        } else if(!replace) return st;
        if(replace) { st=index_.put(maximum,pos,at); if(st!=Status::Ok) return st; }
        pos+=12+size;
    }
    if(next>at+40&&operation) return index_.put(operationKey(operation),at+32,at);
    return Status::Ok;
}
Status Journal::begin(const uint64_t& op) {
    if(!mounted_) return Status::Invalid;
    if(writing_) return Status::Busy;
    if(uncertain_) return Status::IoError;
    if(sequence_==UINT32_MAX || end_>UINT32_MAX-4096) return Status::Capacity;
    if(op) { Key k; Status st=findOperation(op,k); if(st==Status::Ok) return Status::Conflict; if(st!=Status::Missing) return st; }
    Status st=io_.truncate(end_); if(st!=Status::Ok) return st;
    uint8_t h[32]={0}; st=io_.write(end_,h,32); if(st!=Status::Ok) return st;
    writing_=true; remaining_=0; writeAt_=end_+32; payloadCrc_=0xffffffffUL; count_=0; operation_=op; return Status::Ok;
}
Status Journal::put(const Key& k,const uint8_t* value,uint16_t n) {
    if(n&&!value) return !writing_||!uint8_t(k.kind)||!uint8_t(k.field)?Status::Invalid:Status::Capacity;
    Status st=startValue(k,n);
    return st==Status::Ok?appendValue(value,n):st;
}
Status Journal::startValue(const Key& k,uint16_t n) {
    if(!writing_) return Status::Invalid;
    if(remaining_) return Status::Busy;
    if(!uint8_t(k.kind) || !uint8_t(k.field)) return Status::Invalid;
    if(n>MaxValue || writeAt_>UINT32_MAX-uint32_t(n)-20) return Status::Capacity;
    uint8_t h[12]; h[0]=uint8_t(k.kind); h[1]=uint8_t(k.field); put32(h+2,k.object); put32(h+6,k.index); put16(h+10,n);
    Status st=io_.write(writeAt_,h,12); if(st!=Status::Ok) { abort(); return st; }
    payloadCrc_=crc32(payloadCrc_,h,12); writeAt_+=12;
    remaining_=n; if(!n) ++count_;
    return Status::Ok;
}
Status Journal::appendValue(const uint8_t* bytes,uint16_t n) {
    if(!writing_) return Status::Invalid;
    if(n>remaining_ || (n&&!bytes)) { abort(); return Status::Capacity; }
    if(!n) return Status::Ok;
    Status st=io_.write(writeAt_,bytes,n); if(st!=Status::Ok) { abort(); return st; }
    payloadCrc_=crc32(payloadCrc_,bytes,n); writeAt_+=n; remaining_-=n;
    if(!remaining_) ++count_;
    return Status::Ok;
}
Status Journal::commit() {
    if(!writing_) return Status::Invalid;
    if(remaining_) { abort(); return Status::Invalid; }
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
        if(indexed_ && indexTransaction(end_,next,op)!=Status::Ok) indexed_=false;
        end_=next; sequence_=seq; tail_=false;
    }
    return st;
}
Status Journal::get(const Key& wanted,uint8_t* out,uint16_t& capacity) {
    ValueReader reader; Status st=openValue(wanted,0,reader); if(st!=Status::Ok) return st;
    if(capacity<reader.remaining()) return Status::Capacity;
    capacity=reader.remaining(); return reader.read(out,capacity);
}
Status Journal::openValue(const Key& wanted,uint16_t expected,ValueReader& reader) {
    reader=ValueReader(); uint32_t at; uint16_t size;
    Status st=locate(wanted,at,size); if(st!=Status::Ok) return st;
    if(expected&&size!=expected) return Status::Corrupt;
    reader.io_=&io_; reader.at_=at; reader.remaining_=size; return Status::Ok;
}
Status ValueReader::read(uint8_t* out,uint16_t size) {
    if(!io_) return Status::Invalid;
    if(size>remaining_ || (size&&!out)) return Status::Capacity;
    Status st=io_->read(at_,out,size);
    if(st!=Status::Ok) { io_=nullptr; return st; }
    at_+=size; remaining_-=size; return Status::Ok;
}
Status ValueReader::skip(uint16_t size) {
    if(!io_) return Status::Invalid;
    if(size>remaining_) return Status::Capacity;
    at_+=size; remaining_-=size; return Status::Ok;
}
Status Journal::locate(const Key& wanted,uint32_t& valueAt,uint16_t& valueLength) {
    if(!uint8_t(wanted.kind) || !uint8_t(wanted.field)) return Status::Invalid;
    Key key=wanted;
    return findEntry(Query::Value,key,valueAt,valueLength);
}
Status Journal::findEntry(Query mode,Key& wanted,uint32_t& valueAt,uint16_t& valueLength,const uint64_t* operation) {
    uint32_t transaction=0, entry=0;
    if(indexed_) {
        Key lookup=wanted;
        if(operation) lookup=operationKey(*operation);
        if(mode==Query::MaxObject) lookup=Key(Kind(0),uint8_t(wanted.kind),Field::Exists);
        Status st=index_.get(lookup,entry,transaction);
        if(st==Status::Missing) {
            if(mode!=Query::MaxObject) return st;
            valueAt=0;
            return Status::Ok;
        }
        if(st!=Status::Ok || transaction>=end_ || entry<transaction || entry-transaction<32 ||
           (mode!=Query::Value && end_-transaction<40) ||
           (mode==Query::Operation && entry-transaction!=32)) indexed_=false;
    }
    if(!indexed_) { transaction=0; valueAt=0; valueLength=0; }
    while(transaction<end_) {
        uint32_t next,seq;
        uint64_t saved;
        Status st=verify(transaction,end_,next,seq,saved,true);
        if(st!=Status::Ok) return st;
        const uint32_t limit=next-8;
        uint8_t bytes[12];
        if(indexed_) {
            if(entry<=limit && limit-entry>=12 && (!operation || saved==*operation)) {
                st=io_.read(entry,bytes,mode==Query::MaxObject?6:12);
                if(st!=Status::Ok) return st;
                if(mode==Query::MaxObject) {
                    if(bytes[0]==uint8_t(wanted.kind)) { valueAt=get32(bytes+2); return Status::Ok; }
                } else {
                    const Key found=entryKey(bytes);
                    if(mode==Query::Operation) { wanted=found; return Status::Ok; }
                    uint16_t size=get16(bytes+10);
                    if(found==wanted && validEntryLength(size,limit-entry)) {
                        if(!size) return Status::Missing;
                        valueAt=entry+12; valueLength=size; return Status::Ok;
                    }
                }
            }
            indexed_=false;
            transaction=0;
            valueAt=0;
            valueLength=0;
            continue;
        }
        if(!operation||saved==*operation) {
            for(uint32_t scan=transaction+32;scan<limit;) {
                uint16_t size;
                st=readEntry(scan,limit-scan,bytes,size); if(st!=Status::Ok) return st;
                const Key key=entryKey(bytes);
                if(mode==Query::Operation) { wanted=key; return Status::Ok; }
                if(mode==Query::MaxObject) { if(key.kind==wanted.kind&&key.object>valueAt) valueAt=key.object; }
                else if(key==wanted) { valueAt=scan+12; valueLength=size; }
                scan+=12+size;
            }
        }
        transaction=next;
    }
    return mode==Query::MaxObject||valueLength?Status::Ok:Status::Missing;
}

Status Journal::copy(const Key& from,const Key& to,uint16_t expected) {
    if(!writing_) return Status::Invalid;
    if(!uint8_t(to.kind) || !uint8_t(to.field)) return Status::Invalid;
    ValueReader reader; Status st=openValue(from,expected,reader); if(st!=Status::Ok) return st;
    st=startValue(to,reader.remaining()); if(st!=Status::Ok) return st;
    uint8_t bytes[32];
    while(reader.remaining()) {
        uint16_t chunk=reader.remaining()>32?32:reader.remaining();
        st=reader.read(bytes,chunk);
        if(st==Status::Ok) st=appendValue(bytes,chunk);
        if(st!=Status::Ok) { abort(); return st; }
    }
    return Status::Ok;
}
Status Journal::findOperation(const uint64_t& op,Key& first) {
    if(!op) return Status::Missing;
    uint32_t at; uint16_t length;
    return findEntry(Query::Operation,first,at,length,&op);
}
Status Journal::maxObject(Kind kind,uint32_t& out) {
    Key key(kind); uint16_t length;
    return findEntry(Query::MaxObject,key,out,length);
}
}
