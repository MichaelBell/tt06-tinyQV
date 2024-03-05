
from cocotb.triggers import ClockCycles

async def reset(dut, latency=1, ui_in=0):
  # Reset
  dut._log.info(f"Reset, latency {latency}")
  dut.ena.value = 1
  dut.ui_in.value = ui_in
  dut.uio_in.value = 0
  dut.rst_n.value = 1
  await ClockCycles(dut.clk, 2)
  dut.rst_n.value = 0
  dut.latency_cfg.value = latency
  await ClockCycles(dut.clk, 1)
  assert dut.uio_oe.value == 0
  await ClockCycles(dut.clk, 9)
  dut.rst_n.value = 1
  await ClockCycles(dut.clk, 1)
  assert dut.uio_oe.value == 0b11001001
