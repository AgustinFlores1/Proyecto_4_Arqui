// Testbench del botón de reset: igual que tb_proyecto_4.sv, pero presiona un botón
// de la placa entre dos ticks y revisa que trade.s vuelva a empezar de cero.
//
// Correr desde la raíz del repositorio:
//   make sim_reset
// y comparar con el emulador:
//   python trading_sim/emular.py sw/trade.hex tb/practica.csv --ticks 2000 --reset 500
//   diff decisiones_reset.csv decisiones_python.csv
//
// Qué se espera en tb/practica.csv con RESET_TICK = 500:
//   - En el tick 500 el algoritmo tiene acciones (compró en el 455).
//   - Al reiniciar, trade.s olvida eso: comprado = 0, buffer y sumas en 0.
//   - Durante los 31 ticks siguientes no opera (calentamiento de 32 precios).
//   - Su primera orden después del reset es COMPRAR (0x7F), aunque la maestra
//     todavía le tiene acciones: es la prueba de que el flag se borró.
//     (Sin reset, su siguiente orden habría sido VENDER en el tick 638.)

`timescale 1ns/1ps

module tb_reset;

  // Configuración
  parameter string PROGRAMA   = "sw/trade.hex";
  localparam string SERIE      = "tb/practica.csv";
  localparam int    PERIODO_NS = 100000;   // ronda 3
  localparam int    NTICKS     = 2000;
  localparam int    RESET_TICK = 500;      // el botón se presiona después de este tick
  localparam int    BOTON_NS   = 20000;    // cuánto tiempo se mantiene presionado (500 ciclos)

  localparam int CAJA0    = 10000;
  localparam int COMISION = 5;
  localparam int SPI_NS   = 9500;

  // Pochoco SoC a 25 MHz
  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  logic [3:0] botones = 4'b0000;           // botones de la placa (1 = presionado)
  wire  miso;

  pochoco_soc #(.MemFile(PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(botones),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // Lee la serie de precios
  int precio [20000];

  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(SERIE, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", SERIE); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < NTICKS; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask

  // SPI modo 0 (igual que el testbench del curso)
  int bits_x = 0;

  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  // Contabilidad oficial (igual que el testbench del curso; la maestra NO se reinicia)
  int caja = CAJA0, acciones = 0, w = CAJA0, peak = CAJA0, max_dd = 0;
  int ordenes = 0;

  task automatic ejecutar(input logic [7:0] decision, input int p);
    int q = decision[5:0];
    case (decision[7:6])
      2'b01: begin
        if (q > (caja - COMISION) / p) q = (caja - COMISION) / p;
        if (q > 0) begin caja -= q * p + COMISION; acciones += q; ordenes++; end
      end
      2'b10: begin
        if (q > acciones) q = acciones;
        if (q > 0 && caja + q * p >= COMISION) begin caja += q * p - COMISION; acciones -= q; ordenes++; end
      end
      default: ;
    endcase
    w = caja + acciones * p;
    if (w > peak) peak = w;
    if (peak - w > max_dd) max_dd = peak - w;
  endtask

  // Ciclos entre el precio y DECISION, y precios no leídos
  int ciclos = 0, peor_caso = 0, respuestas = 0, precios_perdidos = 0;
  bit esperando = 0;

  always @(posedge clk) begin
    ciclos++;
    if (dut.u_spi.byte_done) begin
      if (dut.u_spi.new_price_q) precios_perdidos++;
      ciclos = 0;
      esperando = 1;
    end else if (esperando && dut.u_spi.wr && dut.u_spi.off == 2) begin
      if (ciclos > peor_caso) peor_caso = ciclos;
      respuestas++;
      esperando = 0;
    end
  end

  // Chequeos
  int total_tests = 0, tests_aprobados = 0;

  task automatic chequear(input bit ok, input string nombre);
    total_tests++;
    if (ok) begin tests_aprobados++; $display("PASS %s", nombre); end
    else $display("FAIL %s", nombre);
  endtask

  // Lo que se observa después del reset
  int         ordenes_calentamiento = 0;   // decisiones distintas de 00 durante el calentamiento
  logic [7:0] primera = 8'h00;             // primera decisión distinta de 00 después del calentamiento
  bit         vista = 0;

  // Simulación
  logic [7:0] decision;
  int fd;

  initial begin
    leer_serie();
    fd = $fopen("decisiones_reset.csv", "w");
    $fdisplay(fd, "tick,precio,decision,caja,acciones,patrimonio");
    #4000;

    for (int n = 0; n < NTICKS; n++) begin
      spi(precio[n], decision);
      ejecutar(decision, precio[n]);
      $fdisplay(fd, "%0d,%0d,%02h,%0d,%0d,%0d", n, precio[n], decision, caja, acciones, w);

      // La decisión leída en el tick n es la respuesta al precio n-1.
      // Tras el reset, los precios RESET_TICK+1 .. RESET_TICK+31 son de calentamiento,
      // así que las decisiones leídas en los ticks RESET_TICK+2 .. RESET_TICK+32 deben ser 00.
      if (n >= RESET_TICK + 2 && n <= RESET_TICK + 32 && decision != 8'h00) ordenes_calentamiento++;
      if (n > RESET_TICK + 32 && !vista && decision != 8'h00) begin primera = decision; vista = 1; end

      if (n == RESET_TICK) begin
        $display("Tick %0d: botón presionado (la maestra tiene %0d acciones del grupo)", n, acciones);
        botones = 4'b0001;
        #(BOTON_NS);
        botones = 4'b0000;
        #(PERIODO_NS - SPI_NS - BOTON_NS);
      end else begin
        #(PERIODO_NS - SPI_NS);
      end
    end
    $fclose(fd);

    $display("Patrimonio final:          %0d", w);
    $display("Ordenes ejecutadas:        %0d", ordenes);
    $display("Primera orden tras reset:  %02h", primera);
    $display("Detalle por tick en decisiones_reset.csv");

    chequear(bits_x == 0,                 "MISO sin valores X");
    chequear(precios_perdidos == 0,       "el programa lee todos los precios (también después del reset)");
    chequear(peor_caso < (PERIODO_NS - SPI_NS) / 40, "la decision llega antes del siguiente tick");
    chequear(ordenes_calentamiento == 0,  "tras el reset no opera durante el calentamiento");
    chequear(primera == 8'h7F,            "la primera orden tras el reset es comprar (olvido que tenia acciones)");

    $display("Testbenchs aprobados: %0d/%0d", tests_aprobados, total_tests);
    $finish;
  end

endmodule
