#include "svdpi.h"
#include "isa_model.h"
#include <stdio.h>

/*
 * Single global ISA state — one instance per simulation.
 * Reset by calling isa_reset_dpi() from tb_top initial block.
 */
static isa_state_t g_state;
static int g_initialized = 0;

/* ── Called from SV initial block before simulation starts ─── */
void isa_reset_dpi(void) {
    isa_init(&g_state);
    g_initialized = 1;
}

/*
 * isa_step_dpi()
 *
 * Called by the scoreboard every cycle a valid RVFI retirement occurs.
 *
 * Inputs  (from SV via RVFI monitor):
 *   instr      — 32-bit instruction encoding
 *   rvfi_rs1   — rs1 value observed on RVFI bus (for memory model sync)
 *   rvfi_rs2   — rs2 value
 *   rvfi_mem_addr — effective memory address (for store sync)
 *   rvfi_mem_wdata — store data
 *   rvfi_mem_rmask — read mask (non-zero = this was a load)
 *
 * Outputs (compared against Ibex's rvfi_rd_wdata and rvfi_pc_wdata):
 *   model_rd       — destination register index
 *   model_rd_wdata — value written to rd by reference model
 *   model_pc_next  — next PC computed by reference model
 *   model_valid    — 1 if instruction was legal
 */
void isa_step_dpi(
    svLogicVecVal *instr,
    svLogicVecVal *rvfi_rs1,
    svLogicVecVal *rvfi_rs2,
    svLogicVecVal *rvfi_mem_addr,
    svLogicVecVal *rvfi_mem_wdata,
    svLogicVecVal *rvfi_mem_rmask,
    svLogicVecVal *model_rd,
    svLogicVecVal *model_rd_wdata,
    svLogicVecVal *model_pc_next,
    svLogicVecVal *model_valid
) {
    if (!g_initialized) {
        fprintf(stderr, "[DPI] ERROR: isa_step_dpi called before isa_reset_dpi\n");
        model_valid->aval = 0;
        return;
    }

    uint32_t raw_instr      = instr->aval;
    uint32_t mem_addr       = rvfi_mem_addr->aval >> 2;   /* word address */
    uint32_t mem_wdata      = rvfi_mem_wdata->aval;
    uint32_t mem_rmask      = rvfi_mem_rmask->aval;

    /* Sync memory: if RTL did a store, mirror it into our model memory */
    if (mem_rmask == 0 && rvfi_mem_addr->aval != 0) {
        /* store occurred — sync RTL write into ISA model */
        if (mem_addr < 1024) g_state.mem[mem_addr] = mem_wdata;
    }

    /* Decode and execute */
    isa_decoded_t dec;
    isa_decode(raw_instr, &dec);
    int ok = isa_execute(&g_state, &dec);

    /* Return outputs */
    model_rd->aval       = dec.rd;
    model_rd_wdata->aval = isa_rd_reg(&g_state, dec.rd);
    model_pc_next->aval  = isa_rd_pc(&g_state);
    model_valid->aval    = (ok == 0) ? 1 : 0;

    model_rd->bval       = 0;
    model_rd_wdata->bval = 0;
    model_pc_next->bval  = 0;
    model_valid->bval    = 0;
}
