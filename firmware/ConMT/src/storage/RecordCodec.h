#pragma once
#include "Journal.h"
namespace conmt {
enum class RecordType : uint8_t { Row, Point, Model, Result, SampleTime, Channels, Average };
Status readRecord(Journal& journal,const Key& key,RecordType type,void* record);
Status writeRecord(Journal& journal,const Key& key,RecordType type,const void* record);
Status appendRecord(Journal& journal,RecordType type,const void* record);
}
