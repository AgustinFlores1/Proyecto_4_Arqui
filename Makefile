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

# Assembly Sources (se pueden cambiar desde la línea de comandos)
SS   ?= sw/trade.s
HEX  ?= sw/trade.hex

# Variante de hardware (se puede cambiar desde la línea de comandos):
#   DEF=                    solo software
#   DEF=-DUSAR_SMA          variante A: periférico de media móvil
#   DEF=-DUSAR_CUSTOM       variante B: instrucciones custom-0
DEF  ?=

.PHONY: all prog clean asm sim sim_reset sim_sma sim_custom

# Default target
all: asm prog

# Step 1: Synthesis using Yosys
$(JSON): $(SRC) $(HEX)
	yosys -p "read_verilog $(DEF) $(SRC); chparam -set MemFile \"$(HEX)\" $(TOP); synth_ice40 -top $(TOP) -json ${TOP}.json; stat"

# Step 2: Place and Route using NextPNR
$(ASC): $(JSON) $(PCF)
	nextpnr-ice40 --hx1k --package vq100 --freq 25 --json $(JSON) --pcf $(PCF) --asc $(ASC)

# Step 3: Bitstream Generation
$(BIN): $(ASC)
	icepack $(ASC) $(BIN)

# Step 4: Flash the Board
prog: $(BIN)
	iceprog $(BIN)

# Assembles $(SS) into $(HEX)
$(HEX): $(SS)
	python3 tools/assembler.py $(SS) -o $(HEX)

asm: $(HEX)

# Runs the course testbench (tb/tb_proyecto_4.sv)
sim: asm
	iverilog -g2012 $(DEF) -s tb_proyecto_4 -P'tb_proyecto_4.PROGRAMA="$(HEX)"' -o tb_p4 $$(yosys-config --datdir)/ice40/cells_sim.v $(SRC) tb/tb_proyecto_4.sv
	vvp -n tb_p4

# Reset button testbench (tb/tb_reset.sv)
sim_reset: asm
	iverilog -g2012 $(DEF) -s tb_reset -P'tb_reset.PROGRAMA="$(HEX)"' -o tb_reset $$(yosys-config --datdir)/ice40/cells_sim.v $(SRC) tb/tb_reset.sv
	vvp -n tb_reset

# Variante A: testbench del periférico de media móvil
sim_sma:
	iverilog -g2012 -s tb_sma -o tb_sma rtl/pochoco_sma.v tb/tb_sma.sv
	vvp -n tb_sma

# Variante B: testbench de las instrucciones custom-0 (decodificador + ALU)
sim_custom:
	iverilog -g2012 -DUSAR_CUSTOM -s tb_custom -o tb_custom rtl/espino_core/espino_decoder.v rtl/espino_core/espino_alu.v tb/tb_custom.sv
	vvp -n tb_custom

# Clean up generated files
clean:
	rm -f $(JSON) $(ASC) $(BIN) $(HEX) tb_p4 tb_reset tb_sma tb_custom
