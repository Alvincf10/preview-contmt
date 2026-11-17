#pragma once
#include <stdint.h>
#include <stddef.h>
namespace conmt {
class Text {
    char* out_; size_t capacity_,used_;
public:
    Text(char* out,size_t capacity) : out_(out),capacity_(capacity),used_(0) { if(capacity_) out_[0]=0; }
    Text& character(char value);
    Text& ram(const char* value);
    Text& flash(const char* value);
    Text& number(uint32_t value,uint8_t digits=0);
};
void copyRam(char* out,size_t capacity,const char* text);
void formatUnsigned(char* out,size_t capacity,uint32_t value,uint8_t digits=0);
void formatHms(char* out,size_t capacity,uint32_t hours,uint8_t minutes,uint8_t seconds,uint8_t hourDigits=2);
}
