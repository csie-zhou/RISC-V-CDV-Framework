# riscv_sequences.py
# Directed, random, and stress sequences.
# Equivalent to riscv_directed_seq.sv, riscv_rand_seq.sv,
# riscv_stress_seq.sv in the UVM branch.

from .riscv_types import InstrItem, InstrType, HazardType
from .riscv_instr_gen import RiscvInstrGen, NOP, encode_i, encode_r, encode_load, encode_store, encode_branch, encode_lui


class DirectedSequence:
    """
    Hand-crafted corner cases — equivalent to riscv_directed_seq.sv.
    Returns list[InstrItem] ready to load into IMEM.
    """

    def generate(self) -> list[InstrItem]:
        program: list[InstrItem] = []
        program += self._self_dependency()
        program += self._lui_addi_pair()
        program += self._shift_extremes()
        program += self._branch_taken_zero()
        program += self._all_registers()
        program += self._imm_boundaries()
        program += self._load_use()
        program += [InstrItem(encoding=NOP)] * 8  # pipeline flush
        return program

    def _raw(self, enc: int) -> InstrItem:
        return InstrItem(encoding=enc)

    def _self_dependency(self) -> list[InstrItem]:
        return [
            self._raw(0x00500093),  # ADDI x1, x0, 5
            self._raw(0x00008093),  # ADDI x1, x1, 0  (self-dep)
        ]

    def _lui_addi_pair(self) -> list[InstrItem]:
        return [
            self._raw(0xDEAD0137),  # LUI  x2, 0xDEAD0
            self._raw(0x00010113),  # ADDI x2, x2, 0
        ]

    def _shift_extremes(self) -> list[InstrItem]:
        return [
            self._raw(0x00509093),  # SLLI x1, x1, 0
            self._raw(0x01f09093),  # SLLI x1, x1, 31
            self._raw(0x0000d093),  # SRLI x1, x1, 0
            self._raw(0x41f0d093),  # SRAI x1, x1, 31
        ]

    def _branch_taken_zero(self) -> list[InstrItem]:
        return [
            self._raw(0x00500093),  # ADDI x1, x0, 5
            self._raw(0x00500113),  # ADDI x2, x0, 5
            self._raw(0x00208463),  # BEQ  x1, x2, +8  → TAKEN
            self._raw(0x06300893),  # ADDI x17, x0, 99 → SKIPPED
            self._raw(0x00a00193),  # ADDI x3, x0, 10  → executes
        ]

    def _all_registers(self) -> list[InstrItem]:
        items = []
        for i in range(1, 32):
            enc = encode_i(rd=i, rs1=0, imm12=i, funct3=0x0)
            items.append(InstrItem(encoding=enc, itype=InstrType.I_ALU, rd=i))
        return items

    def _imm_boundaries(self) -> list[InstrItem]:
        boundaries = [0, 1, 0xFFF, 0x7FF, 0x800]  # 0,-1,2047,-2048 in 12-bit
        return [
            InstrItem(encoding=encode_i(rd=1, rs1=0, imm12=imm, funct3=0x0),
                      itype=InstrType.I_ALU)
            for imm in boundaries
        ]

    def _load_use(self) -> list[InstrItem]:
        return [
            self._raw(0x00A00093),  # ADDI x1, x0, 10
            self._raw(0x00102023),  # SW x1, 0(x0)
            self._raw(0x00002083),  # LW x1, 0(x0)
            self._raw(0x001080B3),  # ADD x1, x1, x1  (load-use stall)
        ]


class RandomSequence:
    """
    Generates N random instructions — equivalent to riscv_rand_seq.sv.
    """

    def __init__(self, **kwargs):
        self.gen = RiscvInstrGen(**kwargs)

    def generate(self) -> list[InstrItem]:
        program = self.gen.generate_program()
        program += [InstrItem(encoding=NOP)] * 8
        return program


class StressSequence:
    """
    Maximum hazard density — equivalent to riscv_stress_seq.sv.
    Three passes: RAW chains, load-use intensive, branch-heavy.
    """

    def generate(self) -> list[InstrItem]:
        flush = [InstrItem(encoding=NOP)] * 8
        program = []

        # Pass 1: back-to-back RAW chains
        program += RiscvInstrGen(
            num_instrs=200, hazard_heavy=True,
            branch_pct=0, load_pct=0
        ).generate_program() + flush

        # Pass 2: load-use intensive
        program += RiscvInstrGen(
            num_instrs=200, load_pct=60, store_pct=20, branch_pct=0
        ).generate_program() + flush

        # Pass 3: branch-heavy
        program += RiscvInstrGen(
            num_instrs=100, branch_pct=50, load_pct=5
        ).generate_program() + flush

        return program
