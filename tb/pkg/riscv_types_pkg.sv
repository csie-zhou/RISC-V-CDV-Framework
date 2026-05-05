// riscv_types_pkg.sv — shared types used across TB components

`ifndef RISCV_TYPES_PKG_SV
`define RISCV_TYPES_PKG_SV

package riscv_types_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    // Transaction type: one committed instruction, all RVFI fields
    typedef struct {
        logic [31:0] instr;
        logic [4:0]  rd;
        logic [31:0] rd_wdata;
        logic [31:0] pc_rdata;
        logic [31:0] pc_wdata;
        logic [31:0] rs1_rdata;
        logic [31:0] rs2_rdata;
        logic [31:0] mem_addr;
        logic [3:0]  mem_rmask;
        logic [3:0]  mem_wmask;
        logic [31:0] mem_rdata;
        logic [31:0] mem_wdata;
        longint      cycle;
    } riscv_trans_t;

endpackage

`endif
