CXX = g++
CXXFLAGS = -std=c++20 -O3 -Wall -Wextra -fPIC -Iinclude -MMD -MP
LDFLAGS = -lpthread

SRC_DIR = src
INC_DIR = include
TEST_DIR = tests
BIN_DIR = bin
LIB_DIR = lib

SRCS = $(wildcard $(SRC_DIR)/*.cpp)
OBJS = $(SRCS:.cpp=.o)
TEST_OBJS = $(wildcard $(TEST_DIR)/*.o)
DEPS = $(SRCS:.cpp=.d) $(wildcard $(TEST_DIR)/*.d)

LIB_TARGET = $(LIB_DIR)/libyanmo_engine.so
TEST_ENGINE = $(BIN_DIR)/test_engine
TEST_SPELLER = $(BIN_DIR)/test_speller
TEST_BIGRAM = $(BIN_DIR)/test_bigram
TEST_LLM = $(BIN_DIR)/test_llm_provider
TEST_LATTICE = $(BIN_DIR)/test_lattice

all: $(LIB_TARGET) $(TEST_ENGINE) $(TEST_SPELLER) $(TEST_BIGRAM) $(TEST_LLM) $(TEST_LATTICE)

$(LIB_TARGET): $(OBJS)
	@mkdir -p $(LIB_DIR)
	$(CXX) -shared -o $@ $^ $(LDFLAGS)
	@echo "Built shared library: $@"

$(TEST_ENGINE): $(OBJS) $(TEST_DIR)/test_engine.o
	@mkdir -p $(BIN_DIR)
	$(CXX) -o $@ $^ $(LDFLAGS)
	@echo "Built test executable: $@"

$(TEST_SPELLER): $(SRC_DIR)/speller.o $(SRC_DIR)/lattice.o $(SRC_DIR)/keyboard_model.o $(TEST_DIR)/test_speller.o
	@mkdir -p $(BIN_DIR)
	$(CXX) -o $@ $^ $(LDFLAGS)
	@echo "Built test speller executable: $@"

$(TEST_BIGRAM): $(SRC_DIR)/bigram.o $(SRC_DIR)/decoder.o $(TEST_DIR)/test_bigram.o
	@mkdir -p $(BIN_DIR)
	$(CXX) -o $@ $^ $(LDFLAGS)
	@echo "Built test bigram executable: $@"

$(TEST_LLM): $(SRC_DIR)/rule_llm_provider.o $(TEST_DIR)/test_llm_provider.o
	@mkdir -p $(BIN_DIR)
	$(CXX) -o $@ $^ $(LDFLAGS)
	@echo "Built test LLM executable: $@"

$(TEST_LATTICE): $(SRC_DIR)/lattice.o $(SRC_DIR)/keyboard_model.o $(TEST_DIR)/test_lattice.o
	@mkdir -p $(BIN_DIR)
	$(CXX) -o $@ $^ $(LDFLAGS)
	@echo "Built test lattice executable: $@"

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

test: all
	cd $(BIN_DIR) && ./test_lattice
	cd $(BIN_DIR) && ./test_speller
	cd $(BIN_DIR) && ./test_bigram
	cd $(BIN_DIR) && ./test_llm_provider
	cd $(BIN_DIR) && ./test_engine

clean:
	rm -f $(SRC_DIR)/*.o $(SRC_DIR)/*.d $(TEST_DIR)/*.o $(TEST_DIR)/*.d $(LIB_TARGET) $(TEST_ENGINE) $(TEST_SPELLER) $(TEST_BIGRAM) $(TEST_LLM) $(TEST_LATTICE)

-include $(DEPS)

.PHONY: all clean test

