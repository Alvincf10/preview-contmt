#include "FieldRules.h"
#include "../core/Flash.h"
#include "../core/Command.h"
namespace conmt {
bool fieldRule(const char* token,FieldRule& out) {
    static const char tokens[] CM_ROM="operator\0project\0date\0pourDate\0pourClock\0name\0target\0datum\0cement\0water\0coarse\0fine\0retarderPct\0retarderBrand\0acceleratorPct\0acceleratorBrand\0flyAshPct\0flyAshBrand";
#define R(kind,field,format,cap) {Kind::kind,Field::field,InputFormat::format,cap}
    static const FieldRule rules[] CM_ROM={
        R(User,Operator,Text,33),R(User,Project,Text,65),R(User,Date,Date,65),
        R(Draft,Pour,PourDate,0),R(Draft,Pour,PourClock,0),
        R(Draft,Name,Text,65),R(Draft,Target,Positive,0),R(Draft,Datum,Datum,0),
        R(Draft,Cement,NonNegative,0),R(Draft,Water,NonNegative,0),R(Draft,Coarse,NonNegative,0),R(Draft,Fine,NonNegative,0),
        R(Draft,RetarderPct,NonNegative,0),R(Draft,RetarderBrand,Text,33),
        R(Draft,AcceleratorPct,NonNegative,0),R(Draft,AcceleratorBrand,Text,33),
        R(Draft,FlyAshPct,NonNegative,0),R(Draft,FlyAshBrand,Text,33)
    };
#undef R
    uint8_t id=flashToken(token,tokens,sizeof(rules)/sizeof(*rules));
    if(!id) return false;
    out=flashValue(rules+id-1); return true;
}
}
