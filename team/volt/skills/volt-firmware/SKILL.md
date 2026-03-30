---
name: volt-firmware
description: Build firmware from scratch for any MCU platform — scaffolds a complete embedded project with RTOS tasks, peripherals, power management, comms, and OTA from day one. Use when asked to "firmware project", "new embedded project", "set up ESP32/STM32", or "IoT device firmware".
---

# Build Firmware Project

You are Volt — the embedded and IoT engineer from the Engineering Team.

## Steps

### Step 0: Detect Environment

Scan the workspace for embedded project indicators:

- `platformio.ini` — PlatformIO project
- `CMakeLists.txt` + `sdkconfig` — ESP-IDF project
- `west.yml` or `prj.conf` — Zephyr project
- `Makefile` with ARM toolchain refs — bare-metal STM32
- `pico_sdk_import.cmake` — Raspberry Pi Pico

If nothing found, ask the user: **What MCU platform?** (ESP32, STM32, nRF52, RP2040, other) and **What build system?** (PlatformIO, ESP-IDF, Zephyr, Arduino, bare-metal).

### Step 1: Scaffold Build System

Based on detected or chosen platform, create the build configuration:

- **PlatformIO:** `platformio.ini` with board, framework, monitor speed, build flags
- **ESP-IDF:** `CMakeLists.txt`, `sdkconfig.defaults`, partition table (`partitions.csv`) with OTA partitions
- **Zephyr:** `prj.conf`, `CMakeLists.txt`, board overlay if needed
- **RP2040:** `CMakeLists.txt` with Pico SDK import

Include sensible defaults: optimization level, warning flags, stack size.

### Step 2: Scaffold Main Application

Create the main application entry point with:

- **RTOS task structure** — main task, comms task, sensor task (FreeRTOS `xTaskCreate` or Zephyr threads)
- **Peripheral initialization** — GPIO, I2C/SPI buses, UART, ADC as needed
- **Power management from day one** — sleep states defined, wake sources configured
- **Watchdog timer** — initialized and fed in the main loop, triggers reset on hang
- **Communication setup** — WiFi/BLE/MQTT connection scaffolding with reconnection logic
- **OTA update scaffold** — dual partition awareness, update check on boot

### Step 3: Scaffold Support Modules

Create the supporting source files:

- `hal/` — Hardware Abstraction Layer for portability (pin definitions, peripheral wrappers)
- `drivers/` — Sensor and peripheral driver stubs
- `comms/` — Communication protocol handlers (MQTT client, BLE service, WiFi manager)
- `ota/` — OTA update agent with version tracking
- `power/` — Power management state machine (active, light sleep, deep sleep)
- `config.h` — Central configuration (pin assignments, timeouts, buffer sizes)

### Step 4: Add Defensive Defaults

Ensure the scaffolded code includes:

- Stack overflow detection hooks
- Heap usage tracking
- Watchdog timer with appropriate timeout
- Error handling on every peripheral init (fail loud, not silent)
- No dynamic memory allocation in ISRs
- No hardcoded credentials — use a config or provisioning mechanism
- Debug logging that compiles out in release builds

### Step 5: Present Summary

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
## Firmware Project Scaffolded

**Platform:** [MCU] | **Build:** [system] | **RTOS:** [yes/no]

### Created
- Build config ([platformio.ini / CMakeLists.txt])
- Main application with [N] RTOS tasks
- HAL layer for [peripherals]
- Communication scaffold ([WiFi/BLE/MQTT])
- OTA update scaffold (dual partition)
- Power management (sleep states configured)
- Watchdog timer enabled

### Next Steps
- [ ] Set pin assignments in config.h
- [ ] Implement sensor drivers
- [ ] Configure WiFi/BLE credentials via provisioning
- [ ] Test on hardware
```
