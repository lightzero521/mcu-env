# Cortex-M33 with FP extension (e.g. GD32F527)

set(CMAKE_SYSTEM_PROCESSOR cortex-m33)
set(MCU_FLAGS "-mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=hard")

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-base-arm.cmake)
