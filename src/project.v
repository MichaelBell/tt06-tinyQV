/*
 * Copyright (c) 2024 Michael Bell
 * SPDX-License-Identifier: Apache-2.0
 */

`define default_netname none

module tt_um_MichaelBell_tinyQV (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

  // All output pins must be assigned. If not used, assign to 0.
  assign uo_out  = ui_in; // Placeholder

  // Bidirs are used for SPI interface
  wire [3:0] spi_data_in = {uio_in[5:4], uio_in[2:1]};
  wire [3:0] spi_data_out;
  wire [3:0] spi_data_oe;
  assign uio_out[5:4] = spi_data_out[3:2];
  assign uio_out[2:1] = spi_data_out[1:0];
  assign uio_oe = {2'b11, spi_data_oe[3:2], 1'b1, spi_data_oe[1:0], 1'b1};

  // CPU to memory controller wiring
  wire [23:1] instr_addr;
  wire        instr_fetch_restart;
  wire        instr_fetch_stall;
  wire        instr_fetch_started;
  wire        instr_fetch_stopped;
  wire [15:0] instr_data;
  wire        instr_ready;
  wire [27:0] data_addr;
  wire  [1:0] data_write_n;
  wire  [1:0] data_read_n;
  wire [31:0] data_to_write;
  wire        data_ready;
  wire [31:0] data_from_read;

  tinyqv_cpu cpu(
        .clk(clk),
        .rstn(rst_n),

        .instr_addr(instr_addr),
        .instr_fetch_restart(instr_fetch_restart),
        .instr_fetch_stall(instr_fetch_stall),

        .instr_fetch_started(instr_fetch_started),
        .instr_fetch_stopped(instr_fetch_stopped),
        .instr_data_in(instr_data),
        .instr_ready(instr_ready),

        .data_addr(data_addr),
        .data_write_n(data_write_n),
        .data_read_n(data_read_n),
        .data_out(data_to_write),

        .data_ready(data_ready),
        .data_in(data_from_read)
    );

  tinyqv_mem_ctrl mem(
        .clk(clk),
        .rstn(rst_n),

        .instr_addr(instr_addr),
        .instr_fetch_restart(instr_fetch_restart),
        .instr_fetch_stall(instr_fetch_stall),

        .instr_fetch_started(instr_fetch_started),
        .instr_fetch_stopped(instr_fetch_stopped),
        .instr_data(instr_data),
        .instr_ready(instr_ready),

        .data_addr(data_addr),
        .data_write_n(data_write_n),
        .data_read_n(data_read_n),
        .data_to_write(data_to_write),

        .data_ready(data_ready),
        .data_from_read(data_from_read),

        .spi_data_in(spi_data_in),
        .spi_data_out(spi_data_out),
        .spi_data_oe(spi_data_oe),
        .spi_flash_select(uio_out[0]),
        .spi_ram_a_select(uio_out[6]),
        .spi_ram_b_select(uio_out[7]),
        .spi_clk_out(uio_out[3])
    );

endmodule
