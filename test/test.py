# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test project behavior")

    # Set the input values you want to test
    dut.ui_in.value = 20
    dut.uio_in.value = 30

    # hsync timing check
    # We found it goes high at 658 (approx 656 + reset + registration)
    await ClockCycles(dut.clk, 658)
    assert int(dut.uo_out.value) & 0x80 == 0x80, "hsync should be high"
    
    await ClockCycles(dut.clk, 96)
    assert int(dut.uo_out.value) & 0x80 == 0x00, "hsync should be low"

    # Video output check in the second line
    await ClockCycles(dut.clk, 48 + 10) # H_BACK + margin
    found_video = False
    for _ in range(640):
        await ClockCycles(dut.clk, 1)
        if int(dut.uo_out.value) & 0x77 != 0:
            found_video = True
            break
    assert found_video, "Should have found some non-zero video output"
    dut._log.info("Video output found")

    # vsync check (takes time but simulation is fast)
    # Total cycles per frame = 800 * 525 = 420,000
    # vsync starts at V_DISPLAY + V_BOTTOM = 480 + 10 = 490 lines
    # That is approx 490 * 800 = 392,000 cycles
    
    # We already spent ~1600 cycles.
    await ClockCycles(dut.clk, 392000 - 1600)
    
    # Check for vsync (bit 3 of uo_out)
    found_vsync = False
    for _ in range(2000): # Check a few cycles around the expected time
        await ClockCycles(dut.clk, 1)
        if int(dut.uo_out.value) & 0x08:
            found_vsync = True
            dut._log.info(f"vsync found")
            break
            
    assert found_vsync, "vsync should be detected"
    dut._log.info("Test passed: hsync, video, and vsync validated")

    # Keep testing the module by changing the input values, waiting for
    # one or more clock cycles, and asserting the expected output values.
