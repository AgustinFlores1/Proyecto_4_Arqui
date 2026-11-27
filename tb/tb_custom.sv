// Testbench de las instrucciones custom-0 (variante B): decodificador + ALU.
//
// Arma las instrucciones como lo hace el ensamblador, las pasa por espino_decoder
// y espino_alu, y revisa:
//   - que el decodificador las reconozca (no ilegales, escriben rd, operando correcto),
//   - que la ALU calcule  dif: rd = 4*rs1 - rs2   y   circ: rd = (rs1 + imm) & 0x7C,
//   - que un funct3 no usado de custom-0 se marque como ilegal,
//   - que una instrucción normal (add) se siga decodificando igual.
//
// Correr desde la raíz del repositorio:  make sim_custom   (compila con -DUSAR_CUSTOM)

`timescale 1ns/1ps

module tb_custom;

  // Decodificador
  logic [31:0] instr;
  wire         ilegal;
  wire  [4:0]  operador;
  wire  [1:0]  sel_a;
  wire         sel_b;
  wire  [31:0] imm;
  wire         rf_we;

  espino_decoder u_dec (
    .instr_i(instr), .illegal_insn_o(ilegal),
    .alu_operator_o(operador), .alu_op_a_sel_o(sel_a), .alu_op_b_sel_o(sel_b),
    .imm_operand_o(imm), .imm_target_o(),
    .rf_we_o(rf_we), .rf_wd_sel_o(),
    .is_branch_o(), .is_jal_o(), .is_jalr_o(),
    .lsu_req_o(), .lsu_we_o(), .lsu_type_o(), .lsu_sign_o());

  // ALU, con el operando B elegido como en la etapa ID (registro o inmediato)
  logic [31:0] rs1_val, rs2_val;
  wire  [31:0] operando_b = sel_b ? imm : rs2_val;
  wire  [31:0] resultado;

  espino_alu u_alu (
    .operator_i(operador), .operand_a_i(rs1_val), .operand_b_i(operando_b),
    .result_o(resultado), .cmp_result_o());

  // Codificación igual que en tools/assembler.py
  function automatic logic [31:0] tipo_r(input [6:0] opcode, input [2:0] f3, input [6:0] f7,
                                         input [4:0] rd, input [4:0] rs1, input [4:0] rs2);
    return {f7, rs2, rs1, f3, rd, opcode};
  endfunction

  function automatic logic [31:0] tipo_i(input [6:0] opcode, input [2:0] f3,
                                         input [4:0] rd, input [4:0] rs1, input [11:0] inm);
    return {inm, rs1, f3, rd, opcode};
  endfunction

  localparam [6:0] CUSTOM0 = 7'h0b, OP = 7'h33;

  int errores_dif = 0, errores_circ = 0, errores_deco = 0;
  int inm;                                                                      // inmediato de circ

  initial begin
    // 1. dif con valores aleatorios (incluye negativos: rs2 > 4*rs1)
    for (int k = 0; k < 20000; k++) begin
      rs1_val = $urandom; rs2_val = $urandom;
      if (k < 10000) begin rs1_val = rs1_val % 3000; rs2_val = rs2_val % 9000; end   // rango de S_c y S_l
      instr = tipo_r(CUSTOM0, 3'b000, 7'b0, 5'd7, 5'd14, 5'd15);                  // dif x7, x14, x15
      #1;
      if (ilegal || !rf_we || sel_b != 1'b0) errores_deco++;
      if (resultado !== 4 * rs1_val - rs2_val) begin
        errores_dif++;
        if (errores_dif <= 5) $display("  dif: rs1 %0d rs2 %0d -> %0d (esperado %0d)",
                                        rs1_val, rs2_val, $signed(resultado), $signed(4 * rs1_val - rs2_val));
      end
    end

    // 2. circ con todos los índices del buffer y varios inmediatos
    for (int idx = 0; idx < 128; idx += 4) begin
      for (int j = 0; j < 7; j++) begin                                          // inmediatos: 4, 96, 0, 124, 128, -4, -32
        case (j)
          0: inm = 4;    1: inm = 96;   2: inm = 0;   3: inm = 124;
          4: inm = 128;  5: inm = -4;   default: inm = -32;
        endcase
        rs1_val = idx; rs2_val = 32'hDEAD_BEEF;                                    // rs2 no se usa
        instr = tipo_i(CUSTOM0, 3'b001, 5'd12, 5'd12, inm[11:0]);                  // circ x12, x12, inm
        #1;
        if (ilegal || !rf_we || sel_b != 1'b1) errores_deco++;
        if (resultado !== ((idx + inm) & 32'h7C)) begin
          errores_circ++;
          if (errores_circ <= 5) $display("  circ: idx %0d inm %0d -> %0d (esperado %0d)",
                                           idx, inm, resultado, (idx + inm) & 32'h7C);
        end
      end
    end

    // 3. funct3 no usado en custom-0: debe ser ilegal
    instr = tipo_r(CUSTOM0, 3'b010, 7'b0, 5'd1, 5'd2, 5'd3);
    #1;
    if (!ilegal) errores_deco++;

    // 4. Una instrucción normal sigue igual: add x1, x2, x3
    rs1_val = 32'd1000; rs2_val = 32'd234;
    instr = tipo_r(OP, 3'b000, 7'b0, 5'd1, 5'd2, 5'd3);
    #1;
    if (ilegal || resultado !== 32'd1234) errores_deco++;

    if (errores_dif == 0)  $display("PASS dif rd, rs1, rs2 = 4*rs1 - rs2 en 20000 casos");
    else                   $display("FAIL dif: %0d errores", errores_dif);
    if (errores_circ == 0) $display("PASS circ rd, rs1, imm = (rs1 + imm) & 0x7C en todos los indices");
    else                   $display("FAIL circ: %0d errores", errores_circ);
    if (errores_deco == 0) $display("PASS decodificacion (custom-0 validas, funct3 invalido, add normal)");
    else                   $display("FAIL decodificacion: %0d errores", errores_deco);
    $finish;
  end

endmodule
