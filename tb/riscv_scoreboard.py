# riscv_scoreboard.py
# Lockstep comparison: RVFI observation vs C ISA reference model.
# Equivalent to riscv_scoreboard.sv in the UVM branch.
# Called by the monitor callback on every committed instruction.

import logging
from .riscv_types import RvfiTransaction
from isa_model.isa_ctypes import IsaModel

class RiscvScoreboard:
    """
    Receives RvfiTransaction from the monitor.
    Steps the C reference model.
    Compares rd_wdata and pc_next.
    Raises AssertionError on first mismatch.
    """

    def __init__(self):
        self.log       = logging.getLogger("riscv.scoreboard")
        self.model     = IsaModel()
        self.reg_state = [0] * 32   # Python-native mirror; ctypes writes unreliable
        self.pass_cnt  = 0
        self.fail_cnt  = 0
        self.total_cnt = 0

    def reset(self):
        """Reset model state — call before each test."""
        self.model.reset()
        self.reg_state = [0] * 32
        self.pass_cnt  = 0
        self.fail_cnt  = 0
        self.total_cnt = 0

    def check(self, t: RvfiTransaction):
        """
        Called by monitor callback on every committed instruction.
        This is the equivalent of uvm_scoreboard::write() in the UVM branch.
        """
        self.total_cnt += 1

        # Sync model PC from RVFI so any accumulated skew is corrected
        # each cycle — pc_wdata is still checked against model output.
        self.model._state.pc = t.pc_rdata
        result = self.model.step(
            instr     = t.instr,
            mem_addr  = t.mem_addr,
            mem_wdata = t.mem_wdata,
            mem_wmask = t.mem_wmask,
        )

        # Check 1: instruction legality
        if not result["valid"]:
            msg = (f"[{t.sim_time}ns] Illegal instruction "
                   f"0x{t.instr:08x} at PC=0x{t.pc_rdata:08x}")
            self.log.error(msg)
            self.fail_cnt += 1
            raise AssertionError(msg)

        # Check 2: register write-back value
        if t.rd != 0:
            if t.rd_wdata != result["rd_wdata"]:
                msg = (
                    f"[{t.sim_time}ns] MISMATCH rd_wdata | "
                    f"PC=0x{t.pc_rdata:08x} instr=0x{t.instr:08x} "
                    f"rd=x{t.rd} | "
                    f"RTL=0x{t.rd_wdata:08x} "
                    f"MODEL=0x{result['rd_wdata']:08x}"
                )
                self.log.error(msg)
                self.fail_cnt += 1
                raise AssertionError(msg)

        # Check 3: next PC
        if t.pc_wdata != result["pc_next"]:
            msg = (
                f"[{t.sim_time}ns] MISMATCH pc_next | "
                f"PC=0x{t.pc_rdata:08x} instr=0x{t.instr:08x} | "
                f"RTL=0x{t.pc_wdata:08x} "
                f"MODEL=0x{result['pc_next']:08x}"
            )
            self.log.error(msg)
            self.fail_cnt += 1
            raise AssertionError(msg)

        # Sync model register state from RTL after each instruction so
        # per-instruction checks are independent (errors don't accumulate).
        if t.rd != 0:
            self.model._state.regs[t.rd] = t.rd_wdata
            self.reg_state[t.rd] = t.rd_wdata

        # All checks passed
        self.log.info(
            f"PASS #{self.total_cnt} | "
            f"PC=0x{t.pc_rdata:08x} "
            f"rd=x{t.rd}=0x{t.rd_wdata:08x} "
            f"next_pc=0x{t.pc_wdata:08x}"
        )
        self.pass_cnt += 1

    def report(self):
        """Print final results — call at end of test."""
        sep = "=" * 42
        self.log.info(
            f"\n{sep}\n"
            f"  SCOREBOARD RESULTS\n"
            f"  Total committed : {self.total_cnt}\n"
            f"  PASS            : {self.pass_cnt}\n"
            f"  FAIL            : {self.fail_cnt}\n"
            f"{sep}"
        )
        if self.fail_cnt > 0:
            raise AssertionError(
                f"TEST FAILED — {self.fail_cnt} mismatches. See log above.")
        self.log.info(
            "TEST PASSED — RTL matches ISA model on all instructions")
