#pragma once
#include "Journal.h"
#include "../core/Math.h"
namespace conmt {
class Repository {
    Journal& journal_;
public:
    explicit Repository(Journal& j) : journal_(j) {}
    Journal& journal() { return journal_; }
    Status number(const Key& k,Real& out);
    Status integer(const Key& k,uint32_t& out);
    Status time(const Key& k,uint64_t& out);
    Status text(const Key& k,char* out,uint16_t capacity);
    Status putNumber(const Key& k,Real value);
    Status putInteger(const Key& k,uint32_t value);
    Status putTime(const Key& k,uint64_t value);
    Status putText(const Key& k,const char* value,uint16_t cap);
    Status row(Kind kind,uint32_t object,uint32_t id,Row& out);
    Status putRow(Kind kind,uint32_t object,const Row& row);
    Status point(Kind kind,uint32_t object,uint32_t id,Point& out);
    Status putPoint(Kind kind,uint32_t object,const Point& point);
    Status model(Kind kind,uint32_t object,Fit& out);
    Status putModel(Kind kind,uint32_t object,const Fit& fit);
    Status result(Kind kind,uint32_t object,Result& out);
    Status putResult(Kind kind,uint32_t object,const Result& result);
    Status putSensors(Kind kind,uint32_t object,const SensorFrame& frame,const Average& avg,const Time& time,Field destination=Field::Sensors);
    Status copyScalar(const Key& from,const Key& to,uint16_t expected=0);
    Status copy(Kind from,uint32_t src,Kind to,uint32_t dest);
    Status list(Kind kind,uint32_t after,uint32_t& id);
};
enum class RowView : uint8_t { Chronological, Display, CompleteDraft };
class StoredRows : public RowSource {
    Repository& repo_; Kind kind_; uint32_t object_,max_,lastId_; Real lastH_,lastDay_;
    uint8_t seen_;
    RowView view_;
public:
    StoredRows(Repository& repo,Kind kind,uint32_t object,RowView view=RowView::Chronological);
    void reset() override;
    Status next(Row& out) override;
};
class Record {
    Repository& repo_;
    Key key_;
    const Key& field(Field value) { key_.field=value; return key_; }
public:
    Record(Repository& repo,Kind kind,uint32_t object) : repo_(repo),key_(kind,object) {}
    Status number(Field field,Real& out);
    Status integer(Field field,uint32_t& out);
    Status time(Field field,uint64_t& out);
    Status text(Field field,char* out,uint16_t capacity);
    Status putNumber(Field field,Real value);
    Status putInteger(Field field,uint32_t value);
    Status putTime(Field field,uint64_t value);
    Status putText(Field field,const char* value,uint16_t capacity);
    Status erase(Field field);
    Status get(Field field,uint8_t* out,uint16_t& size);
    Status put(Field field,const uint8_t* value,uint16_t size);
};
Status nextPoint(Repository& repo,Kind kind,uint32_t object,const Point* after,Point& out);
Status replayPoints(Repository& repo,Kind kind,uint32_t object,Real datum,Real& maturity,Point& last,uint32_t stopAt=0,bool summaryStatus=false);
}
