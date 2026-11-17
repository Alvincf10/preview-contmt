#include <stdint.h>
#include "Flash.h"
namespace conmt {
void copyFlash(char* out,size_t capacity,const char* value) {
    if(!capacity) return;
    size_t at=0;
    while(at+1<capacity) {
        char c=flashValue(value+at); if(!c) break;
        out[at++]=c;
    }
    out[at]=0;
}
void indexedName(char* out,size_t capacity,const char* prefix,uint8_t slot) {
    copyFlash(out,capacity,prefix);
    if(!capacity) return;
    size_t length=strlen(out);
    if(slot<10 && length+1<capacity) { out[length]=char('0'+slot); out[length+1]=0; }
}
}
