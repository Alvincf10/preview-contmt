#pragma once
#include "../app/Controller.h"
namespace conmt {
class Presenter {
    Controller& app_;
    bool rows(uint8_t index,char* component,size_t cc,char* value,size_t vc);
    bool points(uint8_t index,char* component,size_t cc,char* value,size_t vc);
public:
    explicit Presenter(Controller& app) : app_(app) {}
    bool field(uint16_t index,char* component,size_t cc,char* value,size_t vc);
};
}
