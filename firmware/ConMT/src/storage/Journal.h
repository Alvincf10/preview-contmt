#pragma once
#include "../core/Types.h"
#include "DiskIndex.h"
namespace conmt {
class StoragePort {
protected:
    ~StoragePort() {}
public:
    virtual StoragePort* indexStorage() { return nullptr; }
    virtual Status reopen() { return Status::Ok; }
    virtual Status size(uint32_t& value)=0;
    virtual Status read(uint32_t at,uint8_t* out,uint16_t length)=0;
    virtual Status write(uint32_t at,const uint8_t* data,uint16_t length)=0;
    virtual Status truncate(uint32_t length)=0;
    virtual Status sync()=0;
};
class ValueReader {
    friend class Journal;
    StoragePort* io_;
    uint32_t at_;
    uint16_t remaining_;
public:
    ValueReader() : io_(nullptr),at_(0),remaining_(0) {}
    Status read(uint8_t* out,uint16_t size);
    Status skip(uint16_t size);
    uint16_t remaining() const { return remaining_; }
};
enum class Kind : uint8_t { User=1, Settings, Draft, Baseline, Session, Result, System };
enum class Field : uint8_t {
    Exists=1, Name, Target, Datum, Pour, Created, Operator, Project, Date,
    Cement, Water, Coarse, Fine, RetarderPct, RetarderBrand, AcceleratorPct,
    AcceleratorBrand, FlyAshPct, FlyAshBrand, MaxRow, Row, Model,
    BaselineRef, Start, InitialTemp, State, Gap, Result, Sensors,
    Interval, Brightness, Sound, AutoSave, ClockIssue, GapStart, GapEnd, PreviewSensors, DayInput, TempInput, FcInput, ClockAdjustment
};
struct Key {
    Kind kind; uint32_t object; Field field; uint32_t index;
    Key(Kind k=Kind::System,uint32_t o=0,Field f=Field::Exists,uint32_t i=0) __attribute__((noinline));
    bool operator==(const Key& b) const { return kind==b.kind && object==b.object && field==b.field && index==b.index; }
};
class Journal {
    enum class Query : uint8_t { Value, Operation, MaxObject };
    struct Transaction {
        uint32_t next, sequence;
        uint64_t operation;
    };
    struct Lookup {
        Query mode;
        const uint8_t* key;
        const uint64_t* operation;
        uint32_t indexedEntry, found, object;
        uint16_t length;
        void consider(uint32_t position,const uint8_t* header,uint16_t size);
    };
    StoragePort& io_;
    DiskIndex index_;
    uint32_t end_,sequence_,writeAt_,payloadCrc_,count_;
    uint64_t operation_;
    uint16_t remaining_;
    bool writing_,tail_,uncertain_,mounted_,indexed_;
    Status scan();
    Status indexTransaction(uint32_t at,uint32_t next,const uint64_t& operation);
    Status readEntry(uint32_t at,uint32_t available,uint8_t* header,uint16_t& length);
    Status locate(const Key& key,uint32_t& at,uint16_t& length);
    Status findEntry(Lookup& lookup);
    Status verify(uint32_t at,uint32_t limit,Transaction& transaction,bool footer,Lookup* lookup=nullptr);
public:
    static const uint16_t MaxValue=128;
    explicit Journal(StoragePort& io) : io_(io),end_(0),sequence_(0),writeAt_(0),payloadCrc_(0),count_(0),operation_(0),remaining_(0),writing_(false),tail_(false),uncertain_(false),mounted_(false),indexed_(false) {}
    Status mount();
    Status begin(const uint64_t& operation=0);
    Status put(const Key& key,const uint8_t* value,uint16_t size);
    Status startValue(const Key& key,uint16_t size);
    Status appendValue(const uint8_t* bytes,uint16_t size);
    Status erase(const Key& key) { return put(key,nullptr,0); }
    Status commit();
    void abort() { writing_=false; remaining_=0; }
    Status get(const Key& key,uint8_t* value,uint16_t& size);
    Status openValue(const Key& key,uint16_t expected,ValueReader& reader);
    Status copy(const Key& from,const Key& to,uint16_t expected=0);
    Status findOperation(const uint64_t& operation,Key& first);
    Status maxObject(Kind kind,uint32_t& out);
    uint32_t sequence() const { return sequence_; }
    uint32_t committedBytes() const { return end_; }
    bool recoveredTail() const { return tail_; }
    bool indexed() const { return indexed_; }
};
void put16(uint8_t* b,uint16_t n);
void put32(uint8_t* b,uint32_t n);
void put64(uint8_t* b,uint64_t n);
uint16_t get16(const uint8_t* b);
uint32_t get32(const uint8_t* b);
uint64_t get64(const uint8_t* b);
void putReal(uint8_t* b,Real n);
Real getReal(const uint8_t* b);
}
