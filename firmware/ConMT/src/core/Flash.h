#pragma once
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define CM_EQ(a,b) (strcmp_P((a),PSTR(b))==0)
#define CM_FMT(dst,n,fmt,...) snprintf_P((dst),(n),PSTR(fmt),__VA_ARGS__)
#define CM_TEXT(dst,n,text) conmt::copyFlash((dst),(n),PSTR(text))
#define CM_COPY(dst,text) strcpy_P((dst),PSTR(text))
#define CM_ROM PROGMEM
#define CM_LITERAL(text) PSTR(text)
#else
#define CM_EQ(a,b) (strcmp((a),(b))==0)
#define CM_FMT(dst,n,fmt,...) snprintf((dst),(n),(fmt),__VA_ARGS__)
#define CM_TEXT(dst,n,text) conmt::copyFlash((dst),(n),(text))
#define CM_COPY(dst,text) strcpy((dst),(text))
#define CM_ROM
#define CM_LITERAL(text) text
#endif
namespace conmt {
void copyFlash(char* out,size_t capacity,const char* value);
void indexedName(char* out,size_t capacity,const char* prefix,uint8_t slot);
template<typename T> T flashValue(const T* address) {
#ifdef __AVR__
    T value; memcpy_P(&value,address,sizeof(value)); return value;
#else
    return *address;
#endif
}
}
