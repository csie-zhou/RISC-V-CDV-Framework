// riscv_scoreboard.sv
// Lockstep comparison: RVFI observation vs C ISA reference model.

`ifndef RISCV_SCOREBOARD_SV
`define RISCV_SCOREBOARD_SV

// DPI-C imports — C functions declared in dpi_bridge.c
import "DPI-C" function void isa_reset_dpi();
import "DPI-C" function void isa_step_dpi(
    input  logic [31:0] instr,
    input  logic [31:0] rvfi_rs1,
    input  logic [31:0] rvfi_rs2,
    input  logic [31:0] rvfi_mem_addr,
    input  logic [31:0] rvfi_mem_wdata,
    input  logic [31:0] rvfi_mem_rmask,
    output logic [4:0]  model_rd,
    output logic [31:0] model_rd_wdata,
    output logic [31:0] model_pc_next,
    output logic        model_valid
);

class riscv_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(riscv_scoreboard)

    uvm_analysis_imp #(riscv_trans_t, riscv_scoreboard) analysis_export;

    int pass_cnt, fail_cnt, total_cnt;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        analysis_export = new("analysis_export", this);
        pass_cnt  = 0;
        fail_cnt  = 0;
        total_cnt = 0;
        // Reset the C ISA model at build time
        isa_reset_dpi();
    endfunction

    // Called by the monitor analysis port on every committed instruction
    function void write(riscv_trans_t t);
        logic [4:0]  model_rd;
        logic [31:0] model_rd_wdata;
        logic [31:0] model_pc_next;
        logic        model_valid;

        total_cnt++;

        // Step the C reference model
        isa_step_dpi(
            t.instr,
            t.rs1_rdata,
            t.rs2_rdata,
            t.mem_addr,
            t.mem_wdata,
            {28'b0, t.mem_rmask},
            model_rd,
            model_rd_wdata,
            model_pc_next,
            model_valid
        );

        // Check 1: instruction legality
        if (!model_valid) begin
            `uvm_error("SB", $sformatf(
                "[%0t] Illegal instruction: 0x%08h at PC=0x%08h",
                $time, t.instr, t.pc_rdata))
            fail_cnt++;
            return;
        end

        // Check 2: register write-back value
        if (t.rd != 5'd0) begin
            if (t.rd_wdata !== model_rd_wdata) begin
                `uvm_error("SB", $sformatf(
                    "[%0t] MISMATCH rd_wdata | PC=0x%08h instr=0x%08h rd=x%0d | RTL=0x%08h MODEL=0x%08h",
                    $time, t.pc_rdata, t.instr, t.rd, t.rd_wdata, model_rd_wdata))
                fail_cnt++;
                return;
            end
        end

        // Check 3: next PC
        if (t.pc_wdata !== model_pc_next) begin
            `uvm_error("SB", $sformatf(
                "[%0t] MISMATCH pc_next | PC=0x%08h instr=0x%08h | RTL=0x%08h MODEL=0x%08h",
                $time, t.pc_rdata, t.instr, t.pc_wdata, model_pc_next))
            fail_cnt++;
            return;
        end

        // All checks passed
        `uvm_info("SB", $sformatf(
            "[%0t] PASS #%0d | PC=0x%08h rd=x%0d=0x%08h next_pc=0x%08h",
            $time, total_cnt, t.pc_rdata, t.rd, t.rd_wdata, t.pc_wdata), UVM_MEDIUM)
        pass_cnt++;
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SB", $sformatf(
            "\n========================================\n" +
            "  SCOREBOARD RESULTS\n" +
            "  Total committed : %0d\n" +
            "  PASS            : %0d\n" +
            "  FAIL            : %0d\n" +
            "========================================",
            total_cnt, pass_cnt, fail_cnt), UVM_NONE)

        if (fail_cnt > 0)
            `uvm_error("SB", "TEST FAILED — see mismatch reports above")
        else
            `uvm_info("SB", "TEST PASSED — RTL matches ISA model on all instructions", UVM_NONE)
    endfunction

endclass

`endif
