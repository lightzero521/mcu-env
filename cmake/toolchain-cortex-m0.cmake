# Cortex-M0: no FPU (e.g. STM32F0, GD32E230)

set(CMAKE_SYSTEM_PROCESSOR cortex-m0)
set(MCU_FLAGS "-mcpu=cortex-m0 -mthumb")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
