#pragma once
#ifndef __AVR_ATmega328P__
#error "ConMT production target must be ATmega328P"
#endif
#if !__has_include("BoardBinding.h")
#error "BoardBinding.h required: verified clock/pins/sensor/RTC/battery/UART settings; see BOARD_PROFILE_REQUIRED.md"
#else
#include "BoardBinding.h"
#if !defined(CONMT_BOARD_VERIFIED) || CONMT_BOARD_VERIFIED != 1
#error "Board profile is not verified; production cannot use test ports"
#endif
#ifndef CONMT_UART_BAUD
#error "Verified Nextion baud is required"
#endif
#ifndef CONMT_SD_CS
#error "Verified SD chip select is required"
#endif
#ifndef CONMT_SD_SPI_RATE
#error "Verified SPI rate is required"
#endif
#endif
