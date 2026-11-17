#pragma once
#include "../core/Types.h"
namespace conmt {
class StoragePort;
struct Key;
class DiskIndex {
    StoragePort* io_;
    uint32_t end_;
    Status root(const Key& key,uint32_t& slot,uint32_t& at);
    Status node(uint32_t at,uint8_t* bytes);
public:
    DiskIndex() : io_(nullptr),end_(512) {}
    Status reset(StoragePort* storage);
    Status put(const Key& key,uint32_t entry,uint32_t transaction);
    Status get(const Key& key,uint32_t& entry,uint32_t& transaction);
};
}
