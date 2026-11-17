#include "HostPorts.h"
#include "storage/Repository.h"
#include <iostream>
#include <cstdlib>
#include <unistd.h>
using namespace conmt;
#define REQUIRE(x) do { if(!(x)) { std::cerr<<__LINE__<<" "<<#x<<'\n'; std::exit(1); } } while(0)
#define OK(x) REQUIRE((x)==Status::Ok)
int main() {
    host::MemoryStorage media,sidecar; media.sidecar=&sidecar;
    Journal journal(media); Repository repo(journal); OK(journal.mount()); REQUIRE(journal.indexed());
    for(unsigned round=0;round<4;++round) {
        OK(journal.begin());
        for(unsigned i=1;i<=200;++i) OK(repo.putInteger(Key(Kind::Baseline,i,Field::Target),round*1000+i));
        OK(journal.commit());
    }
    uint32_t value; media.readCalls=media.readBytes=0;
    for(unsigned i=1;i<=200;++i) { OK(repo.integer(Key(Kind::Baseline,i,Field::Target),value)); REQUIRE(value==3000+i); }
    auto indexedBytes=media.readBytes+sidecar.readBytes;
    media.sidecar=nullptr; Journal scan(media); Repository slow(scan); OK(scan.mount());media.readBytes=0;
    for(unsigned i=1;i<=200;++i) { OK(slow.integer(Key(Kind::Baseline,i,Field::Target),value)); REQUIRE(value==3000+i); }
    REQUIRE(media.readBytes>indexedBytes*3);
    std::cout<<"indexed bytes="<<indexedBytes<<" full-scan bytes="<<media.readBytes<<'\n';
    media.sidecar=&sidecar; Journal reopened(media); Repository r(reopened); OK(reopened.mount()); REQUIRE(reopened.indexed());
    OK(reopened.begin()); OK(reopened.erase(Key(Kind::Baseline,1,Field::Target))); OK(reopened.commit());
    REQUIRE(r.integer(Key(Kind::Baseline,1,Field::Target),value)==Status::Missing);
    auto authoritative=media.bytes;
    sidecar.bytes.assign(22,0xff); Journal rebuilt(media);Repository rr(rebuilt);OK(rebuilt.mount());REQUIRE(rebuilt.indexed());
    OK(rr.integer(Key(Kind::Baseline,200,Field::Target),value));REQUIRE(value==3200&&media.bytes==authoritative);
    sidecar.full=true;OK(rebuilt.begin());OK(rr.putInteger(Key(Kind::Baseline,200,Field::Target),999));OK(rebuilt.commit());REQUIRE(!rebuilt.indexed());
    OK(rr.integer(Key(Kind::Baseline,200,Field::Target),value));REQUIRE(value==999);sidecar.full=false;
    Journal refresh(media);Repository final(refresh);OK(refresh.mount());REQUIRE(refresh.indexed());
    sidecar.bytes.assign(sidecar.bytes.size(),0xff);OK(final.integer(Key(Kind::Baseline,200,Field::Target),value));REQUIRE(value==999&&!refresh.indexed());
    for(int cut=0;cut<40;++cut) {
        host::MemoryStorage m,idx;m.sidecar=&idx;Journal j(m);Repository r2(j);OK(j.mount());
        idx.writeBudget=cut;OK(j.begin());OK(r2.putInteger(Key(Kind::Baseline,1,Field::Target),73));OK(j.commit());
        OK(r2.integer(Key(Kind::Baseline,1,Field::Target),value));REQUIRE(value==73);
        idx.writeBudget=-1;Journal reboot(m);Repository recovered(reboot);OK(reboot.mount());REQUIRE(reboot.indexed());
        OK(recovered.integer(Key(Kind::Baseline,1,Field::Target),value));REQUIRE(value==73);
    }
    {
        host::MemoryStorage source;Journal seed(source);OK(seed.mount());OK(seed.begin());
        uint8_t bytes[128];for(unsigned i=0;i<128;++i)bytes[i]=uint8_t(i);
        for(unsigned i=1;i<=3;++i)OK(seed.put(Key(Kind::Draft,1,Field::Name,i),bytes,128));OK(seed.commit());
        auto original=source.bytes;
        for(int cut=0;cut<500;++cut) {
            host::MemoryStorage m,idx;m.bytes=original;m.sidecar=&idx;Journal j(m);OK(j.mount());m.writeBudget=cut;
            Status st=j.begin();for(unsigned i=1;i<=3&&st==Status::Ok;++i)st=j.copy(Key(Kind::Draft,1,Field::Name,i),Key(Kind::Baseline,1,Field::Name,i),128);
            if(st==Status::Ok)st=j.commit();m.writeBudget=-1;Journal reboot(m);OK(reboot.mount());
            unsigned found=0;for(unsigned i=1;i<=3;++i){uint8_t actual[128];uint16_t n=128;Status got=reboot.get(Key(Kind::Baseline,1,Field::Name,i),actual,n);REQUIRE(got==Status::Ok||got==Status::Missing);if(got==Status::Ok){++found;REQUIRE(n==128);for(unsigned k=0;k<128;++k)REQUIRE(actual[k]==bytes[k]);}}
            REQUIRE(found==0||found==3);if(st==Status::Ok)REQUIRE(found==3);
        }
    }
    const auto committed=media.bytes;
    for(int cut=0;cut<100;++cut) {
        host::MemoryStorage m,idx;m.bytes=committed;m.sidecar=&idx;Journal j(m);Repository r2(j);OK(j.mount());m.writeBudget=cut;
        Status st=j.begin();if(st==Status::Ok)st=r2.putInteger(Key(Kind::Baseline,200,Field::Target),123);if(st==Status::Ok)st=j.commit();
        m.writeBudget=-1;Journal reboot(m);Repository recovered(reboot);OK(reboot.mount());OK(recovered.integer(Key(Kind::Baseline,200,Field::Target),value));REQUIRE(value==999||value==123);
    }
    char path[]="/private/tmp/conmt-index-XXXXXX";int fd=mkstemp(path);REQUIRE(fd>=0);close(fd);
    { host::FileStorage file(path); Journal j(file);Repository r2(j);OK(j.mount());REQUIRE(j.indexed());OK(j.begin());OK(r2.putInteger(Key(Kind::User,0,Field::Target),35));OK(j.commit()); }
    unlink((std::string(path)+".idx").c_str());
    { host::FileStorage file(path); Journal j(file);Repository r2(j);OK(j.mount());REQUIRE(j.indexed());OK(r2.integer(Key(Kind::User,0,Field::Target),value));REQUIRE(value==35); }
    unlink(path);unlink((std::string(path)+".idx").c_str());
    std::cout<<"Disk index collisions, updates, tombstone, rebuild, loss/full/corruption fallback, interrupted commit and real-file restart PASS\n";
}
