#include "isa_model.h"
#include <string.h>
#include <stdio.h>

/* ── Opcode constants ──────────────────────────────────────── */
#define OP_LUI    0x37
#define OP_AUIPC  0x17
#define OP_JAL    0x6F
#define OP_JALR   0x67
#define OP_BRANCH 0x63
#define OP_LOAD   0x03
#define OP_STORE  0x23
#define OP_ALUI   0x13   /* I-type ALU  */
#define OP_ALUR   0x33   /* R-type ALU  */

/* ── Helpers ───────────────────────────────────────────────── */
static inline int32_t sign_ext(uint32_t val, int bits) {
    int shift = 32 - bits;
    return (int32_t)(val << shift) >> shift;
}

static inline uint32_t rd_reg(const isa_state_t *s, uint32_t idx) {
    return (idx == 0) ? 0 : s->regs[idx];
}

static inline void wr_reg(isa_state_t *s, uint32_t idx, uint32_t val) {
    if (idx != 0) s->regs[idx] = val;
}

/* ── Init ──────────────────────────────────────────────────── */
void isa_init(isa_state_t *s) {
    memset(s, 0, sizeof(*s));
}

/* ── Decode ────────────────────────────────────────────────── */
void isa_decode(uint32_t instr, isa_decoded_t *d) {
    d->raw    = instr;
    d->opcode = instr & 0x7F;
    d->rd     = (instr >> 7)  & 0x1F;
    d->rs1    = (instr >> 15) & 0x1F;
    d->rs2    = (instr >> 20) & 0x1F;
    d->funct3 = (instr >> 12) & 0x07;
    d->funct7 = (instr >> 25) & 0x7F;

    /* Immediate decoding by format */
    switch (d->opcode) {
        case OP_LUI:
        case OP_AUIPC:
            d->imm = (int32_t)(instr & 0xFFFFF000);
            break;
        case OP_JAL:
            d->imm = sign_ext(
                ((instr >> 31) & 1) << 20 |
                ((instr >> 12) & 0xFF) << 12 |
                ((instr >> 20) & 1) << 11 |
                ((instr >> 21) & 0x3FF) << 1, 21);
            break;
        case OP_JALR:
        case OP_LOAD:
        case OP_ALUI:
            d->imm = sign_ext(instr >> 20, 12);
            break;
        case OP_STORE:
            d->imm = sign_ext(
                ((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12);
            break;
        case OP_BRANCH:
            d->imm = sign_ext(
                ((instr >> 31) & 1) << 12 |
                ((instr >>  7) & 1) << 11 |
                ((instr >> 25) & 0x3F) << 5 |
                ((instr >>  8) & 0xF) << 1, 13);
            break;
        default:
            d->imm = 0;
            break;
    }
}

/* ── Execute ───────────────────────────────────────────────── */
int isa_execute(isa_state_t *s, const isa_decoded_t *d) {
    uint32_t pc   = s->pc;
    uint32_t rs1v = rd_reg(s, d->rs1);
    uint32_t rs2v = rd_reg(s, d->rs2);
    uint32_t result = 0;
    uint32_t next_pc = pc + 4;

    switch (d->opcode) {

        /* ── LUI / AUIPC ──────────────────────────────────── */
        case OP_LUI:
            result = (uint32_t)d->imm;
            wr_reg(s, d->rd, result);
            break;

        case OP_AUIPC:
            result = pc + (uint32_t)d->imm;
            wr_reg(s, d->rd, result);
            break;

        /* ── JAL ───────────────────────────────────────────── */
        case OP_JAL:
            wr_reg(s, d->rd, pc + 4);
            next_pc = pc + (uint32_t)d->imm;
            break;

        /* ── JALR ──────────────────────────────────────────── */
        case OP_JALR:
            wr_reg(s, d->rd, pc + 4);
            next_pc = (rs1v + (uint32_t)d->imm) & ~1u;
            break;

        /* ── BRANCH ────────────────────────────────────────── */
        case OP_BRANCH: {
            int taken = 0;
            switch (d->funct3) {
                case 0x0: taken = (rs1v == rs2v); break;              /* BEQ  */
                case 0x1: taken = (rs1v != rs2v); break;              /* BNE  */
                case 0x4: taken = ((int32_t)rs1v <  (int32_t)rs2v); break; /* BLT  */
                case 0x5: taken = ((int32_t)rs1v >= (int32_t)rs2v); break; /* BGE  */
                case 0x6: taken = (rs1v <  rs2v); break;              /* BLTU */
                case 0x7: taken = (rs1v >= rs2v); break;              /* BGEU */
                default: return -1;
            }
            if (taken) next_pc = pc + (uint32_t)d->imm;
            break;
        }

        /* ── LOAD ──────────────────────────────────────────── */
        case OP_LOAD: {
            uint32_t addr = (rs1v + (uint32_t)d->imm) >> 2; /* word addr */
            uint32_t raw_data = (addr < 1024) ? s->mem[addr] : 0;
            switch (d->funct3) {
                case 0x0: result = sign_ext(raw_data & 0xFF, 8);  break; /* LB  */
                case 0x1: result = sign_ext(raw_data & 0xFFFF, 16); break; /* LH  */
                case 0x2: result = raw_data; break;                /* LW  */
                case 0x4: result = raw_data & 0xFF; break;         /* LBU */
                case 0x5: result = raw_data & 0xFFFF; break;       /* LHU */
                default: return -1;
            }
            wr_reg(s, d->rd, result);
            break;
        }

        /* ── STORE ─────────────────────────────────────────── */
        case OP_STORE: {
            uint32_t addr = (rs1v + (uint32_t)d->imm) >> 2;
            if (addr < 1024) s->mem[addr] = rs2v;
            break;
        }

        /* ── I-type ALU ────────────────────────────────────── */
        case OP_ALUI: {
            int32_t imm = d->imm;
            uint32_t shamt = (uint32_t)imm & 0x1F;
            switch (d->funct3) {
                case 0x0: result = rs1v + (uint32_t)imm;          break; /* ADDI  */
                case 0x1: result = rs1v << shamt;                  break; /* SLLI  */
                case 0x2: result = ((int32_t)rs1v < imm) ? 1 : 0; break; /* SLTI  */
                case 0x3: result = (rs1v < (uint32_t)imm) ? 1 : 0;break; /* SLTIU */
                case 0x4: result = rs1v ^ (uint32_t)imm;          break; /* XORI  */
                case 0x5:
                    if (d->funct7 & 0x20)
                        result = (uint32_t)((int32_t)rs1v >> shamt); /* SRAI */
                    else
                        result = rs1v >> shamt;                        /* SRLI */
                    break;
                case 0x6: result = rs1v | (uint32_t)imm;          break; /* ORI   */
                case 0x7: result = rs1v & (uint32_t)imm;          break; /* ANDI  */
                default: return -1;
            }
            wr_reg(s, d->rd, result);
            break;
        }

        /* ── R-type ALU ────────────────────────────────────── */
        case OP_ALUR: {
            uint32_t shamt = rs2v & 0x1F;
            switch (d->funct3) {
                case 0x0:
                    result = (d->funct7 & 0x20) ?
                        rs1v - rs2v : rs1v + rs2v;                 break; /* ADD/SUB */
                case 0x1: result = rs1v << shamt;                  break; /* SLL  */
                case 0x2: result = ((int32_t)rs1v < (int32_t)rs2v) ? 1 : 0; break; /* SLT */
                case 0x3: result = (rs1v < rs2v) ? 1 : 0;         break; /* SLTU */
                case 0x4: result = rs1v ^ rs2v;                    break; /* XOR  */
                case 0x5:
                    if (d->funct7 & 0x20)
                        result = (uint32_t)((int32_t)rs1v >> shamt); /* SRA */
                    else
                        result = rs1v >> shamt;                        /* SRL */
                    break;
                case 0x6: result = rs1v | rs2v;                    break; /* OR   */
                case 0x7: result = rs1v & rs2v;                    break; /* AND  */
                default: return -1;
            }
            wr_reg(s, d->rd, result);
            break;
        }

        default:
            return -1; /* illegal / unsupported */
    }

    s->pc = next_pc;
    return 0;
}

uint32_t isa_rd_reg(const isa_state_t *s, uint32_t idx) {
    return rd_reg(s, idx);
}

uint32_t isa_rd_pc(const isa_state_t *s) {
    return s->pc;
}
