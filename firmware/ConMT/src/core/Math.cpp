#include "Flash.h"
#include "Math.h"
namespace conmt {
Real interval(Real prev,Real now,Real datum,Real h) {
    if (!(h>0) || !finite(prev) || !finite(now)) return 0;
    return ((prev+now)/2-datum)*h;
}
Real locked(Real start,Real now,Real datum,Real sec) { return positive(interval(start,now,datum,positive(sec)/3600)); }
Real fkzFromError(Real e) {
    if (!finite(e)) return 1;
    if (e>0) return 1/(1+e);
    return e>Real(-.1) ? 1 : 1+(fabs(e)-Real(.1));
}
Real predict(Real m,Real a,Real b,Real factor) {
    if (!(m>0) || !finite(m) || !finite(a) || !finite(b)) return 0;
    return positive((a+b*log(m))*(finite(factor) && factor>0?factor:1));
}
Real achievement(Real fc,Real target) { return target>0 && finite(target) && finite(fc)?positive(fc/target*100):0; }
Status Accumulator::add(Real h,Real t,Real datum) {
    if (!finite(h) || !finite(t) || !finite(datum)) return Status::Invalid;
    if (!first_ && h<prevH_) return Status::Invalid;
    if (!first_) m_=positive(m_+interval(prevT_,t,datum,h-prevH_));
    first_=false; prevH_=h; prevT_=t;
    return finite(m_)?Status::Ok:Status::Invalid;
}
FitJob::FitJob(RowSource& s,Real datum) : rows_(s),datum_(datum),mx_(0),my_(0),sx_(0),sy_(0),sxy_(0),n_(0),phase_(0),status_(Status::Busy) { rows_.reset(); }
Status FitJob::step() {
    if (status_!=Status::Busy) return status_;
    Row row;
    Status st=rows_.next(row);
    if (st==Status::Missing) {
        if (!phase_) {
            if (n_<2) return status_=Status::NoModel;
            mx_/=n_; my_/=n_; phase_=1; acc_=Accumulator(); rows_.reset(); return Status::Busy;
        }
        if (!(sx_>0)) return status_=Status::NoModel;
        fit_.b=sxy_/sx_; fit_.a=my_-fit_.b*mx_;
        fit_.r2=sy_==0?1:(sxy_*sxy_/(sx_*sy_));
        if (fit_.r2>1) fit_.r2=1;
        if (fit_.r2<0) fit_.r2=0;
        fit_.n=n_; fit_.valid=finite(fit_.a)&&finite(fit_.b)&&finite(fit_.r2);
        return status_=fit_.valid?Status::Ok:Status::NoModel;
    }
    if (st!=Status::Ok) return status_=st;
    if (!row.hasTemp) return status_=Status::Invalid;
    st=acc_.add(row.timeH,row.temp,datum_);
    if (st!=Status::Ok) return status_=st;
    if (row.hasFc && row.fc>0 && acc_.maturity()>0) {
        if (!finite(row.fc)) return status_=Status::Invalid;
        Real x=log(acc_.maturity());
        if (!phase_) { mx_+=x; my_+=row.fc; ++n_; }
        else { Real dx=x-mx_,dy=row.fc-my_; sx_+=dx*dx; sy_+=dy*dy; sxy_+=dx*dy; }
    }
    return Status::Busy;
}
Status fitRows(RowSource& source,Real datum,Fit& fit) {
    FitJob job(source,datum); Status st;
    do { st=job.step(); } while(st==Status::Busy);
    fit=job.result(); return st;
}
Status lookupRows(RowSource& rows,Real datum,const Fit& fit,Real day,Selection& out) {
    out=Selection(); if (!fit.valid) return Status::NoModel;
    if (!finite(day)) return Status::Ok;
    Accumulator acc; Row r; rows.reset(); Status st;
    Selection upper,last;
    while ((st=rows.next(r))==Status::Ok) {
        if (!r.hasTemp) return Status::Missing;
        st=acc.add(r.timeH,r.temp,datum); if(st!=Status::Ok) return st;
        if (!r.hasFc || !(r.fc>0) || !finite(r.day) || !(acc.maturity()>0)) continue;
        Real ns=fit.a+fit.b*log(acc.maturity());
        if (!(ns>0) || !finite(ns)) continue;
        Real k=fkzFromError((ns-r.fc)/r.fc);
        if (!finite(k) || !(k>0)) continue;
        if (!last.found || r.day>=last.day) { last.day=r.day; last.factor=k; last.found=true; }
        if (r.day>=day && (!upper.found || r.day<=upper.day)) { upper.day=r.day; upper.factor=k; upper.found=true; }
    }
    if (st!=Status::Missing) return st;
    out=upper.found?upper:last; return Status::Ok;
}
Prediction trace(Real m,const Fit& f,const Selection& s) {
    Prediction p; p.maturity=m; p.factor=s.factor; p.referenceDay=s.day; p.hasReference=s.found;
    if (f.valid && m>0 && finite(m)) { p.raw=f.a+f.b*log(m); p.fc=predict(m,f.a,f.b,s.factor); }
    return p;
}
}
