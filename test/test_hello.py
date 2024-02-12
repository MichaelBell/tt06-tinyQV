# SPDX-FileCopyrightText: © 2024 Michael Bell
# SPDX-License-Identifier: MIT

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from test_util import reset

async def receive_string(dut, str):
    for char in str:
        dut._log.info(f"Wait for: {char}")

        for _ in range(5000):
            await ClockCycles(dut.clk, 8)
            if dut.uart_tx.value == 0:
                break
        else:
            # Should have started by now
            assert dut.uart_tx.value == 0
        
        uart_byte = ord(char)
        bit_time = 8680
        await Timer(bit_time / 2, "ns")
        assert dut.uart_tx.value == 0
        for i in range(8):
            await Timer(bit_time, "ns")
            assert dut.uart_tx.value == (uart_byte & 1)
            uart_byte >>= 1
        await Timer(bit_time, "ns")
        assert dut.uart_tx.value == 1

@cocotb.test()
async def test_hello(dut):
    dut._log.info("Start")
  
    # Our example module doesn't use clock and reset, but we show how to use them here anyway.
    clock = Clock(dut.clk, 15, units="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)

    # Should output: Hello, world!\n
    await receive_string(dut, "Hello, world!\n\r")

    await receive_string(dut, "Hello 1\n\r")
    await receive_string(dut, "Hello 2\n\r")
