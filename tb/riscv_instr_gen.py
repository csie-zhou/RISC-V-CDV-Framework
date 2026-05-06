# riscv_instr_gen.py
# Constrained-random RISC-V instruction generator.
# Python equivalent of riscv_instr_gen.sv from the UVM branch.
# Same knobs, same constraint categories, same corner-case coverage goals.

import random
from .riscv_types import InstrItem, InstrType, HazardType


# ── Encoding helpers (mirrors riscv_instr_item.assemble()) ────

def _sign_ext(val: int, bits: int) -> int:
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val

def encode_r(rd, rs1, rs2, funct3, funct7_bit5=0) -> int:
    return ((funct7_bit5 << 30) | (rs2 << 20) | (rs1 << 15) |
            (funct3 << 12) | (rd << 7) | 0x33)

def encode_i(rd, rs1, imm12, funct3, opcode=0x13) -> int:
    return (((imm12 & 0xFFF) << 20) | (rs1 << 15) |
            (funct3 << 12) | (rd << 7) | opcode)

def encode_load(rd, rs1, imm12, funct3=0x2) -> int:
    return encode_i(rd, rs1, imm12, funct3, opcode=0x03)

def encode_store(rs1, rs2, imm12, funct3=0x2) -> int:
    imm = imm12 & 0xFFF
    return (((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) |
            (funct3 << 12) | ((imm & 0x1F) << 7) | 0x23)

def encode_branch(rs1, rs2, imm13, funct3=0x0) -> int:
    # imm13 is a signed 13-bit offset (bit 0 always 0)
    imm = imm13 & 0x1FFF
    return (((imm >> 12) << 31) | (((imm >> 5) & 0x3F) << 25) |
            (rs2 << 20) | (rs1 << 15) | (funct3 << 12) |
            (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | 0x63)

def encode_lui(rd, imm20) -> int:
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x37

NOP = 0x0000_0013


class RiscvInstrGen:
    """
    Generates legal RV32I instruction streams.
    Equivalent to riscv_instr_gen.sv in the UVM branch.

    Knobs (mirror UVM plusargs):
        num_instrs   — total instructions to generate (default 100)
        raw_distance — fixed RAW distance 1-4, or -1 for random
        branch_pct   — % of instructions that are branches (default 10)
        load_pct     — % that are loads (default 20)
        store_pct    — % that are stores (default 10)
        hazard_heavy — if True: force raw_distance=1 for 80% of instrs
    """

    # funct3 values for I-type ALU ops
    _I_ALU_FUNCT3 = [0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7]
    # funct3 values for R-type ops
    _R_FUNCT3     = [0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7]
    # funct3 values for branch ops
    _B_FUNCT3     = [0x0, 0x1, 0x4, 0x5, 0x6, 0x7]

    def __init__(self,
                 num_instrs:   int  = 100,
                 raw_distance: int  = -1,
                 branch_pct:   int  = 10,
                 load_pct:     int  = 20,
                 store_pct:    int  = 10,
                 hazard_heavy: bool = False,
                 seed:         int  = None):
        self.num_instrs   = num_instrs
        self.raw_distance = raw_distance
        self.branch_pct   = branch_pct
        self.load_pct     = load_pct
        self.store_pct    = store_pct
        self.hazard_heavy = hazard_heavy
        self.rng = random.Random(seed)

    def generate_program(self) -> list[InstrItem]:
        """
        Returns a list of InstrItem with valid encodings.
        Equivalent to riscv_instr_gen.generate_program() in SV.
        """
        program: list[InstrItem] = []
        prev: InstrItem | None = None

        for _ in range(self.num_instrs):
            itype = self._pick_type()
            item  = self._make_instr(itype)

            # Inject RAW hazard — skip loads: _reassemble re-encodes the base
            # register, turning a safe x0-based address into an arbitrary one.
            if prev is not None and prev.rd != 0:
                dist = self._raw_distance()
                if dist == 1 and item.itype != InstrType.I_LOAD:
                    item.rs1    = prev.rd
                    item.hazard = HazardType.RAW_1
                    item       = self._reassemble(item)

            # Load-use injection — same guard: don't change the load's base reg.
            if (prev is not None and
                    prev.itype == InstrType.I_LOAD and
                    prev.rd != 0 and
                    self.rng.randint(0, 99) < 40 and
                    item.itype != InstrType.I_LOAD):
                item.rs1    = prev.rd
                item.hazard = HazardType.LOAD_USE
                item        = self._reassemble(item)

            program.append(item)
            prev = item

        return program

    # ── Private helpers ───────────────────────────────────────

    def _pick_type(self) -> InstrType:
        roll = self.rng.randint(0, 99)
        if roll < self.branch_pct:
            return InstrType.B_TYPE
        roll -= self.branch_pct
        if roll < self.load_pct:
            return InstrType.I_LOAD
        roll -= self.load_pct
        if roll < self.store_pct:
            return InstrType.S_TYPE
        if roll < self.store_pct + 30:
            return InstrType.R_TYPE
        return InstrType.I_ALU

    def _raw_distance(self) -> int:
        if self.raw_distance >= 1:
            return self.raw_distance
        if self.hazard_heavy:
            return 1 if self.rng.randint(0, 99) < 80 else self.rng.randint(2, 4)
        roll = self.rng.randint(0, 99)
        if roll < 40:  return 1
        if roll < 70:  return 2
        return self.rng.randint(3, 4)

    def _rand_reg(self, exclude_zero=True) -> int:
        lo = 1 if exclude_zero else 0
        return self.rng.randint(lo, 31)

    def _rand_imm12(self) -> int:
        return self.rng.randint(0, 0xFFF)

    def _rand_dmem_imm(self) -> int:
        # Stay within DMEM range (256 words = byte offset 0–0x3FC)
        return self.rng.randint(0, 255) * 4

    def _make_instr(self, itype: InstrType) -> InstrItem:
        rd  = self._rand_reg()
        rs1 = self._rand_reg()
        rs2 = self._rand_reg()

        if itype == InstrType.R_TYPE:
            f3   = self.rng.choice(self._R_FUNCT3)
            # For funct3=0 (ADD/SUB) and funct3=5 (SRL/SRA), bit5 of funct7 selects variant
            f7b5 = self.rng.randint(0, 1) if f3 in (0x0, 0x5) else 0
            enc  = encode_r(rd, rs1, rs2, f3, f7b5)
            return InstrItem(encoding=enc, itype=itype, rd=rd, rs1=rs1, rs2=rs2)

        elif itype == InstrType.I_ALU:
            f3  = self.rng.choice(self._I_ALU_FUNCT3)
            imm = self._rand_imm12()
            # Constraint: shift amount must be in [0,31] — zero out upper bits
            if f3 in (0x1, 0x5):
                imm = imm & 0x01F
            # SRAI: set bit 10 of imm (funct7[5])
            if f3 == 0x5 and self.rng.randint(0, 1):
                imm |= (1 << 10)
            enc = encode_i(rd, rs1, imm, f3)
            return InstrItem(encoding=enc, itype=itype, rd=rd, rs1=rs1, imm=imm)

        elif itype == InstrType.I_LOAD:
            imm = self._rand_dmem_imm()
            enc = encode_load(rd, rs1=0, imm12=imm)  # base x0 for simplicity
            return InstrItem(encoding=enc, itype=itype, rd=rd, rs1=0, imm=imm)

        elif itype == InstrType.S_TYPE:
            imm = self._rand_dmem_imm()
            enc = encode_store(rs1=0, rs2=rs2, imm12=imm)
            return InstrItem(encoding=enc, itype=itype, rs1=0, rs2=rs2, imm=imm)

        elif itype == InstrType.B_TYPE:
            f3  = self.rng.choice(self._B_FUNCT3)
            # Safe forward branch: +8 (skip one instruction)
            imm = 8
            enc = encode_branch(rs1, rs2, imm, f3)
            return InstrItem(encoding=enc, itype=itype, rs1=rs1, rs2=rs2, imm=imm)

        elif itype == InstrType.U_LUI:
            imm = self.rng.randint(0, 0xFFFFF)
            enc = encode_lui(rd, imm)
            return InstrItem(encoding=enc, itype=itype, rd=rd, imm=imm)

        # fallback NOP
        return InstrItem(encoding=NOP, itype=InstrType.I_ALU)

    def _reassemble(self, item: InstrItem) -> InstrItem:
        """Re-encode an item after field modification (e.g. rs1 changed for RAW)."""
        if item.itype == InstrType.R_TYPE:
            # Extract funct3/funct7 from existing encoding and re-encode
            f3   = (item.encoding >> 12) & 0x7
            f7b5 = (item.encoding >> 30) & 0x1
            item.encoding = encode_r(item.rd, item.rs1, item.rs2, f3, f7b5)
        elif item.itype in (InstrType.I_ALU, InstrType.I_LOAD):
            f3  = (item.encoding >> 12) & 0x7
            opc = item.encoding & 0x7F
            imm = (item.encoding >> 20) & 0xFFF
            item.encoding = encode_i(item.rd, item.rs1, imm, f3, opc)
        return item
