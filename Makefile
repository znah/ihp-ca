.PHONY: all build

MACROS_CFG = src/placement.cfg
SRC_FILES = src/project.v src/hvsync_generator.v src/config_merged.json
RUN_CMD = nix-shell ~/reps/2026/librelane/ --run

all: build

# 1. Run placement generator
$(MACROS_CFG): src/gen_placement.py
	@echo "Generating placement mapping..."
	python3 src/gen_placement.py

# 2. Run the LibreLane flow
build: $(MACROS_CFG) $(SRC_FILES)
	@echo "Running implementation flow..."
	$(RUN_CMD) "python3 -m librelane --pdk ihp-sg13g2 --run-tag precise_place --overwrite src/config_merged.json"
