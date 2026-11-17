#include "Text.h"
#include "Flash.h"
namespace conmt {
Text& Text::character(char value) {
    if(used_+1<capacity_) { out_[used_++]=value; out_[used_]=0; }
    return *this;
}
Text& Text::ram(const char* value) { while(*value) character(*value++); return *this; }
Text& Text::flash(const char* value) { char c; while((c=flashValue(value++))) character(c); return *this; }
Text& Text::number(uint32_t value,uint8_t digits) {
    char reversed[10]; uint8_t count=0;
    do { reversed[count++]=char('0'+value%10); value/=10; } while(value);
    while(digits>count) { character('0'); --digits; }
    while(count) character(reversed[--count]);
    return *this;
}
void copyRam(char* out,size_t capacity,const char* text) { Text(out,capacity).ram(text); }
void formatUnsigned(char* out,size_t capacity,uint32_t value,uint8_t digits) { Text(out,capacity).number(value,digits); }
void formatHms(char* out,size_t capacity,uint32_t hours,uint8_t minutes,uint8_t seconds,uint8_t hourDigits) {
    Text(out,capacity).number(hours,hourDigits).character(':').number(minutes,2).character(':').number(seconds,2);
}
}
