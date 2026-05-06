# test_stress.py
# Stress test — equivalent to riscv_stress_test.sv.

import logging
import cocotb
from cocotb.triggers import ClockCycles
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tb.riscv_env import RiscvEnv
from tb.riscv_sequences import StressSequence

log = logging.getLogger("riscv.test.stress")


@cocotb.test()
async def test_stress(dut):
    """Stress test: RAW chains, load-use, branch-heavy — all three passes."""
    seq     = StressSequence()
    program = seq.generate()

    log.info(f"Stress program: {len(program)} total instructions")

    env = RiscvEnv(dut)
    await env.start()
    await env.driver.load_program(program)

    await ClockCycles(dut.clk, len(program) * 6 + 100)

    env.scoreboard.report()
    log.info("test_stress PASSED")
