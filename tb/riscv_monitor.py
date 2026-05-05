# riscv_monitor.py
# Watches the RVFI retirement bus and emits RvfiTransaction objects.
# Equivalent to riscv_monitor.sv in the UVM branch.
# Portability note: works with any RVFI-compliant core unchanged.

import cocotb
from cocotb.triggers import RisingEdge
import logging
from .riscv_types import RvfiTransaction
import cocotb.utils

class RiscvMonitor:
    """
    Samples the RVFI bus on every rvfi_valid pulse.
    Calls self._callbacks with each captured transaction.
    """

    def __init__(self, dut):
        self.dut       = dut
        self.log       = logging.getLogger("riscv.monitor")
        self._callbacks = []

    def add_callback(self, cb):
        """Register a function to call on every committed transaction."""
        self._callbacks.append(cb)

    async def run(self):
        """Start monitoring — run as a background coroutine."""
        clk = self.dut.clk

        # Wait for reset deassert
        await RisingEdge(clk)
        while self.dut.rst_n.value == 0:
            await RisingEdge(clk)

        self.log.info("Monitor active — watching RVFI bus")

        while True:
            await RisingEdge(clk)

            # rvfi_valid pulses for exactly one cycle per committed instruction
            if self.dut.rvfi_valid.value == 1:
                t = RvfiTransaction(
                    instr      = int(self.dut.rvfi_insn.value),
                    rd         = int(self.dut.rvfi_rd_addr.value),
                    rd_wdata   = int(self.dut.rvfi_rd_wdata.value),
                    pc_rdata   = int(self.dut.rvfi_pc_rdata.value),
                    pc_wdata   = int(self.dut.rvfi_pc_wdata.value),
                    rs1_rdata  = int(self.dut.rvfi_rs1_rdata.value),
                    rs2_rdata  = int(self.dut.rvfi_rs2_rdata.value),
                    mem_addr   = int(self.dut.rvfi_mem_addr.value),
                    mem_rmask  = int(self.dut.rvfi_mem_rmask.value),
                    mem_wmask  = int(self.dut.rvfi_mem_wmask.value),
                    mem_rdata  = int(self.dut.rvfi_mem_rdata.value),
                    mem_wdata  = int(self.dut.rvfi_mem_wdata.value),
                    sim_time   = cocotb.utils.get_sim_time(unit="ns"),
                )

                self.log.debug(
                    f"Committed: PC=0x{t.pc_rdata:08x} "
                    f"instr=0x{t.instr:08x} "
                    f"rd=x{t.rd} wdata=0x{t.rd_wdata:08x} "
                    f"next_pc=0x{t.pc_wdata:08x}"
                )

                for cb in self._callbacks:
                    cb(t)
