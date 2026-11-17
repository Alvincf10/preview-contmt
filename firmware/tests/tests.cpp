#include "app/Controller.h"
#include "HostPorts.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
using namespace conmt;
#define CHECK(x) do { if(!(x)) { std::cerr<<__FILE__<<":"<<__LINE__<<" "<<#x<<"\n"; std::exit(1); } } while(0)
int main() {
    CHECK(fabs(interval(36,Real(36.97),-20,Real(.5))-Real(28.2425))<Real(.0001));
    Accumulator acc; CHECK(acc.add(0,10,0)==Status::Ok); CHECK(acc.add(1,10,0)==Status::Ok); CHECK(acc.add(2,-18,0)==Status::Ok); CHECK(acc.maturity()==6); CHECK(acc.add(3,-18,0)==Status::Ok); CHECK(acc.maturity()==0);
    Real parsed=0; CHECK(parseReal("36.5",parsed)==Status::Ok&&parsed==Real(36.5)); CHECK(parseReal("36,5",parsed)==Status::Invalid); CHECK(parseReal("",parsed)==Status::Missing);
    uint64_t date; CHECK(parseDate("2026-02-30",date)==Status::Invalid); CHECK(parseDate("2024-02-29",date)==Status::Ok);
    CHECK(clockToHours(23*3600+30*60,0,0,parsed)==Status::Ok&&parsed==Real(.5));
    host::MemoryStorage io; Journal j(io); Repository r(j); CHECK(j.mount()==Status::Ok);
    CHECK(j.begin(1)==Status::Ok); CHECK(r.putNumber(Key(Kind::Draft,1,Field::Target),Real(36.55))==Status::Ok); CHECK(j.commit()==Status::Ok);
    CHECK(r.number(Key(Kind::Draft,1,Field::Target),parsed)==Status::Ok&&parsed==Real(36.55));
    CHECK(j.begin(1)==Status::Conflict);
    std::cout<<"domain and journal PASS\n";
}
