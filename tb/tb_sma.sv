// Testbench del periférico de media móvil (pochoco_sma.v), solo el módulo.
//
// Le entrega los precios de tb/practica.csv uno por uno y, en cada precio, compara D
// con un modelo de referencia escrito aquí mismo (las mismas cuentas, con enteros).
// También prueba: la latencia (D listo 3 ciclos después del precio), el reinicio
// (limpiar_i) a mitad de la serie y los valores extremos de D.
//
// Correr desde la raíz del repositorio:  make sim_sma

`timescale 1ns/1ps

module tb_sma;

  localparam string SERIE      = "tb/practica.csv";
  localparam int    NTICKS     = 20000;
  localparam int    TICK_RESET = 500;          // después de este precio se reinicia el periférico

  // Reloj de 25 MHz
  logic clk = 0;
  always #20 clk = ~clk;

  logic              rst_n   = 0;
  logic              start   = 0;
  logic [7:0]        precio  = 0;
  logic              limpiar = 0;
  wire signed [13:0] d;
  wire               ocupado;

  pochoco_sma dut (
    .clk_i(clk), .rst_ni(rst_n),
    .start_i(start), .precio_i(precio), .limpiar_i(limpiar),
    .d_o(d), .ocupado_o(ocupado));

  // ---------------------------------------------------------------------------
  // Modelo de referencia: buffer de 32 precios y las dos sumas
  // ---------------------------------------------------------------------------
  int ref_mem [32];                  // últimos 32 precios
  int ref_idx = 0;                   // posición del más viejo
  int ref_sl  = 0;                   // suma de 32
  int ref_sc  = 0;                   // suma de 8

  task automatic ref_limpiar;
    for (int i = 0; i < 32; i++) ref_mem[i] = 0;
    ref_idx = 0; ref_sl = 0; ref_sc = 0;
  endtask

  task automatic ref_precio(input int p);
    ref_sl = ref_sl + p - ref_mem[ref_idx];                 // sale el de hace 32 ticks
    ref_sc = ref_sc + p - ref_mem[(ref_idx + 24) % 32];     // sale el de hace 8 ticks
    ref_mem[ref_idx] = p;
    ref_idx = (ref_idx + 1) % 32;
  endtask

  function automatic int ref_d();
    return 4 * ref_sc - ref_sl;
  endfunction

  // ---------------------------------------------------------------------------
  // Estímulos
  // ---------------------------------------------------------------------------
  int errores_d = 0, errores_latencia = 0, d_min = 0, d_max = 0;

  // Entrega un precio como lo hace el SPI slave: start y precio durante 1 ciclo.
  // Revisa que después de exactamente 3 flancos el periférico esté libre y D sea correcto.
  task automatic enviar(input int p, input int n);
    @(negedge clk);
    start = 1; precio = p[7:0];
    @(negedge clk);
    start = 0;
    ref_precio(p);
    @(posedge clk); @(posedge clk); #1;                      // 3 flancos desde que se tomó start
    if (ocupado) begin
      errores_latencia++;
      if (errores_latencia <= 5) $display("  latencia: tick %0d, sigue ocupado 3 ciclos después", n);
    end
    if (d !== ref_d()) begin
      errores_d++;
      if (errores_d <= 5) $display("  D distinto: tick %0d, precio %0d, D = %0d, esperado %0d", n, p, d, ref_d());
    end
    if (ref_d() < d_min) d_min = ref_d();
    if (ref_d() > d_max) d_max = ref_d();
  endtask

  // Pide un reinicio y cuenta cuántos ciclos queda ocupado
  task automatic reiniciar(output int ciclos);
    @(negedge clk);
    limpiar = 1;
    @(negedge clk);
    limpiar = 0;
    ref_limpiar();
    ciclos = 0;                                              // flancos que pasa en LIMPIAR
    while (ocupado) begin @(negedge clk); ciclos++; end
  endtask

  // ---------------------------------------------------------------------------
  // Serie de precios
  // ---------------------------------------------------------------------------
  int serie [20000];

  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(SERIE, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", SERIE); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < NTICKS; n++) r = $fscanf(fd, "%d,%d\n", t, serie[n]);
    $fclose(fd);
  endtask

  // Chequeos
  int total_tests = 0, tests_aprobados = 0;

  task automatic chequear(input bit ok, input string nombre);
    total_tests++;
    if (ok) begin tests_aprobados++; $display("PASS %s", nombre); end
    else $display("FAIL %s", nombre);
  endtask

  int ciclos_encendido = 0, ciclos_reset = 0, errores_extremos;
  int d_tras_reset;

  initial begin
    leer_serie();
    ref_limpiar();

    // Encendido: el periférico arranca limpiando su buffer
    #100 rst_n = 1;
    while (ocupado) begin @(negedge clk); ciclos_encendido++; end

    // 1. La serie completa, con un reinicio en TICK_RESET
    for (int n = 0; n < NTICKS; n++) begin
      enviar(serie[n], n);
      if (n == TICK_RESET) begin
        reiniciar(ciclos_reset);
        d_tras_reset = d;
      end
      repeat (5) @(negedge clk);                             // separación entre precios (en la placa es mucho mayor)
    end

    // 2. Valores extremos: 24 precios en 1 y 8 en 255 (D máximo), luego 8 en 1 (D muy negativo)
    errores_extremos = errores_d;
    reiniciar(ciclos_reset);
    for (int i = 0; i < 24; i++) enviar(1, -1);
    for (int i = 0; i < 8;  i++) enviar(255, -1);
    for (int i = 0; i < 24; i++) enviar(255, -1);
    for (int i = 0; i < 8;  i++) enviar(1, -1);
    errores_extremos = errores_d - errores_extremos;

    $display("Ciclos limpiando al encender: %0d", ciclos_encendido);
    $display("Ciclos limpiando al reiniciar: %0d", ciclos_reset);
    $display("D en la serie: minimo %0d, maximo %0d", d_min, d_max);

    chequear(errores_d == 0,             "D igual al modelo de referencia en todos los precios");
    chequear(errores_latencia == 0,      "D listo 3 ciclos despues de cada precio");
    chequear(ciclos_reset == 32 && d_tras_reset == 0, "el reinicio borra las sumas y dura 32 ciclos");
    chequear(errores_extremos == 0,      "D correcto con precios extremos (1 y 255)");

    $display("Testbenchs aprobados: %0d/%0d", tests_aprobados, total_tests);
    $finish;
  end

endmodule
