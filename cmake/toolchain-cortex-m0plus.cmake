# Cortex-M0+: no FPU (e.g. STM32G0, STM32L0)

set(CMAKE_SYSTEM_PROCESSOR cortex-m0plus)
set(MCU_FLAGS "-mcpu=cortex-m0plus -mthumb")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
