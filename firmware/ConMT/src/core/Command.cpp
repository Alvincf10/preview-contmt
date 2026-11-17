#include "Command.h"
#include "Flash.h"
namespace conmt {
static const char commands[] CM_ROM =
    "STORAGE_RESCAN\0"
    "PAGE_READY\0"
    "NAV\0"
    "USER_SAVE\0"
    "FIELD_SET\0"
    "BASE_NEW\0"
    "ROW_ADD_EARLY\0"
    "ROW_ADD_LAB\0"
    "ROW_FILL_EARLY\0"
    "ROW_SET\0"
    "ROW_SENSOR\0"
    "ROW_DELETE\0"
    "ROW_FOCUS\0"
    "ROW_SCHEDULE\0"
    "BASE_GENERATE\0"
    "BASE_SAVE\0"
    "BASE_PICK\0"
    "BASE_OPEN\0"
    "BASE_DELETE\0"
    "MEASURE_START\0"
    "CHECK_ADD\0"
    "CHECK_SET\0"
    "RESULT_PREPARE\0"
    "RESULT_SAVE\0"
    "HISTORY_PICK\0"
    "PAGE_ROWS\0"
    "SETTINGS_SET\0"
    "SETTINGS_STEP\0"
    "SETTINGS_TOGGLE\0"
    "SETTINGS_SAVE\0"
    "SESSION_RESUME\0"
    "GAP_RECONCILE\0"
;
static const uint8_t argumentCounts[] CM_ROM = {255,0,1,1,0,2,0,0,0,0,3,1,2,1,1,0,0,1,0,1,128,1,3,0,0,1,1,2,2,1,0,0,2};
Command commandFromText(const char* text) {
    const char* name=commands;
    for(uint8_t id=1;id<sizeof(argumentCounts);++id) {
#ifdef __AVR__
        if(!strcmp_P(text,name)) return Command(id);
        name+=strlen_P(name)+1;
#else
        if(!strcmp(text,name)) return Command(id);
        name+=strlen(name)+1;
#endif
    }
    return Command::Unknown;
}
bool validArguments(Command command,uint8_t count) {
    uint8_t id=uint8_t(command);
    if(!id||id>=sizeof(argumentCounts)) return false;
#ifdef __AVR__
    uint8_t expected=pgm_read_byte(argumentCounts+id);
#else
    uint8_t expected=argumentCounts[id];
#endif
    return expected==128?count<=1:count==expected;
}
}
