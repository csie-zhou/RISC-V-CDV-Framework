#ifndef ISA_MODEL_H
#define ISA_MODEL_H

#include <stdint.h>

/* Architectural state — mirrors Ibex's integer register file + PC */
typedef struct {
    uint32_t regs[32];   /* x0–x31, x0 always reads 0                */
    uint32_t pc;         /* program counter                           */
    uint32_t mem[1024];  /* flat word-addressed memory (4 KB)         */
} isa_state_t;

/* Decoded instruction fields */
typedef struct {
    uint32_t opcode;
    uint32_t rd, rs1, rs2;
    uint32_t funct3, funct7;
    int32_t  imm;        /* sign-extended immediate                   */
    uint32_t raw;        /* original 32-bit encoding                  */
} isa_decoded_t;

/* API */
void     isa_init   (isa_state_t *s);
void     isa_decode (uint32_t instr, isa_decoded_t *d);
int      isa_execute(isa_state_t *s, const isa_decoded_t *d);  /* returns 0=ok, -1=illegal */
uint32_t isa_rd_reg (const isa_state_t *s, uint32_t idx);
uint32_t isa_rd_pc  (const isa_state_t *s);

#endif /* ISA_MODEL_H */
