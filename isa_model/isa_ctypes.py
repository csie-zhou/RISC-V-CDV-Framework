# isa_ctypes.py
# Python wrapper around the C ISA reference model.
# Equivalent role to dpi_bridge.c in the UVM branch.
# Loads libisa.so via ctypes and exposes isa_step() to the scoreboard.

import ctypes
import os
from pathlib import Path

# ── C struct mirror: isa_state_t ─────────────────────────────
class IsaState(ctypes.Structure):
    _fields_ = [
        ("regs", ctypes.c_uint32 * 32),
        ("pc",   ctypes.c_uint32),
        ("mem",  ctypes.c_uint32 * 1024),
    ]

# ── C struct mirror: isa_decoded_t ───────────────────────────
class IsaDecoded(ctypes.Structure):
    _fields_ = [
        ("opcode", ctypes.c_uint32),
        ("rd",     ctypes.c_uint32),
        ("rs1",    ctypes.c_uint32),
        ("rs2",    ctypes.c_uint32),
        ("funct3", ctypes.c_uint32),
        ("funct7", ctypes.c_uint32),
        ("imm",    ctypes.c_int32),
        ("raw",    ctypes.c_uint32),
    ]

class IsaModel:
    """
    Python interface to the C ISA reference model.
    Mirrors the scoreboard usage pattern from the UVM branch exactly:
        model = IsaModel()
        result = model.step(instr, mem_addr, mem_wdata, mem_wmask)
    """

    def __init__(self):
        lib_path = Path(__file__).parent / "libisa.so"
        if not lib_path.exists():
            raise FileNotFoundError(
                f"libisa.so not found at {lib_path}\n"
                f"Run: cd isa_model && gcc -O2 -shared -fPIC -o libisa.so isa_model.c"
            )

        self._lib = ctypes.CDLL(str(lib_path))
        self._state = IsaState()
        self._decoded = IsaDecoded()

        # Bind C function signatures
        self._lib.isa_init.argtypes    = [ctypes.POINTER(IsaState)]
        self._lib.isa_init.restype     = None

        self._lib.isa_decode.argtypes  = [ctypes.c_uint32,
                                           ctypes.POINTER(IsaDecoded)]
        self._lib.isa_decode.restype   = None

        self._lib.isa_execute.argtypes = [ctypes.POINTER(IsaState),
                                           ctypes.POINTER(IsaDecoded)]
        self._lib.isa_execute.restype  = ctypes.c_int

        self._lib.isa_rd_reg.argtypes  = [ctypes.POINTER(IsaState),
                                           ctypes.c_uint32]
        self._lib.isa_rd_reg.restype   = ctypes.c_uint32

        self._lib.isa_rd_pc.argtypes   = [ctypes.POINTER(IsaState)]
        self._lib.isa_rd_pc.restype    = ctypes.c_uint32

        # Initialise state
        self._lib.isa_init(ctypes.byref(self._state))

    def reset(self):
        """Reset architectural state — call at start of each test."""
        self._lib.isa_init(ctypes.byref(self._state))

    def step(self,
             instr:      int,
             mem_addr:   int = 0,
             mem_wdata:  int = 0,
             mem_wmask:  int = 0) -> dict:
        """
        Execute one instruction in the reference model.

        Args:
            instr     : 32-bit instruction encoding (from rvfi_insn)
            mem_addr  : effective memory address (from rvfi_mem_addr)
            mem_wdata : store data (from rvfi_mem_wdata)
            mem_wmask : write byte mask — non-zero means this was a store

        Returns dict:
            rd        : destination register index
            rd_wdata  : value written to rd
            pc_next   : next PC
            valid     : True if instruction was legal
        """
        # Sync store to model memory (mirrors dpi_bridge.c memory sync)
        if mem_wmask != 0:
            word_addr = (mem_addr >> 2) & 0x3FF
            if word_addr < 1024:
                self._state.mem[word_addr] = mem_wdata

        self._lib.isa_decode(ctypes.c_uint32(instr),
                             ctypes.byref(self._decoded))
        rc = self._lib.isa_execute(ctypes.byref(self._state),
                                   ctypes.byref(self._decoded))

        return {
            "rd":       self._decoded.rd,
            "rd_wdata": self._lib.isa_rd_reg(ctypes.byref(self._state),
                                              self._decoded.rd),
            "pc_next":  self._lib.isa_rd_pc(ctypes.byref(self._state)),
            "valid":    (rc == 0),
        }

    def reg(self, idx: int) -> int:
        """Read a register directly — for end-of-test state dump."""
        if idx == 0:
            return 0
        return self._state.regs[idx]

    def pc(self) -> int:
        return self._lib.isa_rd_pc(ctypes.byref(self._state))
