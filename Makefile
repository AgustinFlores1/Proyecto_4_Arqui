# Copyright 2026 Universidad de los Andes.
# Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
# you may not use this file except in compliance with the License.
# SPDX-License-Identifier: SHL-0.51
#
# Course: Arquitectura de Computadores (2026)
#
# Authors:
# - Nicolás Villegas <navillegas@miuandes.cl>

# Configuration
TOP  := pochoco_soc
PCF  := goboard.pcf

# RTL Sources
SRC  := $(wildcard ./rtl/*.v ./rtl/**/*.v)

# Build Targets
JSON := $(TOP).json
ASC  := $(TOP).asc
BIN  := $(TOP).bin

# Assembly Sources
SS   ?= sw/trade.s
HEX  ?= sw/trade.hex

.PHONY: all prog clean asm sim

# Default target
all: asm prog

# Step 1: Synthesis using Yosys
$(JSON): $(SRC) $(HEX)
	yosys -p "read_verilog $(SRC); chparam -set MemFile \"$(HEX)\" $(TOP); synth_ice40 -top $(TOP) -json ${TOP}.json; stat"

# Step 2: Place and Route using NextPNR
$(ASC): $(JSON) $(PCF)
	nextpnr-ice40 --hx1k --package vq100 --freq 25 --json $(JSON) --pcf $(PCF) --asc $(ASC)

# Step 3: Bitstream Generation
$(BIN): $(ASC)
	icepack $(ASC) $(BIN)

# Step 4: Flash the Board
prog: $(BIN)
	iceprog $(BIN)

# Assembles trade.s into trade.hex
$(HEX): $(SS)
	python3 tools/assembler.py $(SS) -o $(HEX)

asm: $(HEX)

# Runs the course testbench (tb/tb_proyecto_4.sv)
sim: asm
	iverilog -g2012 -s tb_proyecto_4 -P'tb_proyecto_4.PROGRAMA="$(HEX)"' -o tb_p4 $$(yosys-config --datdir)/ice40/cells_sim.v $(SRC) tb/tb_proyecto_4.sv
	vvp -n tb_p4

sim_reset: asm
	iverilog -g2012 -s tb_reset -P'tb_reset.PROGRAMA="$(HEX)"' -o tb_reset $$(yosys-config --datdir)/ice40/cells_sim.v $(SRC) tb/tb_reset.sv
	vvp -n tb_reset

sim_sma:
	iverilog -g2012 -s tb_sma -o tb_sma $$(yosys-config --datdir)/ice40/cells_sim.v $(SRC) tb/tb_sma.sv
	vvp -n tb_sma

# Clean up generated files
clean:
	rm -f $(JSON) $(ASC) $(BIN) $(HEX) tb_p4 tb_reset tb_sma