#include "HostPorts.h"
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
namespace conmt { namespace host {
Status MemoryStorage::size(uint32_t& v) { if(absent) return Status::Absent; v=uint32_t(bytes.size()); return Status::Ok; }
Status MemoryStorage::read(uint32_t at,uint8_t* b,uint16_t n) { if(absent) return Status::Absent; if(uint64_t(at)+n>bytes.size()) return Status::IoError; std::copy(bytes.begin()+at,bytes.begin()+at+n,b); return Status::Ok; }
Status MemoryStorage::write(uint32_t at,const uint8_t* b,uint16_t n) {
    if(absent) return Status::Absent;
    if(full) return Status::Full;
    uint16_t done=writeBudget<0?n:uint16_t(std::min<int64_t>(n,writeBudget));
    if(uint64_t(at)+done>bytes.size()) bytes.resize(at+done);
    std::copy(b,b+done,bytes.begin()+at);
    if(writeBudget>=0) writeBudget-=done;
    return done==n?Status::Ok:Status::IoError;
}
Status MemoryStorage::truncate(uint32_t n) { if(absent) return Status::Absent; if(n>bytes.size()) return Status::IoError; bytes.resize(n); return Status::Ok; }
Status MemoryStorage::sync() { return absent?Status::Absent:(failSync?Status::IoError:Status::Ok); }
FileStorage::FileStorage(const std::string& p) : path_(p),fd_(::open(p.c_str(),O_RDWR|O_CREAT,0600)) {}
FileStorage::~FileStorage() { if(fd_>=0) ::close(fd_); }
Status FileStorage::size(uint32_t& v) { struct stat st; if(fstat(fd_,&st)) return Status::IoError; if(st.st_size>UINT32_MAX) return Status::Capacity; v=uint32_t(st.st_size); return Status::Ok; }
Status FileStorage::read(uint32_t at,uint8_t* b,uint16_t n) { return pread(fd_,b,n,at)==n?Status::Ok:Status::IoError; }
Status FileStorage::write(uint32_t at,const uint8_t* b,uint16_t n) { if(pwrite(fd_,b,n,at)==n) return Status::Ok; return errno==ENOSPC?Status::Full:Status::IoError; }
Status FileStorage::truncate(uint32_t n) { return ftruncate(fd_,n)==0?Status::Ok:Status::IoError; }
Status FileStorage::sync() { return fsync(fd_)==0?Status::Ok:Status::IoError; }
}}
