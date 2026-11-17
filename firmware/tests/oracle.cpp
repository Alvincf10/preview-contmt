#include "core/Math.h"
#include <vector>
#include <iostream>
#include <iomanip>
using namespace conmt;
class Rows : public RowSource {
public:
    std::vector<Row> data; size_t i=0;
    void reset() override { i=0; }
    Status next(Row& r) override { if(i==data.size()) return Status::Missing; r=data[i++]; return Status::Ok; }
};
int main() {
    Rows rows; Real datum; size_t n; std::cin>>datum>>n;
    for(size_t i=0;i<n;++i) { Row r; r.id=uint32_t(i+1); std::cin>>r.day>>r.timeH>>r.temp>>r.fc; r.hasTemp=true; r.hasFc=r.fc>0; rows.data.push_back(r); }
    Fit f; if(fitRows(rows,datum,f)!=Status::Ok) return 1;
    std::cout<<std::setprecision(17)<<f.a<<' '<<f.b<<' '<<f.r2<<' '<<f.n<<'\n';
    Accumulator acc;
    for(const Row& r:rows.data) {
        if(acc.add(r.timeH,r.temp,datum)!=Status::Ok) return 2;
        Selection s; if(lookupRows(rows,datum,f,r.day,s)!=Status::Ok) return 3;
        std::cout<<acc.maturity()<<' '<<predict(acc.maturity(),f.a,f.b,s.factor)<<' '<<s.factor<<'\n';
    }
    return 0;
}
