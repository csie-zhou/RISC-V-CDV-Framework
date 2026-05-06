# riscv_driver.py (Week 2 update)
# Accepts list[InstrItem] from a sequence instead of a raw int list.

import logging
import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from .riscv_types import InstrItem

NOP = 0x0000_0013

class RiscvDriver:

    def __init__(self, dut):
        self.dut = dut
        self.log = logging.getLogger("riscv.driver")

    async def load_program(self, program: list[InstrItem] | list[int]):
        """
        Accepts either list[InstrItem] (Week 2+) or list[int] (Week 1 compat).
        Writes encodings into IMEM, releases reset.
        """
        clk = self.dut.clk
        self.dut.rst_n.value = 0
        await ClockCycles(clk, 5)

        # Normalise to list of ints
        words = [
            item.encoding if isinstance(item, InstrItem) else item
            for item in program
        ]

        for i, word in enumerate(words[:2048]):
            self.dut.imem[i].value = word

        for i in range(len(words), 2048):
            self.dut.imem[i].value = NOP

        self.log.info(f"IMEM loaded: {len(words)} instructions")
        await RisingEdge(clk)
        self.dut.rst_n.value = 1
        self.log.info("Reset released")
