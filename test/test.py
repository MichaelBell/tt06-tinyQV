# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from riscvmodel.insn import *
from riscvmodel.regnames import x0, x1, tp

select = None

async def start_read(dut, addr):
    global select

    if addr >= 0x1800000:
        select = dut.spi_ram_b_select
    elif addr >= 0x1000000:
        select = dut.spi_ram_a_select
    else:
        select = dut.spi_flash_select
    
    assert select.value == 0
    assert dut.spi_flash_select.value == 0 if dut.spi_flash_select == select else 1
    assert dut.spi_ram_a_select.value == 0 if dut.spi_ram_a_select == select else 1
    assert dut.spi_ram_b_select.value == 0 if dut.spi_ram_b_select == select else 1
    assert dut.spi_clk_out.value == 0
    assert dut.spi_data_oe.value == 1

    # Command
    cmd = 0xEB
    for i in range(8):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 1
        assert dut.spi_data_out.value == (1 if cmd & 0x80 else 0)
        assert dut.spi_data_oe.value == 1
        cmd <<= 1
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 0

    # Address
    for i in range(6):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 1
        assert dut.spi_data_out.value == (addr >> (20 - i * 4)) & 0xF
        assert dut.spi_data_oe.value == 0xF
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 0

    # Dummy
    for i in range(2):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 1
        assert dut.spi_data_oe.value == 0xF
        assert dut.spi_data_out.value == 0xF
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 0

    for i in range(4):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 1
        assert dut.spi_data_oe.value == 0
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 0


nibble_shift_order = [4, 0, 12, 8, 20, 16, 28, 24]

async def send_instr(dut, data):
    for i in range(8):
        dut.spi_data_in.value = (data >> (nibble_shift_order[i])) & 0xF
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        for _ in range(20):
            if dut.spi_clk_out.value == 0:
                await ClockCycles(dut.clk, 1, False)
            else:
                break
        assert dut.spi_clk_out.value == 1
        assert dut.spi_data_oe.value == 0
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.spi_clk_out.value == 0

send_nops = True
nop_task = None

async def nops_loop(dut):
    while send_nops:
        await send_instr(dut, InstructionADDI(x0, x0, 0).encode())

def start_nops(dut):
    global send_nops, nop_task
    send_nops = True
    nop_task = cocotb.start_soon(nops_loop(dut))

async def stop_nops():
    global send_nops, nop_task
    send_nops = False
    await nop_task


@cocotb.test()
async def test_start(dut):
  dut._log.info("Start")
  
  # Our example module doesn't use clock and reset, but we show how to use them here anyway.
  clock = Clock(dut.clk, 15, units="ns")
  cocotb.start_soon(clock.start())

  # Reset
  dut._log.info("Reset")
  dut.ena.value = 1
  dut.ui_in.value = 0
  dut.uio_in.value = 0
  dut.rst_n.value = 1
  await ClockCycles(dut.clk, 2)
  dut.rst_n.value = 0
  await ClockCycles(dut.clk, 1)
  assert dut.uio_oe.value == 0
  await ClockCycles(dut.clk, 9)
  dut.rst_n.value = 1
  await ClockCycles(dut.clk, 1)
  assert dut.uio_oe.value == 0b11001001
  
  # Should start reading flash after 1 cycle
  await ClockCycles(dut.clk, 1)
  await start_read(dut, 0)
  
  for i in range(8):
    await send_instr(dut, InstructionADDI(i+8, x0, 0x102*i).encode())

  uart_byte = 0x54
  await send_instr(dut, InstructionADDI(x1, x0, uart_byte).encode())
  await send_instr(dut, InstructionSW(tp, x1, 0x10).encode())

  start_nops(dut)
  bit_time = 8680
  await Timer(bit_time / 2, "ns")
  assert dut.uart_tx.value == 0
  for i in range(8):
      await Timer(bit_time, "ns")
      assert dut.uart_tx.value == (uart_byte & 1)
      uart_byte >>= 1
  await Timer(bit_time, "ns")
  assert dut.uart_tx.value == 1

  await stop_nops()
