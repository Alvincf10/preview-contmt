#pragma once
#include "../storage/Repository.h"
namespace conmt {
struct Entity { Kind kind; uint32_t id; };
enum class TxTarget : uint8_t { Destination, Source, User, System, Settings };
enum class TxOp : uint8_t {
    Constant, SourceId, DestinationId, Integer, Number, Time, Now, Model, Point,
    Sensors, CopyObject, CopyNumber, CopyText, CopyUserText, CopyUserField, CopySensors
};
struct TxStep { TxOp op; TxTarget target; Field field; uint8_t argument; };
struct TxSample { Time time; Average average; SensorFrame frame; };
Status applyTransaction(Repository& repo,ClockPort& clock,const TxStep* steps,uint8_t count,
                        const Entity& source,const Entity& destination,const void* data);
}
