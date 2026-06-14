# Default fallback toolchain (Cortex-M4 profile).
# mcuenv.py build selects toolchain-cortex-m{3,4,7,33}.cmake from chip registry cpu.

include(${CMAKE_CURRENT_LIST_DIR}/toolchain-cortex-m4.cmake)
