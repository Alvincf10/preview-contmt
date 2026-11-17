#include "Journal.h"
#include <string.h>
namespace conmt {
static void keyBytes(const Key& key,uint8_t* bytes) {
    bytes[0]=uint8_t(key.kind); bytes[1]=uint8_t(key.field);
    put32(bytes+2,key.object); put32(bytes+6,key.index);
}
static uint32_t checksum(const uint8_t* bytes,uint8_t size) { return crc32(0xffffffffUL,bytes,size)^0xffffffffUL; }
Status DiskIndex::reset(StoragePort* storage) {
    io_=storage; end_=512;
    if(!io_) return Status::Unsupported;
    Status st=io_->truncate(0); if(st!=Status::Ok) return st;
    uint8_t empty[8]={0}; put32(empty+4,checksum(empty,4));
    for(uint16_t slot=0;slot<512;slot+=8) { st=io_->write(slot,empty,8); if(st!=Status::Ok) return st; }
    return Status::Ok;
}
Status DiskIndex::root(const Key& key,uint32_t& slot,uint32_t& at) {
    if(!io_) return Status::Unsupported;
    uint8_t bytes[10]; keyBytes(key,bytes); slot=(checksum(bytes,10)&63)*8;
    Status st=io_->read(slot,bytes,8); if(st!=Status::Ok) return st;
    if(get32(bytes+4)!=checksum(bytes,4)) return Status::Corrupt;
    at=get32(bytes); return Status::Ok;
}
Status DiskIndex::node(uint32_t at,uint8_t* bytes) {
    if(at<512 || at>end_ || end_-at<26 || (at-512)%26) return Status::Corrupt;
    Status st=io_->read(at,bytes,26); if(st!=Status::Ok) return st;
    if(get32(bytes+22)!=checksum(bytes,22)) return Status::Corrupt;
    uint32_t next=get32(bytes+18);
    if(next && (next<512 || next>=at || (next-512)%26)) return Status::Corrupt;
    return Status::Ok;
}
Status DiskIndex::get(const Key& key,uint32_t& entry,uint32_t& transaction) {
    uint32_t slot,at; Status st=root(key,slot,at); if(st!=Status::Ok) return st;
    uint8_t wanted[10],bytes[26]; keyBytes(key,wanted);
    while(at) {
        st=node(at,bytes); if(st!=Status::Ok) return st;
        if(!memcmp(bytes,wanted,10)) { entry=get32(bytes+10); transaction=get32(bytes+14); return Status::Ok; }
        at=get32(bytes+18);
    }
    return Status::Missing;
}
Status DiskIndex::put(const Key& key,uint32_t entry,uint32_t transaction) {
    uint32_t slot,head; Status st=root(key,slot,head); if(st!=Status::Ok) return st;
    uint32_t at=head; uint8_t wanted[10],bytes[26]; keyBytes(key,wanted);
    while(at) {
        st=node(at,bytes); if(st!=Status::Ok) return st;
        if(!memcmp(wanted,bytes,10)) break;
        at=get32(bytes+18);
    }
    if(!at) {
        if(end_>UINT32_MAX-26) return Status::Capacity;
        memcpy(bytes,wanted,10); put32(bytes+18,head); at=end_;
    }
    put32(bytes+10,entry); put32(bytes+14,transaction); put32(bytes+22,checksum(bytes,22));
    st=io_->write(at,bytes,26); if(st!=Status::Ok) return st;
    if(at==end_) {
        end_+=26; put32(bytes,at); put32(bytes+4,checksum(bytes,4));
        st=io_->write(slot,bytes,8);
    }
    return st;
}
}
