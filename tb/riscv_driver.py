# riscv_driver.py
# Loads instruction program into Ibex IMEM, releases reset.
# Passive after that — monitor owns the RVFI bus.
# Equivalent to riscv_driver.sv in the UVM branch.

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
import logging

class RiscvDriver:
    """
    Drives stimulus into the DUT:
      1. Assert reset for 5 cycles
      2. Backdoor-write the instruction program into IMEM
      3. Deassert reset — pipeline starts fetching
      4. Go passive
    """

    def __init__(self, dut):
        self.dut = dut
        self.log = logging.getLogger("riscv.driver")

    async def load_program(self, program: list[int]):
        """
        program: list of 32-bit instruction words (index = word address)
        """
        clk = self.dut.clk

        # 1. Assert reset
        self.dut.rst_n.value = 0
        await ClockCycles(clk, 5)

        # 2. Backdoor-write IMEM
        #    Ibex boot vector is boot_addr_i + 0x80; with boot_addr_i=0
        #    the reset PC is 0x80 = word offset 32.
        BOOT_WORD = 0x80 // 4  # 32
        nop = 0x0000_0013
        for i in range(256):
            self.dut.imem[i].value = nop
        for i, word in enumerate(program):
            self.dut.imem[BOOT_WORD + i].value = word

        self.log.info(f"IMEM loaded: {len(program)} instructions")

        # 3. Release reset
        await RisingEdge(clk)
        self.dut.rst_n.value = 1
        self.log.info("Reset released — pipeline fetching")
