// Reuse the host test's card image and board ports with the production CM1 parser.
#define main conmt_host_test_main
#include "ConMTTest.cpp"
#undef main

int main() {
  formatCard();
  live = {{2600000, 2612500, 2587500}, 7};
  panel::begin();
  std::string input;
  const char digits[] = "0123456789abcdef";
  while (std::getline(std::cin, input)) {
    if (input == "!UNAVAILABLE") {
      image.clear();
      live.valid = 0;
      wall = {NoDate, 0};
      panel::begin();
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
    } else {
      frame(input);
    }
    for (const unsigned char value : output)
      std::cout << digits[value >> 4] << digits[value & 15];
    std::cout << std::endl;
  }
}
