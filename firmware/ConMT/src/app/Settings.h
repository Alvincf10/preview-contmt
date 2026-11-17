#pragma once
#include "../storage/Repository.h"
namespace conmt {
struct Settings { uint32_t intervalSeconds; uint8_t brightness; bool sound,autoSave; };
Status loadSettings(Repository& repo,Settings& settings);
Status settingValue(const char* name,const Settings& current,uint32_t& value,Field& field);
void assignSetting(Settings& settings,Field field,uint32_t value);
}
