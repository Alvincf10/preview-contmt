#pragma once
#include "Types.h"
namespace conmt {
Real interval(Real prev, Real now, Real datum, Real hours);
Real locked(Real start, Real now, Real datum, Real elapsedSec);
Real fkzFromError(Real error);
Real predict(Real m, Real a, Real b, Real factor=1);
Real achievement(Real fc, Real target);
class Accumulator {
    bool first_;
    Real prevT_, prevH_, m_;
public:
    Accumulator() : first_(true), prevT_(0), prevH_(0), m_(0) {}
    Status add(Real timeH, Real temp, Real datum);
    Real maturity() const { return m_; }
};
class FitJob {
    RowSource& rows_;
    Real datum_, mx_, my_, sx_, sy_, sxy_;
    uint32_t n_;
    uint8_t phase_;
    Accumulator acc_;
    Fit fit_;
    Status status_;
public:
    FitJob(RowSource& source, Real datum);
    Status step();
    const Fit& result() const { return fit_; }
};
Status fitRows(RowSource& rows, Real datum, Fit& out);
Status lookupRows(RowSource& rows, Real datum, const Fit& fit, Real day, Selection& out);
Prediction trace(Real maturity, const Fit& fit, const Selection& factor);
}
