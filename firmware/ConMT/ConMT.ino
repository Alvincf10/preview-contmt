#include "src/board/BoardProfile.h"
#include "src/board/SdStorage.h"
#include "src/board/ArduinoUart.h"
#include "src/board/BatteryDevices.h"

using namespace conmt;
// BoardBinding defines these real peripheral ports; there are no fallback drivers.
extern ClockPort& conmtClock();
extern SensorPort& conmtSensors();
extern DevicePort& conmtDevices();
extern void conmtBoardBegin();
SdStorage media;
Journal journal(media);
Repository repository(journal);
BatteryDevices devices(conmtDevices());
Controller controller(repository,conmtClock(),conmtSensors(),devices);
ArduinoUart panelUart(Serial);
Transport panel(controller,panelUart);
void setup() {
    conmtBoardBegin();
    Serial.begin(CONMT_UART_BAUD);
    media.begin(CONMT_SD_CS,CONMT_SD_SPI_RATE);
    controller.boot();
    panel.refresh();
}
void loop() {
    controller.tick();
    panel.poll(millis());
}
