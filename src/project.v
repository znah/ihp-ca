/*
 * Copyright (c) 2024 Alexander Mordvintsev
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_vga_ca(
  input  wire [7:0] ui_in,    // Dedicated inputs
  output wire [7:0] uo_out,   // Dedicated outputs
  input  wire [7:0] uio_in,   // IOs: Input path
  output wire [7:0] uio_out,  // IOs: Output path
  output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
  input  wire       ena,      // always 1 when the design is powered, so you can ignore it
  input  wire       clk,      // clock
  input  wire       rst_n     // reset_n - low to reset
);

  // VGA signals
  wire hsync;
  wire vsync;
  wire [1:0] R;
  wire [1:0] G;
  wire [1:0] B;
  wire video_active;
  wire [9:0] pix_x;
  wire [9:0] pix_y;

  // TinyVGA PMOD
  assign uo_out = {hsync, B[0], G[0], R[0], vsync, B[1], G[1], R[1]};

  // Unused outputs assigned to 0.
  assign uio_out = 0;
  assign uio_oe  = 0;

  // Suppress unused signals warning
  wire _unused_ok = &{ena, ui_in, uio_in};

  hvsync_generator hvsync_gen(
    .clk(clk),
    .reset(~rst_n),
    .hsync(hsync),
    .vsync(vsync),
    .display_on(video_active),
    .hpos(pix_x),
    .vpos(pix_y)
  );
  
  parameter logCELL_SIZE = 2;
  parameter CELL_SIZE = 1<<logCELL_SIZE;
  parameter WIDTH = 640;
  parameter HEIGHT = 480;
  parameter GRID_W = 136;
  parameter PAD_LEFT = (WIDTH-GRID_W*CELL_SIZE)/2;
  
  wire [9:0] x = pix_x-PAD_LEFT;
  wire [7:0] cell_x = x[9:logCELL_SIZE];

  wire [logCELL_SIZE-1:0] fract_x = x[logCELL_SIZE-1:0];
  wire [logCELL_SIZE-1:0] fract_y = pix_y[logCELL_SIZE-1:0];
  
  parameter L = GRID_W-1;
  `ifdef PDK_ihp_sg13g2
    `define BUF(name) sg13g2_dlygate4sd3_1 name``buf_[L:0] ( .X(name``_buf), .A(name) );
    `define CLKGATE(name, en) \
      wire name``_gclk; \
      sg13g2_lgcp_1 name``_cg (.GATE(en), .CLK(clk), .GCLK(name``_gclk));
    `define DFF(name) \
      wire [L:0] name; \
      sg13g2_dfrbpq_1 name``_reg[L:0] ( .CLK(name``_gclk), .D(name``_next), .Q(name), .RESET_B(ena) );
  `elsif PDK_sky130A
    `define BUF(name) sky130_fd_sc_hd__dlygate4sd3_1 name``buf_[L:0] ( .X(name``_buf), .A(name) );
    `define CLKGATE(name, en) \
      wire name``_gclk; \
      sky130_fd_sc_hd__sdlclkp name``_cg (.GATE(en), .CLK(clk), .GCLK(name``_gclk), .SCE(1'b0));
    `define DFF(name) \
      wire [L:0] name; \
      sky130_fd_sc_hd__dfrtp_1 name``_reg[L:0] ( .CLK(name``_gclk), .D(name``_next), .Q(name), .RESET_B(1'b1) );
  `else
    `define BUF(name) assign name``_buf = name
    `define CLKGATE(name, en) \
      reg name``_latchen; \
      /* verilator lint_off LATCH */ \
      always @(*) if (!clk) name``_latchen = en; \
      /* verilator lint_on LATCH */ \
      wire name``_gclk = clk && name``_latchen;
    `define DFF(name) \
      reg [L:0] name``_reg; \
      always @(posedge name``_gclk) name``_reg <= name``_next; \
      wire [L:0] name = name``_reg;
  `endif

  `define REG(name, en) `CLKGATE(name, en) wire[L:0] name``_next; `DFF(name) wire[L:0] name``_buf; `BUF(name)

  `define HEAD(data) data``_next[0]
  `define TAIL(data,i) data``_buf[L-(i)]

  wire cells_en = in_grid && fract_x==0;
  `REG(cells, cells_en);
  `REG(first_row_cells, cells_en && (pix_y == 0 || pix_y == CELL_SIZE));
  reg left;
  wire center = `TAIL(cells, 0);
  wire right = `TAIL(cells, 1);

  reg [10:0] row_count;
  wire [5:0] rule_i = (row_count[10:5] ^ {3'b00, cell_x[7:5]});
  wire [7:0] rule = rule_i*173;
  wire [5:0] rule_color = rule[6:1];
  
  wire seed_cell = cell_x == GRID_W/2;
  wire first_row_cell_val = row_count==0 ? seed_cell : `TAIL(first_row_cells, 0);
  wire rule_cell = fract_y==0 ? rule[{left,center,right}] : center;
  wire new_cell = pix_y==0 ? first_row_cell_val : rule_cell;

  wire in_grid = cell_x < GRID_W && video_active;
  wire row_end = pix_x == WIDTH;

  // Hardwired shift registers to avoid MUXes (uses gated clocks via REG macros)
  assign cells_next = {cells_buf[L-1:0], new_cell};
  assign first_row_cells_next = {first_row_cells_buf[L-1:0], new_cell};

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      row_count <= 0;
      left <= 0;
    end else begin
      if (row_end && pix_y<HEIGHT && &fract_y) begin
        row_count <= row_count+1;
      end else if (row_end && pix_y==HEIGHT) begin
        row_count <= row_count-HEIGHT/CELL_SIZE+1;
      end

      if (in_grid && fract_x==0) begin
        left <= `TAIL(cells, 0);
      end
    end
  end

  wire c = `HEAD(cells) & in_grid;
  wire [5:0] color = c ? rule_color : 6'b000000;

  assign R = color[5:4];
  assign G = color[3:2];
  assign B = color[1:0];
endmodule
