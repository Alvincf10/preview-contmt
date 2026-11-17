#pragma once
#include <string.h>
#include <stdio.h>
#ifdef __AVR__
#include <avr/pgmspace.h>
#define CM_EQ(a,b) (strcmp_P((a),PSTR(b))==0)
#define CM_FMT(dst,n,fmt,...) snprintf_P((dst),(n),PSTR(fmt),__VA_ARGS__)
#define CM_TEXT(dst,n,text) snprintf_P((dst),(n),PSTR(text))
#define CM_COPY(dst,text) strcpy_P((dst),PSTR(text))
#define CM_ROM PROGMEM
namespace conmt { inline const char* flashText(const char* p) { static char value[32]; strncpy_P(value,p,sizeof(value)-1); value[sizeof(value)-1]=0; return value; } }
#else
#define CM_EQ(a,b) (strcmp((a),(b))==0)
#define CM_FMT(dst,n,fmt,...) snprintf((dst),(n),(fmt),__VA_ARGS__)
#define CM_TEXT(dst,n,text) snprintf((dst),(n),(text))
#define CM_COPY(dst,text) strcpy((dst),(text))
#define CM_ROM
namespace conmt { inline const char* flashText(const char* p) { return p; } }
#endif
