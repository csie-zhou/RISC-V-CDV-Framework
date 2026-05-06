# riscv_env.py
# Wires driver, monitor, and scoreboard together.
# Equivalent to riscv_env.sv + riscv_agent.sv in the UVM branch.

import logging
import cocotb
from .riscv_driver     import RiscvDriver
from .riscv_monitor    import RiscvMonitor
from .riscv_scoreboard import RiscvScoreboard

class RiscvEnv:
    """
    Top-level verification environment.
    Usage:
        env = RiscvEnv(dut)
        await env.start()
        await env.driver.load_program(program)
        # ... wait for test to complete ...
        env.scoreboard.report()
    """

    def __init__(self, dut):
        self.dut        = dut
        self.driver     = RiscvDriver(dut)
        self.monitor    = RiscvMonitor(dut)
        self.scoreboard = RiscvScoreboard()

        # Wire monitor → scoreboard (equivalent to UVM analysis port connect)
        self.monitor.add_callback(self.scoreboard.check)

    async def start(self):
        """Launch background monitor coroutine."""
        logging.getLogger("riscv").setLevel(logging.DEBUG)
        self.scoreboard.reset()
        cocotb.start_soon(self.monitor.run())
