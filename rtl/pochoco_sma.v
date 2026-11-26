// pochoco_sma.v: periférico de media móvil para CruceMedias (variante A del co-diseño).
//
// Cada vez que llega un precio (start_i), actualiza en hardware:
//   - un buffer circular con los últimos 32 precios (en un bloque BRAM),
//   - s_l = suma de los últimos 32 precios,
//   - s_c = suma de los últimos 8 precios,
// y deja listo D = 4*s_c - s_l, con signo, 3 ciclos después de start_i.
// La CPU lee D y decide: compra si D > 64, vende si D < -64 (32 * margen 2).
//
// limpiar_i borra el buffer y las sumas (32 ciclos). También se hace solo al encender.
//
// Rangos: s_l <= 32*255 = 8160 (13 bits), s_c <= 8*255 = 2040 (11 bits),
//         D en [-8160, 8160] (14 bits con signo).
//
// Para ahorrar celdas lógicas:
//   - no guarda una copia del precio: precio_i viene de price_q del SPI slave,
//     que no cambia hasta el próximo precio;
//   - un solo restador (delta = precio - precio viejo) sirve para las dos sumas:
//     en LEER32 el viejo es el de hace 32 ticks, en LEER8 el de hace 8.

module pochoco_sma (
  input  wire               clk_i,
  input  wire               rst_ni,      // reset activo en bajo

  input  wire               start_i,     // pulso de 1 ciclo: llegó un precio (byte_done)
  input  wire [7:0]         precio_i,    // el precio recibido; estable desde el ciclo siguiente a start_i
  input  wire               limpiar_i,   // pulso de 1 ciclo: borrar buffer y sumas

  output wire signed [13:0] d_o,         // D = 4*s_c - s_l
  output wire               ocupado_o    // 1 mientras actualiza o limpia
);

  // Estados
  localparam [1:0] REPOSO  = 2'd0,       // esperando un precio
                   LEER32  = 2'd1,       // llegó el precio de hace 32 ticks: se actualiza s_l
                   LEER8   = 2'd2,       // llegó el precio de hace 8 ticks: se actualiza s_c y se guarda el nuevo
                   LIMPIAR = 2'd3;       // escribiendo ceros en el buffer

  reg  [1:0]  estado;                    // estado actual
  reg  [4:0]  idx;                       // posición del precio más viejo (0-31); contador en LIMPIAR
  reg  [12:0] s_l;                       // suma de los últimos 32 precios
  reg  [10:0] s_c;                       // suma de los últimos 8 precios

  // ---------------------------------------------------------------------------
  // Buffer de 32 precios: lectura sincrónica y un solo puerto -> 1 bloque BRAM
  // ---------------------------------------------------------------------------
  (* ram_style = "block" *)
  reg  [7:0]  mem [0:31];                // los últimos 32 precios
  reg  [7:0]  rdata;                     // dato leído (llega un ciclo después de raddr)
  reg  [4:0]  raddr;                     // dirección de lectura
  reg         we;                        // habilita la escritura
  reg  [7:0]  wdata;                     // dato a escribir (la dirección de escritura siempre es idx)

  always @(posedge clk_i) begin
    if (we) mem[idx] <= wdata;
    rdata <= mem[raddr];
  end

  // Qué se lee y qué se escribe en cada estado (combinacional)
  always @(*) begin
    raddr = idx;                         // REPOSO: siempre apuntando al más viejo, listo para leerlo
    we    = 1'b0;
    wdata = precio_i;
    case (estado)
      LEER32:  raddr = idx + 5'd24;      // idx + 24 = idx - 8 en 5 bits: el precio de hace 8 ticks
      LEER8:   we = 1'b1;                // mem[idx] = precio (reemplaza al de hace 32 ticks)
      LIMPIAR: begin we = 1'b1; wdata = 8'd0; end   // mem[idx] = 0
      default: ;
    endcase
  end

  // Un solo restador para las dos sumas: precio nuevo - precio que sale (de -255 a 255, 9 bits con signo)
  wire [8:0] delta = {1'b0, precio_i} - {1'b0, rdata};

  // ---------------------------------------------------------------------------
  // Máquina de estados
  // ---------------------------------------------------------------------------
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      estado <= LIMPIAR;                 // al encender, el buffer tiene basura: se limpia
      idx    <= 5'd0;
      s_l    <= 13'd0;
      s_c    <= 11'd0;
    end else if (limpiar_i) begin        // la CPU pidió reiniciar (tiene prioridad)
      estado <= LIMPIAR;
      idx    <= 5'd0;
      s_l    <= 13'd0;
      s_c    <= 11'd0;
    end else begin
      case (estado)
        REPOSO: if (start_i)             // ciclo 0: llegó el precio; rdata <= mem[idx] en este flanco
          estado <= LEER32;
        LEER32: begin                    // ciclo 1: rdata = precio de hace 32 ticks
          s_l    <= s_l + {{4{delta[8]}}, delta};   // s_l += precio - viejo32 (delta con signo extendido)
          estado <= LEER8;               // se pide mem[idx+24]
        end
        LEER8: begin                     // ciclo 2: rdata = precio de hace 8 ticks; se escribe mem[idx]
          s_c    <= s_c + {{2{delta[8]}}, delta};   // s_c += precio - viejo8
          idx    <= idx + 5'd1;          // de 31 pasa a 0 solo (5 bits)
          estado <= REPOSO;              // ciclo 3: D ya tiene el valor nuevo
        end
        LIMPIAR: begin                   // 32 ciclos: mem[0..31] = 0
          idx <= idx + 5'd1;
          if (idx == 5'd31) estado <= REPOSO;   // idx vuelve a 0
        end
      endcase
    end
  end

  // D = 4*s_c - s_l. Multiplicar por 4 son solo cables: dos ceros a la derecha.
  assign d_o       = $signed({1'b0, s_c, 2'b00}) - $signed({1'b0, s_l});
  assign ocupado_o = (estado != REPOSO);

endmodule
