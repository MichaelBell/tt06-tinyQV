# SPDX-FileCopyrightText: © 2024 Michael Bell
# SPDX-License-Identifier: MIT

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

# This hack because it isn't easy to install requirements in the TT GitHub actions
try:
    from riscvmodel.insn import *
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "riscv-model"])
    from riscvmodel.insn import *

from riscvmodel.regnames import x0, x1, sp, tp, a0, a1, a2, a3

from test_util import reset

select = None

async def start_read(dut, addr):
    global select

    if addr is None:
        select = dut.qspi_flash_select
    elif addr >= 0x1800000:
        select = dut.qspi_ram_b_select
    elif addr >= 0x1000000:
        select = dut.qspi_ram_a_select
    else:
        select = dut.qspi_flash_select
    
    assert select.value == 0
    assert dut.qspi_flash_select.value == 0 if dut.qspi_flash_select == select else 1
    assert dut.qspi_ram_a_select.value == 0 if dut.qspi_ram_a_select == select else 1
    assert dut.qspi_ram_b_select.value == 0 if dut.qspi_ram_b_select == select else 1
    assert dut.qspi_clk_out.value == 0

    if dut.qspi_flash_select != select:
        # Command
        cmd = 0x0B
        assert dut.qspi_data_oe.value == 0xF    # Command
        for i in range(2):
            await ClockCycles(dut.clk, 1, False)
            assert select.value == 0
            assert dut.qspi_clk_out.value == 1
            assert dut.qspi_data_out.value == (cmd & 0xF0) >> 4
            assert dut.qspi_data_oe.value == 0xF
            cmd <<= 4
            await ClockCycles(dut.clk, 1, False)
            assert select.value == 0
            assert dut.qspi_clk_out.value == 0

    # Address
    assert dut.qspi_data_oe.value == 0xF
    for i in range(6):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 1
        if addr is not None:
            assert dut.qspi_data_out.value == (addr >> (20 - i * 4)) & 0xF
        assert dut.qspi_data_oe.value == 0xF
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 0

    # Dummy
    if dut.qspi_flash_select == select:
        for i in range(2):
            await ClockCycles(dut.clk, 1, False)
            assert select.value == 0
            assert dut.qspi_clk_out.value == 1
            assert dut.qspi_data_oe.value == 0xF
            assert dut.qspi_data_out.value == 0xA
            await ClockCycles(dut.clk, 1, False)
            assert select.value == 0
            assert dut.qspi_clk_out.value == 0

    for i in range(4):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 1
        assert dut.qspi_data_oe.value == 0
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 0


nibble_shift_order = [4, 0, 12, 8, 20, 16, 28, 24]

async def send_instr(dut, data):
    instr_len = 8 if (data & 3) == 3 else 4
    for i in range(instr_len):
        dut.qspi_data_in.value = (data >> (nibble_shift_order[i])) & 0xF
        await ClockCycles(dut.clk, 1, False)
        assert dut.qspi_flash_select.value == 0
        for _ in range(20):
            if dut.qspi_clk_out.value == 0:
                await ClockCycles(dut.clk, 1, False)
            else:
                break
        assert dut.qspi_clk_out.value == 1
        assert dut.qspi_data_oe.value == 0
        await ClockCycles(dut.clk, 1, False)
        if i != instr_len - 1:
            assert dut.qspi_flash_select.value == 0
        assert dut.qspi_clk_out.value == 0

async def expect_load(dut, addr, val):
    if addr >= 0x1800000:
        select = dut.qspi_ram_b_select
    elif addr >= 0x1000000:
        select = dut.qspi_ram_a_select
    else:
        assert False # Load from flash not currently supported in this test

    for i in range(12):
        if select.value == 0:
            await start_read(dut, addr)
            dut.qspi_data_in.value = (val >> (nibble_shift_order[0])) & 0xF
            for j in range(1,8):
                await ClockCycles(dut.clk, 1, False)
                assert select.value == 0
                assert dut.qspi_clk_out.value == 1
                assert dut.qspi_data_oe.value == 0
                await ClockCycles(dut.clk, 1, False)
                if select.value != 0:
                    assert j in (2, 4)
                    break
                assert dut.qspi_clk_out.value == 0
                dut.qspi_data_in.value = (val >> (nibble_shift_order[j])) & 0xF
            break
        elif dut.qspi_flash_select.value == 0:
            await send_instr(dut, 0x0001)
        else:
            await ClockCycles(dut.clk, 1, False)
    else:
        assert False

    for i in range(8):
        await ClockCycles(dut.clk, 1)
        if dut.qspi_flash_select.value == 0:
            if hasattr(dut.user_project, "i_tinyqv"):
                await start_read(dut, dut.user_project.i_tinyqv.instr_addr.value.integer * 2)
            else:
                await start_read(dut, None)
            break
    else:
        assert False

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

async def read_reg(dut, reg, expected_val):
  await send_instr(dut, InstructionSW(tp, reg, 0x18).encode())

  start_nops(dut)
  for i in range(80):
      if dut.debug_uart_tx.value == 0:
          break
      else:
          await Timer(5, "ns")
  assert dut.debug_uart_tx.value == 0
  bit_time = 250
  await Timer(bit_time / 2, "ns")
  assert dut.debug_uart_tx.value == 0
  for i in range(8):
      await Timer(bit_time, "ns")
      assert dut.debug_uart_tx.value == (expected_val & 1)
      expected_val >>= 1
  await Timer(bit_time, "ns")
  assert dut.debug_uart_tx.value == 1

  await stop_nops()


@cocotb.test()
async def test_start(dut):
  dut._log.info("Start")
  
  clock = Clock(dut.clk, 15.624, units="ns")
  cocotb.start_soon(clock.start())

  # Reset
  await reset(dut)
  
  # Should start reading flash after 1 cycle
  await ClockCycles(dut.clk, 1)
  await start_read(dut, 0)
  
  for i in range(8):
    await send_instr(dut, InstructionADDI(i+8, x0, 0x102*i).encode())

  # Test UART TX
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

  # Test Debug UART TX
  uart_byte = 0x5A
  await send_instr(dut, InstructionADDI(x1, x0, uart_byte).encode())
  await read_reg(dut, x1, uart_byte)

  # Test SPI
  spi_byte = 0xa5
  spi_byte_in = random.randint(0, 255)
  #print(f"{spi_byte_in:02x}")
  await send_instr(dut, InstructionADDI(x1, x0, spi_byte | 0x100).encode())
  await send_instr(dut, InstructionSW(tp, x1, 0x20).encode())

  start_nops(dut)
  assert dut.spi_cs == 1
  for i in range(20):
    await ClockCycles(dut.clk, 1)
    if dut.spi_cs == 0:
        break

  # Default divider is 2
  divider = 2
  for i in range(8):
      assert dut.spi_cs == 0
      assert dut.spi_sck == 0
      assert dut.spi_mosi.value == (1 if (spi_byte & 0x80) else 0)
      await ClockCycles(dut.clk, divider)
      assert dut.spi_cs == 0
      assert dut.spi_sck == 1
      dut.spi_miso.value = (1 if (spi_byte_in & 0x80) else 0)
      assert dut.spi_mosi.value == (1 if (spi_byte & 0x80) else 0)
      await ClockCycles(dut.clk, divider)
      spi_byte <<= 1
      spi_byte_in <<= 1

  assert dut.spi_sck == 0
  assert dut.spi_cs.value == 0
  await ClockCycles(dut.clk, divider)
  assert dut.spi_cs.value == 1

  await stop_nops()  

  await send_instr(dut, InstructionLW(x1, tp, 0x20).encode())
  await read_reg(dut, x1, spi_byte_in >> 8)

  for divider in range(1,5):
    spi_byte = random.randint(0, 255)
    spi_byte_in = random.randint(0, 255)
    #print(f"{spi_byte_in:02x}")
    spi_config = divider - 1
    if divider == 1: spi_config += 4  # Use high latency for divider 1
    await send_instr(dut, InstructionADDI(x1, x0, spi_config).encode())
    await send_instr(dut, InstructionSW(tp, x1, 0x24).encode())
    await send_instr(dut, InstructionADDI(x1, x0, spi_byte | 0x100).encode())
    await send_instr(dut, InstructionSW(tp, x1, 0x20).encode())

    start_nops(dut)
    assert dut.spi_cs == 1
    for i in range(20):
        await ClockCycles(dut.clk, 1)
        if dut.spi_cs == 0:
            break

    for i in range(8):
        assert dut.spi_cs == 0
        assert dut.spi_sck == 0
        assert dut.spi_mosi.value == (1 if (spi_byte & 0x80) else 0)
        await ClockCycles(dut.clk, divider)
        assert dut.spi_cs == 0
        assert dut.spi_sck == 1
        dut.spi_miso.value = (1 if (spi_byte_in & 0x80) else 0)
        assert dut.spi_mosi.value == (1 if (spi_byte & 0x80) else 0)
        await ClockCycles(dut.clk, divider)
        spi_byte <<= 1
        spi_byte_in <<= 1

    await ClockCycles(dut.clk, divider)
    assert dut.spi_cs.value == 1

    await stop_nops()  
    await send_instr(dut, InstructionLW(x1, tp, 0x20).encode())
    await read_reg(dut, x1, spi_byte_in >> 8)

  # GPIO
  for i in range(40):
    gpio_sel = random.randint(0, 255)
    gpio_out = random.randint(0, 255)
    await send_instr(dut, InstructionADDI(x1, x0, gpio_sel).encode())
    await send_instr(dut, InstructionSW(tp, x1, 0x0C).encode())
    await send_instr(dut, InstructionADDI(x1, x0, gpio_out).encode())
    await send_instr(dut, InstructionSW(tp, x1, 0x0).encode())
    for _ in range(3):
        await send_instr(dut, InstructionADDI(x0, x0, 0).encode())
    assert (dut.uo_out.value & gpio_sel) == (gpio_out & gpio_sel)

@cocotb.test()
async def test_debug_reg(dut):
  dut._log.info("Start")
  
  clock = Clock(dut.clk, 15.624, units="ns")
  cocotb.start_soon(clock.start())

  # Reset
  await reset(dut, 1, 0x18)
  
  # Should start reading flash after 1 cycle
  await ClockCycles(dut.clk, 1)
  await start_read(dut, 0)
  dut.ui_in.value = 0b01101000 # Register write enable
  
  val = 0
  for i in range(8):
    val += 0x102 * i
    await send_instr(dut, InstructionADDI(i+8, x0 if i == 0 else (i+7), 0x102*i).encode())
    start_nops(dut)
    for i in range(24):
        if dut.uo_out[7].value == 1:
            break
        await ClockCycles(dut.clk, 1)
    else:
        assert False

    await ClockCycles(dut.clk, 1)
    for j in range(8):
        assert ((dut.uo_out.value >> 2) & 0xF) == ((val >> (4 * j)) & 0xF)
        await ClockCycles(dut.clk, 1)
    await stop_nops()

@cocotb.test()
async def test_load_bug(dut):
  dut._log.info("Start")
  
  clock = Clock(dut.clk, 15.624, units="ns")
  cocotb.start_soon(clock.start())

  # Reset
  await reset(dut)

  input_byte = 0b01101000
  dut.ui_in.value = input_byte

  def encode_clwsp(reg, base_reg, imm):
    scrambled = (((imm << (12 - 5)) & 0b1000000000000) |
                    ((imm << ( 4 - 2)) & 0b0000001110000) |
                    ((imm >> ( 6 - 2)) & 0b0000000001100))
    if base_reg == 2:
        return 0x4002 | scrambled | (reg << 7)
    else:
        return 0x6002 | scrambled | (reg << 7)  
  
  # Should start reading flash after 1 cycle
  await ClockCycles(dut.clk, 1)
  await start_read(dut, 0)
  await send_instr(dut, InstructionAUIPC(sp, 0x1001).encode())
  await send_instr(dut, InstructionADDI(a0, x0, 0x001).encode())
  await send_instr(dut, InstructionBEQ(a0, x0, 270).encode())

  await send_instr(dut, encode_clwsp(a3, tp, 4))
  await send_instr(dut, encode_clwsp(a2, sp, 12))
  await expect_load(dut, 0x1001000 + 12, 0x123)
  await read_reg(dut, a3, input_byte)
  await read_reg(dut, a2, 0x123)
