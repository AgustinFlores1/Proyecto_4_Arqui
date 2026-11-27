// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// 
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>

// Modificado (Proyecto 4, variante B): el operador pasa de 4 a 5 bits para agregar dos
// operaciones a la medida de CruceMedias (instrucciones custom-0, solo con USAR_CUSTOM):
//   ALU_DIF  : result = 4*a - b            (D = 4*S_c - S_l en una instrucción)
//   ALU_CIRC : result = (a + b) & 0x7C     (índice del buffer circular: suma y vuelta a 0 en una instrucción)

module espino_alu (
  input  wire [4:0]  operator_i,
  input  wire [31:0] operand_a_i,
  input  wire [31:0] operand_b_i,
  output reg  [31:0] result_o,
  output reg         cmp_result_o
);

  localparam [4:0] ALU_ADD  = 5'd0,
                   ALU_SUB  = 5'd1,
                   ALU_XOR  = 5'd2,
                   ALU_OR   = 5'd3,
                   ALU_AND  = 5'd4,
                   ALU_SLL  = 5'd5,
                   ALU_SRL  = 5'd6,
                   ALU_SRA  = 5'd7,
                   ALU_SLT  = 5'd8,
                   ALU_SLTU = 5'd9,
                   ALU_EQ   = 5'd10,
                   ALU_NE   = 5'd11,
                   ALU_LT   = 5'd12,
                   ALU_GE   = 5'd13,
                   ALU_LTU  = 5'd14,
                   ALU_GEU  = 5'd15,
                   ALU_DIF  = 5'd16,   // custom-0: 4*a - b
                   ALU_CIRC = 5'd17;   // custom-0: (a + b) & 0x7C

  wire signed [31:0] a_s;
  wire signed [31:0] b_s;
  assign a_s = operand_a_i;
  assign b_s = operand_b_i;

  wire [4:0] shamt;
  assign shamt = operand_b_i[4:0];

  // Comparisons
  wire cmp_eq, cmp_lt, cmp_ltu;
  assign cmp_eq  = (operand_a_i == operand_b_i);
  assign cmp_lt  = (a_s < b_s);
  assign cmp_ltu = (operand_a_i < operand_b_i);

  always @* begin
    case (operator_i)
      ALU_EQ:  cmp_result_o =  cmp_eq;
      ALU_NE:  cmp_result_o = ~cmp_eq;
      ALU_LT:  cmp_result_o =  cmp_lt;
      ALU_GE:  cmp_result_o = ~cmp_lt;
      ALU_LTU: cmp_result_o =  cmp_ltu;
      ALU_GEU: cmp_result_o = ~cmp_ltu;
      default: cmp_result_o = 1'b0;
    endcase
  end

  // Main result
  always @* begin
    case (operator_i)
      ALU_ADD:  result_o = operand_a_i + operand_b_i;
      ALU_SUB:  result_o = operand_a_i - operand_b_i;
      ALU_XOR:  result_o = operand_a_i ^ operand_b_i;
      ALU_OR:   result_o = operand_a_i | operand_b_i;
      ALU_AND:  result_o = operand_a_i & operand_b_i;
      ALU_SLT:  result_o = {31'b0, cmp_lt};
      ALU_SLTU: result_o = {31'b0, cmp_ltu};
`ifdef USAR_CUSTOM
      ALU_DIF:  result_o = {operand_a_i[29:0], 2'b00} - operand_b_i;   // 4*a: dos ceros a la derecha (solo cables)
      ALU_CIRC: result_o = (operand_a_i + operand_b_i) & 32'h0000_007C; // máscara 124: índices 0, 4, ..., 124
`endif
      // Shifts disabled to save LUTs
      // ALU_SLL:  result_o = operand_a_i << shamt;
      // ALU_SRL:  result_o = operand_a_i >> shamt;
      // ALU_SRA:  result_o = a_s >>> shamt;
      default:  result_o = operand_a_i + operand_b_i;
    endcase
  end

endmodule