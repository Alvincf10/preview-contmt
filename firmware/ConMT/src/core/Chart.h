#pragma once
#include "Math.h"
namespace conmt {
struct ChartSample { Real maturity,fc; };
class ChartCurve {
    Fit fit_; Real maximum_,start_;
public:
    ChartCurve(const Fit& fit,Real dataMax) : fit_(fit) {
        maximum_=ceil(positive(dataMax)/5000)*5000; if(maximum_<20000) maximum_=20000;
        Real zero=fit.b!=0?exp(-fit.a/fit.b):1;
        start_=zero>1?zero:1; if(start_>maximum_*Real(.02)) start_=maximum_*Real(.02);
    }
    Real maximum() const { return maximum_; }
    bool sample(uint8_t i,ChartSample& out) const {
        if(i>64||!fit_.valid) return false;
        out.maturity=start_+(maximum_-start_)*Real(i)/64;
        out.fc=fit_.a+fit_.b*log(out.maturity);
        return finite(out.fc);
    }
};
}
