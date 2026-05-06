# test_rand.py
# Random instruction test — equivalent to riscv_rand_test.sv.

import logging
import cocotb
from cocotb.triggers import ClockCycles
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tb.riscv_env import RiscvEnv
from tb.riscv_sequences import RandomSequence

log = logging.getLogger("riscv.test.rand")

def _get_plusarg(name: str, default):
    """Read cocotb plusargs: +name=value"""
    val = cocotb.plusargs.get(name, None)
    if val is None:
        return default
    if default is None:
        return val          # return raw string when no type hint
    return type(default)(val)


@cocotb.test()
async def test_rand(dut):
    """Random instruction test."""
    num_instrs   = _get_plusarg("num_instrs",   1000)
    branch_pct   = _get_plusarg("branch_pct",   10)
    load_pct     = _get_plusarg("load_pct",      20)
    store_pct    = _get_plusarg("store_pct",     10)
    hazard_heavy = _get_plusarg("hazard_mode",   "") == "heavy"
    seed         = _get_plusarg("seed",          None)

    log.info(f"Config: num_instrs={num_instrs} branch={branch_pct}% "
             f"load={load_pct}% hazard_heavy={hazard_heavy} seed={seed}")

    seq = RandomSequence(
        num_instrs   = num_instrs,
        branch_pct   = branch_pct,
        load_pct     = load_pct,
        store_pct    = store_pct,
        hazard_heavy = hazard_heavy,
        seed         = int(seed) if seed else None,
    )
    program = seq.generate()

    env = RiscvEnv(dut)
    await env.start()
    await env.driver.load_program(program)

    # Wait: num_instrs × worst-case 5 cycles + pipeline flush
    await ClockCycles(dut.clk, num_instrs * 6 + 50)

    env.scoreboard.report()
    log.info("test_rand PASSED")
