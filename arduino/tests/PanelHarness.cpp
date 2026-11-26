// Reuse the host test's card image and board ports with the production CM1 parser.
#define main conmt_host_test_main
#include "ConMTTest.cpp"
#undef main

namespace {

void measureLongList(Engine& engine, Ref baseline) {
  success(engine.start(baseline));
  for (unsigned day = 1; day <= 8; ++day) {
    wall = forward(wall, DaySeconds);
    success(engine.checkpoint(day * DayScale, wall, 2600000, true, false));
  }
}

void seedLongLists() {
  Engine engine;
  assert(engine.recover());
  setUser(engine);
  Ref baseline = 0;
  for (unsigned test = 1; test <= 6; ++test) {
    success(engine.draft(baseline));
    const std::string name = "Scroll baseline " + std::to_string(test);
    success(engine.set(Field::Name, name.c_str()));
    if (!baseline) {
      success(engine.set(Field::Target, "35"));
      success(engine.set(Field::Datum, "-20"));
      success(engine.row(0, Field::Temperature, "26"));
      for (unsigned day = 1; day <= 2; ++day) {
        success(engine.addRows(false, false));
        success(engine.row(day, Field::Temperature, "26"));
        success(engine.row(day, Field::Fc, day == 1 ? "10" : "20"));
      }
    }
    success(engine.generate());
    baseline = success(engine.saveBaseline(engine.disk.root().draft));
    measureLongList(engine, baseline);
    success(engine.saveResult(engine.disk.root().active));
  }
  measureLongList(engine, baseline);
}

}  // namespace

int main(int argc, char** argv) {
  formatCard();
  live = {{2600000, 2612500, 2587500}, 7};
  if (argc == 2 && std::string(argv[1]) == "--long-lists") seedLongLists();
  BatteryGauge battery;
  panel::begin();
  std::string input;
  const char digits[] = "0123456789abcdef";
  while (std::getline(std::cin, input)) {
    if (input == "!UNAVAILABLE") {
      image.clear();
      live.valid = 0;
      batteryValue = -1;
      wall = {NoDate, 0};
      panel::begin();
      output.clear();
    } else if (input == "!INSERT") {
      formatCard();
      output.clear();
    } else if (input == "!RESET") {
      wall = {NoDate, 0};
      tick = 0;
      panel::begin();
      output.clear();
    } else if (input.compare(0, 6, "!TICK|") == 0) {
      const uint32_t seconds = std::stoul(input.substr(6));
      wall = forward(wall, seconds);
      tick += seconds * 1000;
      panel::poll();
      output.clear();
    } else if (input.compare(0, 9, "!BATTERY|") == 0) {
      const uint16_t adc = std::stoul(input.substr(9));
      for (unsigned i = 0; i < 800; ++i) battery.sample(adc);
      batteryValue = battery.percent();
      output.clear();
    } else {
      frame(input);
    }
    for (const unsigned char value : output)
      std::cout << digits[value >> 4] << digits[value & 15];
    std::cout << std::endl;
  }
}
