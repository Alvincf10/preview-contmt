#include "src/Board.h"
#include "src/Panel.h"

void setup() {
  conmt::board::begin();
  conmt::panel::begin();
}

void loop() {
  conmt::board::poll();
  conmt::panel::poll();
}
