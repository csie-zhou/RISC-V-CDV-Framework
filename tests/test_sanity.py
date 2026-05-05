# test_sanity.py
# 20-instruction directed program — identical program to UVM branch sanity test.
# Covers: ADDI, ADD, SUB, AND, OR, XOR, SRLI, SRAI, LUI, SW, LW, BEQ

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge
import logging

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tb.riscv_env import RiscvEnv

log = logging.getLogger("riscv.test.sanity")

# ── 20-instruction program (identical encoding to UVM branch) ──
PROGRAM = [
    0x00A00093,   # ADDI x1,  x0, 10       → x1  = 10
    0x01400113,   # ADDI x2,  x0, 20       → x2  = 20
    0x002081B3,   # ADD  x3,  x1, x2       → x3  = 30
    0x40110233,   # SUB  x4,  x2, x1       → x4  = 10
    0x0020F2B3,   # AND  x5,  x1, x2       → x5  = 0
    0x0020E333,   # OR   x6,  x1, x2       → x6  = 30
    0x0041C3B3,   # XOR  x7,  x3, x4       → x7  = 20
    0xFFF00413,   # ADDI x8,  x0, -1       → x8  = 0xFFFFFFFF
    0x00145493,   # SRLI x9,  x8, 1        → x9  = 0x7FFFFFFF
    0x40145513,   # SRAI x10, x8, 1        → x10 = 0xFFFFFFFF
    0x002095B3,   # SLL  x11, x1, x2       → x11 = 10 << 20
    0x01422613,   # SLTI x12, x4, 20       → x12 = 1
    0x005236B3,   # SLTU x13, x4, x5  (placeholder — adjust if needed)
    0xABCDE737,   # LUI  x14, 0xABCDE      → x14 = 0xABCDE000
    0x00102023,   # SW   x1,  0(x0)        → mem[0] = 10
    0x00202223,   # SW   x2,  4(x0)        → mem[1] = 20
    0x00002783,   # LW   x15, 0(x0)        → x15 = 10
    0x00402803,   # LW   x16, 4(x0)        → x16 = 20
    0x00178463,   # BEQ  x15, x1, +8       → branch taken (10 == 10)
    0x06300893,   # ADDI x17, x0, 99       → SKIPPED by branch above
]

# Expected final register state (checked at end of test)
EXPECTED = {
    1:  10,
    2:  20,
    3:  30,
    4:  10,
    5:  0,
    6:  30,
    7:  20,
    8:  0xFFFFFFFF,
    9:  0x7FFFFFFF,
    10: 0xFFFFFFFF,
    14: 0xABCDE000,
    15: 10,
    16: 20,
    17: 0,           # must be 0 — branch skipped this instruction
}


@cocotb.test()
async def test_sanity(dut):
    """
    Directed sanity test — equivalent to riscv_sanity_test.sv in UVM branch.
    Loads 20 instructions, runs until all commit, checks scoreboard + final state.
    """
    env = RiscvEnv(dut)
    await env.start()

    # Load program and release reset
    await env.driver.load_program(PROGRAM)

    log.info("Waiting for all instructions to commit...")

    # BEQ skips one instruction → 19 instructions committed (not 20)
    expected_commits = 19
    clk = dut.clk

    # Wait until expected commits arrive rather than a fixed cycle count,
    # so we don't keep counting NOPs that run after the program ends.
    TIMEOUT_CYCLES = 500
    for _ in range(TIMEOUT_CYCLES):
        await RisingEdge(clk)
        if env.scoreboard.total_cnt >= expected_commits:
            break
    else:
        raise AssertionError(
            f"Timeout: only {env.scoreboard.total_cnt}/{expected_commits} "
            f"commits after {TIMEOUT_CYCLES} cycles"
        )

    # ── Check scoreboard ─────────────────────────────────────
    env.scoreboard.report()

    # ── Verify committed count ───────────────────────────────
    assert env.scoreboard.total_cnt == expected_commits, (
        f"Expected {expected_commits} commits, "
        f"got {env.scoreboard.total_cnt}"
    )

    # ── Verify final register state via ISA model ────────────
    log.info("Checking final register state...")
    for reg_idx, expected_val in EXPECTED.items():
        actual = env.scoreboard.model.reg(reg_idx)
        assert actual == expected_val, (
            f"x{reg_idx}: expected 0x{expected_val:08x}, "
            f"got 0x{actual:08x}"
        )
        log.info(f"  x{reg_idx} = 0x{actual:08x}  ✓")

    log.info("=" * 42)
    log.info("SANITY TEST PASSED")
    log.info("=" * 42)
