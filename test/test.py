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

from riscvmodel.regnames import x0, x1, sp, gp, tp, a0, a1, a2, a3
from riscvmodel.variant import RV32E

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
    assert dut.qspi_flash_select.value == (0 if dut.qspi_flash_select == select else 1)
    assert dut.qspi_ram_a_select.value == (0 if dut.qspi_ram_a_select == select else 1)
    assert dut.qspi_ram_b_select.value == (0 if dut.qspi_ram_b_select == select else 1)
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


async def start_write(dut, addr):
    global select

    if addr >= 0x1800000:
        select = dut.qspi_ram_b_select
    else:
        select = dut.qspi_ram_a_select

    assert select.value == 0
    assert dut.qspi_flash_select.value == 1
    assert dut.qspi_ram_a_select.value == (0 if dut.qspi_ram_a_select == select else 1)
    assert dut.qspi_ram_b_select.value == (0 if dut.qspi_ram_b_select == select else 1)
    assert dut.qspi_clk_out.value == 0
    assert dut.qspi_data_oe.value == 0xF

    # Command
    cmd = 0x02
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
    for i in range(6):
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 1
        assert dut.qspi_data_out.value == (addr >> (20 - i * 4)) & 0xF
        assert dut.qspi_data_oe.value == 0xF
        await ClockCycles(dut.clk, 1, False)
        assert select.value == 0
        assert dut.qspi_clk_out.value == 0


nibble_shift_order = [4, 0, 12, 8, 20, 16, 28, 24]

async def send_instr(dut, data, ok_to_exit=False):
    instr_len = 8 if (data & 3) == 3 else 4
    for i in range(instr_len):
        dut.qspi_data_in.value = (data >> (nibble_shift_order[i])) & 0xF
        await ClockCycles(dut.clk, 1, False)
        for _ in range(20):
            if ok_to_exit and dut.qspi_flash_select.value == 1:
                return
            assert dut.qspi_flash_select.value == 0
            if dut.qspi_clk_out.value == 0:
                await ClockCycles(dut.clk, 1, False)
            else:
                break
        assert dut.qspi_clk_out.value == 1
        assert dut.qspi_data_oe.value == 0
        await ClockCycles(dut.clk, 1, False)
        assert dut.qspi_clk_out.value == 0
        if i != instr_len - 1:
            if ok_to_exit and dut.qspi_flash_select.value == 1:
                return
            assert dut.qspi_flash_select.value == 0

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
                if select.value != 0:
                    assert j in (3, 5)
                    break
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
            await send_instr(dut, 0x0001, True)
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

async def load_reg(dut, reg, value):
    offset = random.randint(-0x400, 0x3FF)
    instr = InstructionLW(reg, gp, offset).encode()
    await send_instr(dut, instr)

    await expect_load(dut, 0x1000400 + offset, value)


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

async def read_byte(dut, reg, expected_val):
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

async def expect_store(dut, addr):
    if addr >= 0x1800000:
        select = dut.qspi_ram_b_select
    elif addr >= 0x1000000:
        select = dut.qspi_ram_a_select
    else:
        assert False

    val = 0
    for i in range(12):
        if select.value == 0:
            await start_write(dut, addr)
            for j in range(8):
                await ClockCycles(dut.clk, 1, False)
                assert select.value == 0
                assert dut.qspi_clk_out.value == 1
                assert dut.qspi_data_oe.value == 0xF
                val |= dut.qspi_data_out.value << (nibble_shift_order[j])
                await ClockCycles(dut.clk, 1, False)
                assert select.value == (1 if j == 7 else 0)
                assert dut.qspi_clk_out.value == 0
            await ClockCycles(dut.clk, 1, False)
            assert select.value == 1
            break
        elif dut.qspi_flash_select.value == 0:
            await send_instr(dut, 0x0001, True)
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

    return val

async def read_reg(dut, reg):
    offset = random.randint(-0x400, 0x3FF)
    instr = InstructionSW(gp, reg, offset).encode()
    await send_instr(dut, instr)

    return await expect_store(dut, 0x1000400 + offset)


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

  # Test UART RX
  for j in range(10):
    assert dut.uart_rts.value == 0
    uart_rx_byte = random.randint(0, 255)
    val = uart_rx_byte
    dut.uart_rx.value = 0
    await Timer(bit_time, "ns")
    for i in range(8):
        dut.uart_rx.value = val & 1
        await Timer(bit_time, "ns")
        assert dut.uart_rts.value == 1
        val >>= 1
    dut.uart_rx.value = 1
    await Timer(bit_time, "ns")
    assert dut.uart_rts.value == 1

    await stop_nops()

    await send_instr(dut, InstructionLW(x1, tp, 0x14).encode())
    await read_byte(dut, x1, 0x2)
    await send_instr(dut, InstructionLW(x1, tp, 0x10).encode())
    await read_byte(dut, x1, uart_rx_byte)
    assert dut.uart_rts.value == 0
    await send_instr(dut, InstructionLW(x1, tp, 0x14).encode())
    await read_byte(dut, x1, 0)

    if j != 9:
        start_nops(dut)

  # Test Debug UART TX
  uart_byte = 0x5A
  await send_instr(dut, InstructionADDI(x1, x0, uart_byte).encode())
  await read_byte(dut, x1, uart_byte)

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
  await read_byte(dut, x1, spi_byte_in >> 8)

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
    await read_byte(dut, x1, spi_byte_in >> 8)

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
  dut.ui_in_base.value = 0b01101000 # Register write enable
  
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
  await read_byte(dut, a3, input_byte)
  await read_byte(dut, a2, 0x123)


### Random operation testing ###
reg = [0] * 16

# Each Op does reg[d] = fn(a, b)
# fn will access reg global array
class SimpleOp:
    def __init__(self, rvm_insn, fn, name):
        self.rvm_insn = rvm_insn
        self.fn = fn
        self.name = name
        self.is_mem_op = False

    def randomize(self):
        self.rvm_insn_inst = self.rvm_insn()
        self.rvm_insn_inst.randomize(variant=RV32E)
    
    def execute_fn(self, rd, rs1, arg2):
        if rd != 0 and rd != 3 and rd != 4:
            reg[rd] = self.fn(rs1, arg2)
            while reg[rd] < -0x80000000: reg[rd] += 0x100000000
            while reg[rd] > 0x7FFFFFFF:  reg[rd] -= 0x100000000

    def encode(self, rd, rs1, arg2):
        return self.rvm_insn(rd, rs1, arg2).encode()
    
    def get_valid_rd(self):
        return random.randint(0, 15)

    def get_valid_rs1(self):
        return random.randint(0, 15)

    def get_valid_arg2(self):
        return (random.randint(0, 15) if issubclass(self.rvm_insn, InstructionRType) else 
                self.rvm_insn_inst.shamt.value if issubclass(self.rvm_insn, InstructionISType) else
                self.rvm_insn_inst.imm.value)

def encode_ci(reg, imm, opcode):
    scrambled = (((imm << (12 - 5)) & 0b1000000000000) |
                    ((imm << ( 2 - 0)) & 0b0000001111100))
    return opcode | scrambled | (reg << 7)

def encode_cli(reg, imm):
    return encode_ci(reg, imm, 0x4001)

def encode_caddi(reg, imm):
    return encode_ci(reg, imm, 0x0001)

def encode_cslli(reg, imm):
    return encode_ci(reg, imm, 0x0002)

def encode_ci2(reg, imm, opcode):
    return encode_ci(reg - 8, imm, opcode)

def encode_csrli(reg, imm):
    return encode_ci2(reg, imm, 0x8001)

def encode_csrai(reg, imm):
    return encode_ci2(reg, imm, 0x8401)

def encode_candi(reg, imm):
    return encode_ci2(reg, imm, 0x8801)

def encode_cnot(reg, _):
    return 0x9c75 | ((reg - 8) << 7)

def encode_czext_b(reg, _):
    return 0x9c61 | ((reg - 8) << 7)

def encode_czext_h(reg, _):
    return 0x9c69 | ((reg - 8) << 7)

def encode_cr(dest_reg, src_reg, opcode):
    return opcode | (dest_reg << 7) | (src_reg << 2)

def encode_cmv(dest_reg, src_reg):
    return encode_cr(dest_reg, src_reg, 0x8002)

def encode_cadd(dest_reg, src_reg):
    return encode_cr(dest_reg, src_reg, 0x9002)

def encode_cmul16(dest_reg, src_reg):
    return encode_cr(dest_reg, src_reg, 0xA002)

def encode_ca(dest_reg, src_reg, opcode):
    return opcode | ((dest_reg - 8) << 7) | ((src_reg - 8) << 2)

def encode_csub(dest_reg, src_reg):
    return encode_ca(dest_reg, src_reg, 0x8C01)

def encode_cxor(dest_reg, src_reg):
    return encode_ca(dest_reg, src_reg, 0x8C21)

def encode_cor(dest_reg, src_reg):
    return encode_ca(dest_reg, src_reg, 0x8C41)

def encode_cand(dest_reg, src_reg):
    return encode_ca(dest_reg, src_reg, 0x8C61)

class CIOp:
    def __init__(self, encoder, min_rs1, min_imm, fn, name):
        self.encoder = encoder
        self.fn = fn
        self.name = name
        self.min_rs1 = min_rs1
        self.min_imm = min_imm
        self.is_mem_op = False

    def randomize(self):
        self.rs1 = random.randint(self.min_rs1, 15)
        self.imm = random.randint(self.min_imm, 31)
    
    def execute_fn(self, rd, rs1, arg2):
        if rd != 0 and rd != 3 and rd != 4:
            reg[rd] = self.fn(rs1, arg2)
            while reg[rd] < -0x80000000: reg[rd] += 0x100000000
            while reg[rd] > 0x7FFFFFFF:  reg[rd] -= 0x100000000

    def encode(self, rd, rs1, arg2):
        return self.encoder(rs1, arg2)
    
    def get_valid_rd(self):
        return self.rs1

    def get_valid_rs1(self):
        return self.rs1

    def get_valid_arg2(self):
        return self.imm

class CROp:
    def __init__(self, encoder, min_reg, fn, name):
        self.encoder = encoder
        self.fn = fn
        self.name = name
        self.min_reg = min_reg
        self.is_mem_op = False

    def randomize(self):
        self.rs1 = random.randint(self.min_reg, 15)
        self.rs2 = random.randint(self.min_reg, 15)
    
    def execute_fn(self, rd, rs1, arg2):
        if rd != 0 and rd != 3 and rd != 4:
            reg[rd] = self.fn(rs1, arg2)
            while reg[rd] < -0x80000000: reg[rd] += 0x100000000
            while reg[rd] > 0x7FFFFFFF:  reg[rd] -= 0x100000000

    def encode(self, rd, rs1, arg2):
        return self.encoder(rs1, arg2)
    
    def get_valid_rd(self):
        return self.rs1

    def get_valid_rs1(self):
        return self.rs1

    def get_valid_arg2(self):
        return self.rs2

ops_alu = [
    SimpleOp(InstructionADDI, lambda rs1, imm: reg[rs1] + imm, "+i"),
    SimpleOp(InstructionADD, lambda rs1, rs2: reg[rs1] + reg[rs2], "+"),
    SimpleOp(InstructionSUB, lambda rs1, rs2: reg[rs1] - reg[rs2], "-"),
    SimpleOp(InstructionANDI, lambda rs1, imm: reg[rs1] & imm, "&i"),
    SimpleOp(InstructionAND, lambda rs1, rs2: reg[rs1] & reg[rs2], "&"),
    SimpleOp(InstructionORI, lambda rs1, imm: reg[rs1] | imm, "|i"),
    SimpleOp(InstructionOR, lambda rs1, rs2: reg[rs1] | reg[rs2], "|"),
    SimpleOp(InstructionXORI, lambda rs1, imm: reg[rs1] ^ imm, "^i"),
    SimpleOp(InstructionXOR, lambda rs1, rs2: reg[rs1] ^ reg[rs2], "^"),
    SimpleOp(InstructionSLTI, lambda rs1, imm: 1 if reg[rs1] < imm else 0, "<i"),
    SimpleOp(InstructionSLT, lambda rs1, rs2: 1 if reg[rs1] < reg[rs2] else 0, "<"),
    SimpleOp(InstructionSLTIU, lambda rs1, imm: 1 if (reg[rs1] & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0, "<iu"),
    SimpleOp(InstructionSLTU, lambda rs1, rs2: 1 if (reg[rs1] & 0xFFFFFFFF) < (reg[rs2] & 0xFFFFFFFF) else 0, "<u"),
    SimpleOp(InstructionSLLI, lambda rs1, imm: reg[rs1] << imm, "<<i"),
    SimpleOp(InstructionSLL, lambda rs1, rs2: reg[rs1] << (reg[rs2] & 0x1F), "<<"),
    SimpleOp(InstructionSRLI, lambda rs1, imm: (reg[rs1] & 0xFFFFFFFF) >> imm, ">>li"),
    SimpleOp(InstructionSRL, lambda rs1, rs2: (reg[rs1] & 0xFFFFFFFF) >> (reg[rs2] & 0x1F), ">>l"),
    SimpleOp(InstructionSRAI, lambda rs1, imm: reg[rs1] >> imm, ">>i"),
    SimpleOp(InstructionSRA, lambda rs1, rs2: reg[rs1] >> (reg[rs2] & 0x1F), ">>"),
    CIOp(encode_cli, 1, -32, lambda rs1, imm: imm, "=i(c)"),
    CIOp(encode_caddi, 1, -32, lambda rs1, imm: reg[rs1] + imm, "+i(c)"),
    CIOp(encode_cslli, 1, 0, lambda rs1, imm: reg[rs1] << imm, "<<i(c)"),
    CIOp(encode_csrli, 8, 0, lambda rs1, imm: (reg[rs1] & 0xFFFFFFFF) >> imm, ">>li(c)"),
    CIOp(encode_csrai, 8, 0, lambda rs1, imm: reg[rs1] >> imm, ">>li(c)"),
    CIOp(encode_candi, 8, -32, lambda rs1, imm: reg[rs1] & imm, "&i(c)"),
    CIOp(encode_cnot, 8, 0, lambda rs1, imm: ~(reg[rs1] & 0xFFFFFFFF), "~(c)"),
    CIOp(encode_czext_b, 8, 0, lambda rs1, imm: reg[rs1] & 0xFF, "zb(c)"),
    CIOp(encode_czext_h, 8, 0, lambda rs1, imm: reg[rs1] & 0xFFFF, "zh(c)"),
    CROp(encode_cmv, 1, lambda rs1, rs2: reg[rs2], "=(c)"),
    CROp(encode_cadd, 1, lambda rs1, rs2: reg[rs1] + reg[rs2], "+(c)"),
    CROp(encode_cmul16, 1, lambda rs1, rs2: reg[rs1] * (reg[rs2] & 0xFFFF), "*(c)"),
    CROp(encode_csub, 8, lambda rs1, rs2: reg[rs1] - reg[rs2], "-(c)"),
    CROp(encode_cxor, 8, lambda rs1, rs2: reg[rs1] ^ reg[rs2], "^(c)"),
    CROp(encode_cor, 8, lambda rs1, rs2: reg[rs1] | reg[rs2], "|(c)"),
    CROp(encode_cand, 8, lambda rs1, rs2: reg[rs1] & reg[rs2], "&(c)"),
]

@cocotb.test()
async def test_random_alu(dut):
    dut._log.info("Start")
  
    clock = Clock(dut.clk, 15.624, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    await reset(dut)

    # Should start reading flash after 1 cycle
    await ClockCycles(dut.clk, 1)
    await start_read(dut, 0)
    
    seed = random.randint(0, 0xFFFFFFFF)
    #seed = 1508125843
    debug = False
    for test in range(50):
        random.seed(seed + test)
        dut._log.info("Running test with seed {}".format(seed + test))
        for i in range(1, 16):
            if i == 3: reg[i] = 0x1000400
            elif i == 4: reg[i] = 0x8000000
            else:
                reg[i] = random.randint(-0x80000000, 0x7FFFFFFF)
                if debug: print("Set reg {} to {}".format(i, reg[i]))
                await load_reg(dut, i, reg[i])

        if False:
            for i in range(16):
                reg_value = (await read_reg(dut, i)).signed_integer
                if debug: print("Reg {} is {}".format(i, reg_value))
                assert reg_value == reg[i]

        last_instr = ops_alu[0]
        for i in range(200):
            while True:
                try:
                    instr = random.choice(ops_alu)
                    instr.randomize()
                    rd = instr.get_valid_rd()
                    rs1 = instr.get_valid_rs1()
                    arg2 = instr.get_valid_arg2()

                    instr.execute_fn(rd, rs1, arg2)
                    break
                except ValueError:
                    pass

            if debug: print("x{} = x{} {} {}, now {} {:08x}".format(rd, rs1, arg2, instr.name, reg[rd], instr.encode(rd, rs1, arg2)))
            await send_instr(dut, instr.encode(rd, rs1, arg2))
            #if debug:
            #    assert await read_reg(dut, rd) == reg[rd] & 0xFFFFFFFF

        for i in range(16):
            reg_value = (await read_reg(dut, i))
            if debug: print("Reg x{} = {} should be {}".format(i, reg_value, reg[i]))
            assert reg_value & 0xFFFFFFFF == reg[i] & 0xFFFFFFFF

def encode_clw(reg, base_reg, imm):
    scrambled = (((imm << (10 - 3)) & 0b1110000000000) |
                    ((imm << ( 6 - 2)) & 0b0000001000000) |
                    ((imm >> ( 6 - 5)) & 0b0000000100000))
    return 0x4000 | scrambled | ((base_reg - 8) << 7) | ((reg - 8) << 2)        

def encode_lh(reg, base_reg, imm):
    scrambled = ((imm << (5 - 1)) & 0b100000)
    return 0x8440 | scrambled | ((base_reg - 8) << 7) | ((reg - 8) << 2)

def encode_lhu(reg, base_reg, imm):
    scrambled = ((imm << (5 - 1)) & 0b100000)
    return 0x8400 | scrambled | ((base_reg - 8) << 7) | ((reg - 8) << 2)

def encode_lbu(reg, base_reg, imm):
    scrambled = (((imm << (5 - 1)) & 0b0100000) |
                    ((imm << (6 - 0)) & 0b1000000))
    return 0x8000 | scrambled | ((base_reg - 8) << 7) | ((reg - 8) << 2)

async def set_reg(dut, rd, value):
    await send_instr(dut, InstructionLUI(rd, (value + 0x800) >> 12).encode())
    await send_instr(dut, InstructionADDI(rd, rd, ((value + 0x800) & 0xFFF) - 0x800).encode())
    reg[rd] = value

class CLoadOp:
    def __init__(self, encoder, min_imm, max_imm, imm_mul, fn, name):
        self.encoder = encoder
        self.fn = fn
        self.name = name
        self.is_mem_op = True
        self.min_imm = min_imm
        self.max_imm = max_imm
        self.imm_mul = imm_mul

    def randomize(self):
        self.rd = random.randint(8, 15)
        self.base_reg = random.randint(8, 15)
        self.imm = random.randint(self.min_imm, self.max_imm) * self.imm_mul
        self.val = random.randint(-0x80000000, 0x7fffffff)

    def execute_fn(self, rd, rs1, arg2):
        if rd != 0 and rd != 3 and rd != 4:
            reg[rd] = self.fn(self.val)

    def encode(self, rd, rs1, arg2):
        return self.encoder(rd, rs1, arg2)
    
    def get_valid_rd(self):
        return self.rd

    def get_valid_rs1(self):
        return self.base_reg

    def get_valid_arg2(self):
        return self.imm
    
    async def do_mem_op(self, dut, addr):
        #print("Load {} from addr {:08x}".format(self.val, addr))
        await expect_load(dut, addr, self.val)

class LoadOp:
    def __init__(self, instr, min_imm, max_imm, imm_mul, fn, name):
        self.instr = instr
        self.fn = fn
        self.name = name
        self.is_mem_op = True
        self.min_imm = min_imm
        self.max_imm = max_imm
        self.imm_mul = imm_mul

    def randomize(self):
        self.rd = random.randint(0, 15)
        while True:
            self.base_reg = random.randint(1, 15)
            if self.base_reg not in (gp, tp):
                break
        self.imm = random.randint(self.min_imm, self.max_imm) * self.imm_mul
        self.val = random.randint(-0x80000000, 0x7fffffff)

    def execute_fn(self, rd, rs1, arg2):
        if rd != 0 and rd != 3 and rd != 4:
            reg[rd] = self.fn(self.val)

    def encode(self, rd, rs1, arg2):
        return self.instr(rd, rs1, arg2).encode()
    
    def get_valid_rd(self):
        return self.rd

    def get_valid_rs1(self):
        return self.base_reg

    def get_valid_arg2(self):
        return self.imm
    
    async def do_mem_op(self, dut, addr):
        #print("Load {} from addr {:08x}".format(self.val, addr))
        await expect_load(dut, addr, self.val)

def encode_csw(base_reg, reg, imm):
    scrambled = (((imm << (10 - 3)) & 0b1110000000000) |
                    ((imm << ( 6 - 2)) & 0b0000001000000) |
                    ((imm >> ( 6 - 5)) & 0b0000000100000))
    return 0xC000 | scrambled | ((base_reg - 8) << 7) | ((reg - 8) << 2)

class CStoreOp:
    def __init__(self, encoder, min_imm, max_imm, imm_mul, fn, name):
        self.encoder = encoder
        self.fn = fn
        self.name = name
        self.is_mem_op = True
        self.min_imm = min_imm
        self.max_imm = max_imm
        self.imm_mul = imm_mul

    def randomize(self):
        self.rs1 = random.randint(8, 15)
        while True:
            self.base_reg = random.randint(8, 15)
            if self.base_reg != self.rs1:
                break
        self.imm = random.randint(self.min_imm, self.max_imm) * self.imm_mul

    def execute_fn(self, rd, rs1, arg2):
        pass

    def encode(self, rd, rs1, arg2):
        return self.encoder(self.base_reg, self.rs1, arg2)
    
    def get_valid_rd(self):
        return self.base_reg

    def get_valid_rs1(self):
        return self.rs1

    def get_valid_arg2(self):
        return self.imm
    
    async def do_mem_op(self, dut, addr):
        #print("Load {} from addr {:08x}".format(self.val, addr))
        assert await expect_store(dut, addr) == self.fn(self.rs1)

class StoreOp:
    def __init__(self, instr, min_imm, max_imm, imm_mul, fn, name):
        self.instr = instr
        self.fn = fn
        self.name = name
        self.is_mem_op = True
        self.min_imm = min_imm
        self.max_imm = max_imm
        self.imm_mul = imm_mul

    def randomize(self):
        self.rs1 = random.randint(0, 15)
        while True:
            self.base_reg = random.randint(1, 15)
            if self.base_reg not in (self.rs1, gp, tp):
                break
        self.imm = random.randint(self.min_imm, self.max_imm) * self.imm_mul

    def execute_fn(self, rd, rs1, arg2):
        pass

    def encode(self, rd, rs1, arg2):
        return self.instr(self.base_reg, self.rs1, arg2).encode()
    
    def get_valid_rd(self):
        return self.base_reg

    def get_valid_rs1(self):
        return self.rs1

    def get_valid_arg2(self):
        return self.imm
    
    async def do_mem_op(self, dut, addr):
        #print("Load {} from addr {:08x}".format(self.val, addr))
        assert await expect_store(dut, addr) == self.fn(self.rs1)

ops = [
    SimpleOp(InstructionADDI, lambda rs1, imm: reg[rs1] + imm, "+i"),
    SimpleOp(InstructionADD, lambda rs1, rs2: reg[rs1] + reg[rs2], "+"),
    SimpleOp(InstructionSUB, lambda rs1, rs2: reg[rs1] - reg[rs2], "-"),
    SimpleOp(InstructionANDI, lambda rs1, imm: reg[rs1] & imm, "&i"),
    SimpleOp(InstructionAND, lambda rs1, rs2: reg[rs1] & reg[rs2], "&"),
    SimpleOp(InstructionORI, lambda rs1, imm: reg[rs1] | imm, "|i"),
    SimpleOp(InstructionOR, lambda rs1, rs2: reg[rs1] | reg[rs2], "|"),
    SimpleOp(InstructionXORI, lambda rs1, imm: reg[rs1] ^ imm, "^i"),
    SimpleOp(InstructionXOR, lambda rs1, rs2: reg[rs1] ^ reg[rs2], "^"),
    SimpleOp(InstructionSLTI, lambda rs1, imm: 1 if reg[rs1] < imm else 0, "<i"),
    SimpleOp(InstructionSLT, lambda rs1, rs2: 1 if reg[rs1] < reg[rs2] else 0, "<"),
    SimpleOp(InstructionSLTIU, lambda rs1, imm: 1 if (reg[rs1] & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0, "<iu"),
    SimpleOp(InstructionSLTU, lambda rs1, rs2: 1 if (reg[rs1] & 0xFFFFFFFF) < (reg[rs2] & 0xFFFFFFFF) else 0, "<u"),
    SimpleOp(InstructionSLLI, lambda rs1, imm: reg[rs1] << imm, "<<i"),
    SimpleOp(InstructionSLL, lambda rs1, rs2: reg[rs1] << (reg[rs2] & 0x1F), "<<"),
    SimpleOp(InstructionSRLI, lambda rs1, imm: (reg[rs1] & 0xFFFFFFFF) >> imm, ">>li"),
    SimpleOp(InstructionSRL, lambda rs1, rs2: (reg[rs1] & 0xFFFFFFFF) >> (reg[rs2] & 0x1F), ">>l"),
    SimpleOp(InstructionSRAI, lambda rs1, imm: reg[rs1] >> imm, ">>i"),
    SimpleOp(InstructionSRA, lambda rs1, rs2: reg[rs1] >> (reg[rs2] & 0x1F), ">>"),
    CIOp(encode_cli, 1, -32, lambda rs1, imm: imm, "=i(c)"),
    CIOp(encode_caddi, 1, -32, lambda rs1, imm: reg[rs1] + imm, "+i(c)"),
    CIOp(encode_cslli, 1, 0, lambda rs1, imm: reg[rs1] << imm, "<<i(c)"),
    CIOp(encode_csrli, 8, 0, lambda rs1, imm: (reg[rs1] & 0xFFFFFFFF) >> imm, ">>li(c)"),
    CIOp(encode_csrai, 8, 0, lambda rs1, imm: reg[rs1] >> imm, ">>li(c)"),
    CIOp(encode_candi, 8, -32, lambda rs1, imm: reg[rs1] & imm, "&i(c)"),
    CIOp(encode_cnot, 8, 0, lambda rs1, imm: ~(reg[rs1] & 0xFFFFFFFF), "~(c)"),
    CIOp(encode_czext_b, 8, 0, lambda rs1, imm: reg[rs1] & 0xFF, "zb(c)"),
    CIOp(encode_czext_h, 8, 0, lambda rs1, imm: reg[rs1] & 0xFFFF, "zh(c)"),
    CROp(encode_cmv, 1, lambda rs1, rs2: reg[rs2], "=(c)"),
    CROp(encode_cadd, 1, lambda rs1, rs2: reg[rs1] + reg[rs2], "+(c)"),
    CROp(encode_cmul16, 1, lambda rs1, rs2: reg[rs1] * (reg[rs2] & 0xFFFF), "*(c)"),
    CROp(encode_csub, 8, lambda rs1, rs2: reg[rs1] - reg[rs2], "-(c)"),
    CROp(encode_cxor, 8, lambda rs1, rs2: reg[rs1] ^ reg[rs2], "^(c)"),
    CROp(encode_cor, 8, lambda rs1, rs2: reg[rs1] | reg[rs2], "|(c)"),
    CROp(encode_cand, 8, lambda rs1, rs2: reg[rs1] & reg[rs2], "&(c)"),
    CLoadOp(encode_clw, 0, 31, 4, lambda val: val, "lw(c)"),
    CLoadOp(encode_lh, 0, 1, 2, lambda val: (val & 0xFFFF) - 0x10000 if (val & 0x8000) != 0 else val & 0xFFFF, "lh(c)"),
    CLoadOp(encode_lhu, 0, 1, 2, lambda val: val & 0xFFFF, "lhu(c)"),
    CLoadOp(encode_lbu, 0, 3, 1, lambda val: val & 0xFF, "lbu(c)"),
    LoadOp(InstructionLW, -0x800, 0x7ff, 1, lambda val: val, "lw"),
    LoadOp(InstructionLH, -0x800, 0x7ff, 1, lambda val: (val & 0xFFFF) - 0x10000 if (val & 0x8000) != 0 else val & 0xFFFF, "lh"),
    LoadOp(InstructionLB, -0x800, 0x7ff, 1, lambda val: (val & 0xFF) - 0x100 if (val & 0x80) != 0 else val & 0xFF, "lb"),
    LoadOp(InstructionLHU, -0x800, 0x7ff, 1, lambda val: val & 0xFFFF, "lhu"),
    LoadOp(InstructionLBU, -0x800, 0x7ff, 1, lambda val: val & 0xFF, "lbu"),
    CStoreOp(encode_csw, 0, 31, 4, lambda rs1: reg[rs1] & 0xFFFFFFFF, "sw(c)"),
    StoreOp(InstructionSW, -0x800, 0x7ff, 1, lambda rs1: reg[rs1] & 0xFFFFFFFF, "sw"),
]

@cocotb.test()
async def test_random(dut):
    dut._log.info("Start")
  
    clock = Clock(dut.clk, 15.624, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    await reset(dut)

    # Should start reading flash after 1 cycle
    await ClockCycles(dut.clk, 1)
    await start_read(dut, 0)
    
    seed = random.randint(0, 0xFFFFFFFF)
    #seed = 1508125843
    debug = False
    for test in range(10):
        random.seed(seed + test)
        dut._log.info("Running test with seed {}".format(seed + test))
        for i in range(1, 16):
            if i == 3: reg[i] = 0x1000400
            elif i == 4: reg[i] = 0x8000000
            else:
                reg[i] = random.randint(-0x80000000, 0x7FFFFFFF)
                if debug: print("Set reg {} to {}".format(i, reg[i]))
                await load_reg(dut, i, reg[i])

        if False:
            for i in range(16):
                reg_value = (await read_reg(dut, i)).signed_integer
                if debug: print("Reg {} is {}".format(i, reg_value))
                assert reg_value == reg[i]

        last_instr = ops[0]
        for i in range(1000):
            while True:
                try:
                    instr = random.choice(ops)
                    instr.randomize()
                    rd = instr.get_valid_rd()
                    rs1 = instr.get_valid_rs1()
                    arg2 = instr.get_valid_arg2()

                    if instr.is_mem_op:
                        addr = random.randint(0x1000000-instr.imm, 0x1fffffc-instr.imm)
                        await set_reg(dut, instr.base_reg, addr)

                    instr.execute_fn(rd, rs1, arg2)
                    break
                except ValueError:
                    pass

            if debug: print("x{} = x{} {} {}, now {} {:08x}".format(rd, rs1, arg2, instr.name, reg[rd], instr.encode(rd, rs1, arg2)))
            await send_instr(dut, instr.encode(rd, rs1, arg2))
            if instr.is_mem_op:
                await instr.do_mem_op(dut, addr + instr.imm)
            #if debug:
            #    assert await read_reg(dut, rd) == reg[rd] & 0xFFFFFFFF

        for i in range(16):
            reg_value = (await read_reg(dut, i))
            if debug: print("Reg x{} = {} should be {}".format(i, reg_value, reg[i]))
            assert reg_value & 0xFFFFFFFF == reg[i] & 0xFFFFFFFF
