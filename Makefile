.PHONY: all build

MACROS_CFG = src/placement.cfg
CONFIG_MERGED = src/config_merged.json
RUN_CMD = nix-shell ~/reps/2026/librelane/ --run
PYTHON_TT = $(RUN_CMD) "python3 src/configure.py"

all: build

# 1. Merge configuration from info.yaml and config.json (sync with GHA) using official TT tools
$(CONFIG_MERGED): info.yaml src/config.json src/configure.py
	@echo "Merging configuration using standalone script..."
	$(PYTHON_TT)

# 2. Run placement generator (rerun if GRID_W changes in project.v)
$(MACROS_CFG): src/gen_placement.py src/project.v
	@echo "Generating placement mapping..."
	python3 src/gen_placement.py

# 3. Run the LibreLane flow
build: $(CONFIG_MERGED) $(MACROS_CFG) src/project.v src/hvsync_generator.v
	@echo "Running implementation flow..."
	$(RUN_CMD) "python3 -m librelane --pdk ihp-sg13g2 --run-tag precise_place --overwrite $(CONFIG_MERGED)"

