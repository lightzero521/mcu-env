# Cortex-M7 with double-precision FPU (e.g. STM32H7)

set(CMAKE_SYSTEM_PROCESSOR cortex-m7)
set(MCU_FLAGS "-mcpu=cortex-m7 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=hard")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
