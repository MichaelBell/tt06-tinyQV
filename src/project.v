/*
 * Copyright (c) 2024 Michael Bell
 * SPDX-License-Identifier: Apache-2.0
 */

`define default_netname none

module tt_um_MichaelBell_tinyQV (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
/*verilator lint_off UNUSEDSIGNAL*/
    input  wire [7:0] uio_in,   // IOs: Input path - only some bits used
/*verilator lint_on UNUSEDSIGNAL*/
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
/*verilator lint_off UNUSEDSIGNAL*/
    input  wire       ena,
/*verilator lint_on UNUSEDSIGNAL*/
    input  wire       clk,
    input  wire       rst_n
);

    // Register the reset on the negative edge of clock for safety.
    // This also allows the option of async reset in the design, which might be preferable in some cases
    reg rst_reg_n;
    always @(negedge clk) rst_reg_n <= rst_n;

    // Bidirs are used for SPI interface
    wire [3:0] qspi_data_in = {uio_in[5:4], uio_in[2:1]};
    wire [3:0] qspi_data_out;
    wire [3:0] qspi_data_oe;
    wire       qspi_clk_out;
    wire       qspi_flash_select;
    wire       qspi_ram_a_select;
    wire       qspi_ram_b_select;
    assign uio_out = {qspi_ram_b_select, qspi_ram_a_select, qspi_data_out[3:2], 
                      qspi_clk_out, qspi_data_out[1:0], qspi_flash_select};
    assign uio_oe = rst_n ? {2'b11, qspi_data_oe[3:2], 1'b1, qspi_data_oe[1:0], 1'b1} : 8'h00;

    wire [27:0] addr;
    wire  [1:0] write_n;
    wire  [1:0] read_n;
/*verilator lint_off UNUSEDSIGNAL*/
    wire [31:0] data_to_write;  // Currently only bottom byte used.
/*verilator lint_on UNUSEDSIGNAL*/

    wire        data_ready;
    reg [31:0] data_from_read;

    tinyQV i_tinyqv(
        .clk(clk),
        .rstn(rst_reg_n),

        .data_addr(addr),
        .data_write_n(write_n),
        .data_read_n(read_n),
        .data_out(data_to_write),

        .data_ready(data_ready),
        .data_in(data_from_read),

        .spi_data_in(qspi_data_in),
        .spi_data_out(qspi_data_out),
        .spi_data_oe(qspi_data_oe),
        .spi_clk_out(qspi_clk_out),
        .spi_flash_select(qspi_flash_select),
        .spi_ram_a_select(qspi_ram_a_select),
        .spi_ram_b_select(qspi_ram_b_select)
    );

    // Peripheral IOs on ui_in and uo_out
/*verilator lint_off UNUSEDSIGNAL*/
    wire [1:0] interrupt = ui_in[1:0];  // TODO
    wire       spi_miso  = ui_in[2];    // TODO
/*verilator lint_on UNUSEDSIGNAL*/
    wire       uart_rxd  = ui_in[3];

    wire       spi_cs;
    wire       spi_sck;
    wire       spi_mosi;
    wire       spi_dc;
    wire       uart_txd;
    wire       uart_rts;
    reg  [1:0] gpio_out;

    assign uo_out[0] = spi_cs;
    assign uo_out[1] = spi_sck;
    assign uo_out[2] = spi_mosi;
    assign uo_out[3] = spi_dc;
    assign uo_out[4] = uart_txd;
    assign uo_out[5] = uart_rts;
    assign uo_out[7:6] = gpio_out;

    // Address to peripheral map
    localparam PERI_NONE = 0;
    localparam PERI_GPIO_OUT = 2;
    localparam PERI_GPIO_IN = 3;
    localparam PERI_UART = 4;
    localparam PERI_UART_STATUS = 5;
    localparam PERI_SPI = 6;
    localparam PERI_SPI_STATUS = 7;

    reg [2:0] connect_peripheral;

    always @(*) begin
        if (addr == 28'h8000000) connect_peripheral = PERI_GPIO_OUT;
        else if (addr == 28'h8000004) connect_peripheral = PERI_GPIO_IN;
        else if (addr == 28'h8000010) connect_peripheral = PERI_UART;
        else if (addr == 28'h8000014) connect_peripheral = PERI_UART_STATUS;
        else if (addr == 28'h8000020) connect_peripheral = PERI_SPI;
        else if (addr == 28'h8000024) connect_peripheral = PERI_SPI_STATUS;
        else connect_peripheral = PERI_NONE;
    end

    // All transactions complete immediately
    assign data_ready = 1'b1;

    // Read data
    always @(*) begin
        case (connect_peripheral)
            PERI_GPIO_OUT:    data_from_read = {24'h0, uo_out};
            PERI_GPIO_IN:     data_from_read = {24'h0, ui_in};
            PERI_UART:        data_from_read = {24'h0, uart_rx_data};
            PERI_UART_STATUS: data_from_read = {30'h0, uart_rx_valid, uart_tx_busy};
            PERI_SPI:         data_from_read = {24'h0, spi_data};
            PERI_SPI_STATUS:  data_from_read = {31'h0, spi_busy};
            default:          data_from_read = 32'hFFFF_FFFF;
        endcase
    end

    // GPIO Out
    always @(posedge clk) begin
        if (!rst_reg_n) gpio_out <= 0;
        if (write_n != 2'b11 && connect_peripheral == PERI_GPIO_OUT) gpio_out <= data_to_write[7:6];
    end

    // UART
    wire uart_tx_busy;
    wire uart_rx_valid;
    wire [7:0] uart_rx_data;
    wire uart_tx_start = write_n != 2'b11 && connect_peripheral == PERI_UART;

    uart_tx #(.CLK_HZ(66_000_000), .BIT_RATE(115_200)) i_uart_tx(
        .clk(clk),
        .resetn(rst_reg_n),
        .uart_txd(uart_txd),
        .uart_tx_en(uart_tx_start),
        .uart_tx_data(data_to_write[7:0]),
        .uart_tx_busy(uart_tx_busy) 
    );

    uart_rx #(.CLK_HZ(66_000_000), .BIT_RATE(115_200)) i_uart_rx(
        .clk(clk),
        .resetn(rst_reg_n),
        .uart_rxd(uart_rxd),
        .uart_rts(uart_rts),
        .uart_rx_read(connect_peripheral == PERI_UART && read_n != 2'b11),
        .uart_rx_valid(uart_rx_valid),
        .uart_rx_data(uart_rx_data) 
    );

    // SPI
    wire spi_start = write_n != 2'b11 && connect_peripheral == PERI_SPI;
    wire [7:0] spi_data;
    wire spi_busy;

    spi_ctrl i_spi(
        .clk(clk),
        .rstn(rst_reg_n),

        .spi_miso(spi_miso),
        .spi_select(spi_cs),
        .spi_clk_out(spi_sck),
        .spi_mosi(spi_mosi),
        .spi_dc(spi_dc),

        .dc_in(data_to_write[9]),
        .end_txn(data_to_write[8]),
        .data_in(data_to_write[7:0]),
        .start(spi_start),
        .data_out(spi_data),
        .busy(spi_busy)
    );

endmodule
