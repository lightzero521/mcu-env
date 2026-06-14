# Cortex-M4 with single-precision FPU (e.g. GD32F303, STM32F4/F3)

set(CMAKE_SYSTEM_PROCESSOR cortex-m4)
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
