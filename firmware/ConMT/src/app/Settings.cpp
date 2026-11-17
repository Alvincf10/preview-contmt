#include "Settings.h"
#include "../core/Flash.h"
#include "../core/Command.h"
namespace conmt {
static const uint32_t maximum[] CM_ROM={86399,100,1,1};
static const uint8_t offsets[] CM_ROM={offsetof(Settings,intervalSeconds),offsetof(Settings,brightness),offsetof(Settings,sound),offsetof(Settings,autoSave)};
static bool valid(uint8_t id,uint32_t value) { return value<=flashValue(maximum+id)&&(id!=1||value%5==0); }
void assignSetting(Settings& settings,Field field,uint32_t value) {
    uint8_t id=uint8_t(field)-uint8_t(Field::Interval);
    uint8_t* out=reinterpret_cast<uint8_t*>(&settings)+flashValue(offsets+id);
    if(id==0) memcpy(out,&value,4);
    else if(id==1) *out=uint8_t(value);
    else *reinterpret_cast<bool*>(out)=value!=0;
}
Status loadSettings(Repository& repo,Settings& settings) {
    for(uint8_t i=0;i<4;++i) {
        Field field=Field(uint8_t(Field::Interval)+i); uint32_t value=0;
        Status st=repo.integer(Key(Kind::Settings,0,field),value);
        if(st==Status::Missing) continue;
        if(st!=Status::Ok) return st;
        if(i&&!valid(i,value)) return Status::Corrupt;
        assignSetting(settings,field,value);
    }
    return valid(0,settings.intervalSeconds)&&valid(1,settings.brightness)?Status::Ok:Status::Corrupt;
}
Status settingValue(const char* name,const Settings& current,uint32_t& value,Field& field) {
    static const char names[] CM_ROM="hour\0minute\0second\0interval\0brightness\0sound\0autoSave";
    uint8_t token=flashToken(name,names,7); if(!token) return Status::Invalid;
    if(token<=3) {
        if(value>(token==1?23u:59u)) return Status::Invalid;
        if(token==1) value=value*3600+current.intervalSeconds%3600;
        else if(token==2) value=current.intervalSeconds/3600*3600+value*60+current.intervalSeconds%60;
        else value=current.intervalSeconds/60*60+value;
        field=Field::Interval;
    } else {
        uint8_t id=token-4;
        if(!valid(id,value)) return Status::Invalid;
        field=Field(uint8_t(Field::Interval)+id);
    }
    return Status::Ok;
}
}
