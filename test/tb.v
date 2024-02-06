`default_nettype none `timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Dump the signals to a VCD file. You can view it with gtkwave.
  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  wire [3:0] spi_data_in;
  assign {uio_in[5:4], uio_in[2:1]} = spi_data_in;

  wire [3:0] spi_data_out = {uio_out[5:4], uio_out[2:1]};
  wire [3:0] spi_data_oe  = {uio_oe[5:4],  uio_oe[2:1]};
  wire spi_clk_out = uio_out[3];
  wire spi_flash_select = uio_out[0];
  wire spi_ram_a_select = uio_out[6];
  wire spi_ram_b_select = uio_out[7];

  wire uart_tx = uo_out[4];

  // Replace tt_um_example with your module name:
  tt_um_MichaelBell_tinyQV user_project (

      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(1'b1),
      .VGND(1'b0),
`endif

      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

endmodule
