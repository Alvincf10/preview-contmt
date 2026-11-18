#include "Journal.h"
#include <string.h>
namespace conmt {
static uint32_t checksum(const uint8_t* bytes,uint8_t size) { return crc32(0xffffffffUL,bytes,size)^0xffffffffUL; }
Status DiskIndex::reset(StoragePort* storage) {
    io_=storage; end_=512;
    if(!io_) return Status::Unsupported;
    Status st=io_->truncate(0); if(st!=Status::Ok) return st;
    uint8_t empty[8]={0}; put32(empty+4,checksum(empty,4));
    for(uint16_t slot=0;slot<512;slot+=8) { st=io_->write(slot,empty,8); if(st!=Status::Ok) return st; }
    return Status::Ok;
}
Status DiskIndex::node(uint32_t at,uint8_t* bytes) {
    if(at<512 || at>end_ || end_-at<26 || (at-512)%26) return Status::Corrupt;
    Status st=io_->read(at,bytes,26); if(st!=Status::Ok) return st;
    if(get32(bytes+22)!=checksum(bytes,22)) return Status::Corrupt;
    uint32_t next=get32(bytes+18);
    if(next && (next<512 || next>=at || (next-512)%26)) return Status::Corrupt;
    return Status::Ok;
}
Status DiskIndex::find(const uint8_t* key,Search& s) {
    if(!io_) return Status::Unsupported;
    s.slot=(checksum(key,KeyBytes)&63)*8;
    Status st=io_->read(s.slot,s.bytes,8);
    if(st!=Status::Ok) return st;
    if(get32(s.bytes+4)!=checksum(s.bytes,4)) return Status::Corrupt;
    s.head=get32(s.bytes);
    s.position=s.head;
    while(s.position) {
        st=node(s.position,s.bytes);
        if(st!=Status::Ok) return st;
        if(!memcmp(s.bytes,key,KeyBytes)) return Status::Ok;
        s.position=get32(s.bytes+18);
    }
    return Status::Missing;
}
Status DiskIndex::get(const uint8_t* key,uint32_t& entry,uint32_t& transaction) {
    Search s;
    Status st=find(key,s);
    if(st==Status::Ok) {
        entry=get32(s.bytes+10);
        transaction=get32(s.bytes+14);
    }
    return st;
}
Status DiskIndex::put(const uint8_t* key,uint32_t entry,uint32_t transaction) {
    Search s;
    Status st=find(key,s);
    if(st==Status::Missing) {
        if(end_>UINT32_MAX-26) return Status::Capacity;
        memcpy(s.bytes,key,KeyBytes);
        put32(s.bytes+18,s.head);
        s.position=end_;
    } else if(st!=Status::Ok) {
        return st;
    }
    put32(s.bytes+10,entry);
    put32(s.bytes+14,transaction);
    put32(s.bytes+22,checksum(s.bytes,22));
    st=io_->write(s.position,s.bytes,26);
    if(st!=Status::Ok) return st;
    if(s.position==end_) {
        end_+=26;
        put32(s.bytes,s.position);
        put32(s.bytes+4,checksum(s.bytes,4));
        st=io_->write(s.slot,s.bytes,8);
    }
    return st;
}
}
