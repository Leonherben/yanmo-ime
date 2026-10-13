cmake_minimum_required(VERSION 3.20)
project(yanmo_engine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(ENABLE_SANITIZERS "Enable Address and Undefined sanitizers" OFF)

if(ENABLE_SANITIZERS)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
endif()

# Compiler options
if(MSVC)
    add_compile_options(/W4 /permissive-)
else()
    add_compile_options(-Wall -Wextra -O3 -fPIC)
endif()

include_directories(include)

# Core sources
file(GLOB CORE_SRCS "src/*.cpp")

find_package(Threads REQUIRED)

# Shared library
add_library(yanmo_engine SHARED ${CORE_SRCS})
target_include_directories(yanmo_engine PUBLIC include)
target_link_libraries(yanmo_engine PRIVATE Threads::Threads)

# Tests & CTest
include(CTest)
enable_testing()

# 1. test_lattice
add_executable(cmake_test_lattice
    src/lattice.cpp
    src/keyboard_model.cpp
    tests/test_lattice.cpp
)
target_link_libraries(cmake_test_lattice PRIVATE Threads::Threads)
add_test(NAME lattice_test COMMAND cmake_test_lattice)

# 2. test_speller
add_executable(cmake_test_speller
    src/speller.cpp
    src/lattice.cpp
    src/keyboard_model.cpp
    tests/test_speller.cpp
)
target_link_libraries(cmake_test_speller PRIVATE Threads::Threads)
add_test(NAME speller_test COMMAND cmake_test_speller)

# 3. test_bigram
add_executable(cmake_test_bigram
    src/bigram.cpp
    src/decoder.cpp
    tests/test_bigram.cpp
)
target_link_libraries(cmake_test_bigram PRIVATE Threads::Threads)
add_test(NAME bigram_test COMMAND cmake_test_bigram)

# 4. test_llm_provider
add_executable(cmake_test_llm_provider
    src/rule_llm_provider.cpp
    tests/test_llm_provider.cpp
)
target_link_libraries(cmake_test_llm_provider PRIVATE Threads::Threads)
add_test(NAME llm_provider_test COMMAND cmake_test_llm_provider)

# 5. test_engine
add_executable(cmake_test_engine
    ${CORE_SRCS}
    tests/test_engine.cpp
)
target_link_libraries(cmake_test_engine PRIVATE Threads::Threads)
add_test(NAME engine_test COMMAND cmake_test_engine)
