clear
SRC="main.cpp src/project.v src/hvsync_generator.v"
verilator --cc --exe --build -j 0 -O3 $SRC -LDFLAGS "-framework Cocoa" \
    -o demo -DSIM && obj_dir/demo