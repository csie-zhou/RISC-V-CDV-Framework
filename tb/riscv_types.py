# riscv_types.py
# Shared transaction type — mirrors riscv_trans_t from the UVM branch.
# Week 2 adds InstrType, HazardType, InstrItem.

from dataclasses import dataclass, field
from enum import Enum, auto

# ── Mirrors instr_type_e from UVM branch ─────────────────────
class InstrType(Enum):
    R_TYPE  = auto()
    I_ALU   = auto()
    I_LOAD  = auto()
    S_TYPE  = auto()
    B_TYPE  = auto()
    U_LUI   = auto()
    U_AUIPC = auto()
    J_TYPE  = auto()


# ── Mirrors hazard_type_e from UVM branch ────────────────────
class HazardType(Enum):
    NONE      = auto()
    RAW_1     = auto()   # read-after-write, distance 1
    RAW_2     = auto()
    RAW_3     = auto()
    LOAD_USE  = auto()   # load followed immediately by dependent op
    WAW       = auto()   # write-after-write


# ── One instruction with metadata — mirrors riscv_instr_item.sv
@dataclass
class InstrItem:
    encoding: int = 0x0000_0013   # default NOP
    itype:    InstrType  = InstrType.I_ALU
    hazard:   HazardType = HazardType.NONE
    rd:  int = 0
    rs1: int = 0
    rs2: int = 0
    imm: int = 0

    def __repr__(self):
        return (f"InstrItem(enc=0x{self.encoding:08x} "
                f"type={self.itype.name} rd=x{self.rd} "
                f"hazard={self.hazard.name})")


# ── RVFI transaction — unchanged from Week 1 ─────────────────
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
