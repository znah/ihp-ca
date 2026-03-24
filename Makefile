.PHONY: all build visualize sim

MACROS_CFG = src/placement.cfg
CONFIG_MERGED = src/config_merged.json

ifndef LIBRELANE_ROOT
  $(error LIBRELANE_ROOT is not defined. Please set it to your librelane directory)
endif

RUN_CMD = nix-shell $(LIBRELANE_ROOT) --run
PYTHON_TT = $(RUN_CMD) "python3 src/configure.py"
SIM_SRC = main.cpp src/project.v src/hvsync_generator.v

all: build visualize

# 1. Simulation (Verilator)
sim: $(SIM_SRC)
	@echo "Running simulation..."
	verilator --cc --exe --build -j 0 -O3 $(SIM_SRC) -LDFLAGS "-framework Cocoa" \
		-o demo -DSIM && obj_dir/demo

# 2. Merge configuration from info.yaml and config.json (sync with GHA) using official TT tools
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

# 4. Extract layout data for visualizer
visualize: layout_data.json

layout_data.json: build extract_layout.py
	@echo "Extracting layout data for visualizer..."
	$(RUN_CMD) "openroad -python -exit extract_layout.py"

