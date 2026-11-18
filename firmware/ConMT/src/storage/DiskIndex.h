#pragma once
#include "../core/Types.h"
namespace conmt {
class StoragePort;
class DiskIndex {
    struct Search {
        uint8_t bytes[26];
        uint32_t slot,head,position;
    };
    StoragePort* io_;
    uint32_t end_;
    Status find(const uint8_t* key,Search& search);
    Status node(uint32_t at,uint8_t* bytes);
public:
    static const uint8_t KeyBytes=10;
    DiskIndex() : io_(nullptr),end_(512) {}
    Status reset(StoragePort* storage);
    Status put(const uint8_t* key,uint32_t entry,uint32_t transaction);
    Status get(const uint8_t* key,uint32_t& entry,uint32_t& transaction);
};
}
