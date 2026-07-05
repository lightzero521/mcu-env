# RISC-V GCC toolchain. Included by toolchain-riscv*.cmake profile files.
# Compiler tools are resolved from PATH (riscv32-unknown-elf-* must be on PATH).

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv)

set(CMAKE_C_COMPILER riscv32-unknown-elf-gcc)
set(CMAKE_ASM_COMPILER riscv32-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER riscv32-unknown-elf-g++)
set(CMAKE_AR riscv32-unknown-elf-ar)
set(CMAKE_OBJCOPY riscv32-unknown-elf-objcopy)
set(CMAKE_OBJDUMP riscv32-unknown-elf-objdump)
set(CMAKE_SIZE riscv32-unknown-elf-size)
set(CMAKE_GDB riscv32-unknown-elf-gdb)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

if(DEFINED MCU_FLAGS)
    set(CMAKE_C_FLAGS_INIT "${MCU_FLAGS} -ffunction-sections -fdata-sections  -fno-builtin")
    set(CMAKE_CXX_FLAGS_INIT "${MCU_FLAGS} -ffunction-sections -fdata-sections  -fno-builtin")
    set(CMAKE_ASM_FLAGS_INIT "${MCU_FLAGS}")
    set(CMAKE_EXE_LINKER_FLAGS_INIT "${MCU_FLAGS} -Wl,--gc-sections")
endif()

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
