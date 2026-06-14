# Cortex-M3: no FPU (e.g. STM32F103)

set(CMAKE_SYSTEM_PROCESSOR cortex-m3)
set(MCU_FLAGS "-mcpu=cortex-m3 -mthumb")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
