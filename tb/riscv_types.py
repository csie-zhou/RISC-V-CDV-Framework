# riscv_types.py
# Shared transaction type — mirrors riscv_trans_t from the UVM branch.

from dataclasses import dataclass, field

@dataclass
class RvfiTransaction:
    """
    One committed instruction captured from the RVFI retirement bus.
    Field names match Ibex's RVFI signal names exactly for easy mapping.
    """
    instr:       int = 0   # rvfi_insn
    rd:          int = 0   # rvfi_rd_addr
    rd_wdata:    int = 0   # rvfi_rd_wdata
    pc_rdata:    int = 0   # rvfi_pc_rdata  (PC of this instruction)
    pc_wdata:    int = 0   # rvfi_pc_wdata  (next PC)
    rs1_rdata:   int = 0   # rvfi_rs1_rdata
    rs2_rdata:   int = 0   # rvfi_rs2_rdata
    mem_addr:    int = 0   # rvfi_mem_addr
    mem_rmask:   int = 0   # rvfi_mem_rmask
    mem_wmask:   int = 0   # rvfi_mem_wmask
    mem_rdata:   int = 0   # rvfi_mem_rdata
    mem_wdata:   int = 0   # rvfi_mem_wdata
    sim_time:    int = 0   # cocotb.utils.get_sim_time()
