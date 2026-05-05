// tb_top.sv — Top-level testbench
// Instantiates Ibex core, binds all interfaces, kicks off UVM.

`timescale 1ns/1ps
`include "uvm_macros.svh"

import uvm_pkg::*;
import riscv_types_pkg::*;

module tb_top;

    // ── Clock ────────────────────────────────────────────────
    logic clk = 1'b0;
    always #5 clk = ~clk;   // 100 MHz

    // ── Reset (driven by driver via ctrl_vif) ────────────────
    logic rst_n;

    // ── Instruction memory (256 x 32-bit words = 1 KB) ───────
    logic [31:0] imem [0:255];
    initial foreach (imem[i]) imem[i] = 32'h0000_0013; // NOP

    // ── Data memory (256 x 32-bit words) ─────────────────────
    logic [31:0] dmem [0:255];
    initial foreach (dmem[i]) dmem[i] = '0;

    // ── Ibex instruction fetch interface ─────────────────────
    logic        instr_req;
    logic        instr_gnt;
    logic        instr_rvalid;
    logic [31:0] instr_addr;
    logic [31:0] instr_rdata;
    logic        instr_err;

    // ── Ibex data interface ───────────────────────────────────
    logic        data_req;
    logic        data_gnt;
    logic        data_rvalid;
    logic        data_we;
    logic [3:0]  data_be;
    logic [31:0] data_addr;
    logic [31:0] data_wdata;
    logic [31:0] data_rdata;
    logic        data_err;

    // ── RVFI outputs ──────────────────────────────────────────
    logic        rvfi_valid;
    logic [63:0] rvfi_order;
    logic [31:0] rvfi_insn;
    logic        rvfi_trap;
    logic        rvfi_halt;
    logic        rvfi_intr;
    logic [1:0]  rvfi_mode;
    logic [1:0]  rvfi_ixl;
    logic [4:0]  rvfi_rs1_addr;
    logic [4:0]  rvfi_rs2_addr;
    logic [31:0] rvfi_rs1_rdata;
    logic [31:0] rvfi_rs2_rdata;
    logic [4:0]  rvfi_rd_addr;
    logic [31:0] rvfi_rd_wdata;
    logic [31:0] rvfi_pc_rdata;
    logic [31:0] rvfi_pc_wdata;
    logic [31:0] rvfi_mem_addr;
    logic [3:0]  rvfi_mem_rmask;
    logic [3:0]  rvfi_mem_wmask;
    logic [31:0] rvfi_mem_rdata;
    logic [31:0] rvfi_mem_wdata;

    // ── Ibex DUT ──────────────────────────────────────────────
    ibex_top #(
        .PMPEnable        (1'b0),
        .MHPMCounterNum   (0),
        .RV32M            (ibex_pkg::RV32MNone),   // no multiply for Week 1
        .RV32B            (ibex_pkg::RV32BNone),
        .WritebackStage   (1'b1),
        .ICache           (1'b0)
    ) u_ibex (
        .clk_i            (clk),
        .rst_ni           (rst_n),

        // Instruction fetch
        .instr_req_o      (instr_req),
        .instr_gnt_i      (instr_gnt),
        .instr_rvalid_i   (instr_rvalid),
        .instr_addr_o     (instr_addr),
        .instr_rdata_i    (instr_rdata),
        .instr_rdata_intg_i('0),
        .instr_err_i      (instr_err),

        // Data
        .data_req_o       (data_req),
        .data_gnt_i       (data_gnt),
        .data_rvalid_i    (data_rvalid),
        .data_we_o        (data_we),
        .data_be_o        (data_be),
        .data_addr_o      (data_addr),
        .data_wdata_o     (data_wdata),
        .data_wdata_intg_o(),
        .data_rdata_i     (data_rdata),
        .data_rdata_intg_i('0),
        .data_err_i       (data_err),

        // Interrupts / debug (tied off for Week 1)
        .irq_software_i   (1'b0),
        .irq_timer_i      (1'b0),
        .irq_external_i   (1'b0),
        .irq_fast_i       (15'b0),
        .irq_nm_i         (1'b0),
        .debug_req_i      (1'b0),
        .crash_dump_o     (),
        .double_fault_seen_o(),

        // RVFI
        .rvfi_valid       (rvfi_valid),
        .rvfi_order       (rvfi_order),
        .rvfi_insn        (rvfi_insn),
        .rvfi_trap        (rvfi_trap),
        .rvfi_halt        (rvfi_halt),
        .rvfi_intr        (rvfi_intr),
        .rvfi_mode        (rvfi_mode),
        .rvfi_ixl         (rvfi_ixl),
        .rvfi_rs1_addr    (rvfi_rs1_addr),
        .rvfi_rs2_addr    (rvfi_rs2_addr),
        .rvfi_rs1_rdata   (rvfi_rs1_rdata),
        .rvfi_rs2_rdata   (rvfi_rs2_rdata),
        .rvfi_rd_addr     (rvfi_rd_addr),
        .rvfi_rd_wdata    (rvfi_rd_wdata),
        .rvfi_pc_rdata    (rvfi_pc_rdata),
        .rvfi_pc_wdata    (rvfi_pc_wdata),
        .rvfi_mem_addr    (rvfi_mem_addr),
        .rvfi_mem_rmask   (rvfi_mem_rmask),
        .rvfi_mem_wmask   (rvfi_mem_wmask),
        .rvfi_mem_rdata   (rvfi_mem_rdata),
        .rvfi_mem_wdata   (rvfi_mem_wdata),

        // Misc
        .fetch_enable_i   (ibex_pkg::IbexMuBiOn),
        .alert_minor_o    (),
        .alert_major_internal_o(),
        .alert_major_bus_o(),
        .core_sleep_o     ()
    );

    // ── Instruction memory model ──────────────────────────────
    // Single-cycle response (gnt same cycle as req, rvalid next cycle)
    assign instr_gnt   = instr_req;
    assign instr_err   = 1'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            instr_rvalid <= 1'b0;
            instr_rdata  <= '0;
        end else begin
            instr_rvalid <= instr_req;
            instr_rdata  <= instr_req ? imem[instr_addr[9:2]] : '0;
        end
    end

    // ── Data memory model ─────────────────────────────────────
    assign data_gnt  = data_req;
    assign data_err  = 1'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_rvalid <= 1'b0;
            data_rdata  <= '0;
        end else begin
            data_rvalid <= data_req;
            if (data_req && data_we) begin
                // Byte-enable write
                if (data_be[0]) dmem[data_addr[9:2]][7:0]   <= data_wdata[7:0];
                if (data_be[1]) dmem[data_addr[9:2]][15:8]  <= data_wdata[15:8];
                if (data_be[2]) dmem[data_addr[9:2]][23:16] <= data_wdata[23:16];
                if (data_be[3]) dmem[data_addr[9:2]][31:24] <= data_wdata[31:24];
            end
            data_rdata <= data_req ? dmem[data_addr[9:2]] : '0;
        end
    end

    // ── RVFI interface (connects monitor to DUT signals) ──────
    rvfi_if rvfi_bus (.clk(clk), .rst_n(rst_n));

    assign rvfi_bus.rvfi_valid      = rvfi_valid;
    assign rvfi_bus.rvfi_insn       = rvfi_insn;
    assign rvfi_bus.rvfi_rs1_rdata  = rvfi_rs1_rdata;
    assign rvfi_bus.rvfi_rs2_rdata  = rvfi_rs2_rdata;
    assign rvfi_bus.rvfi_rd_addr    = rvfi_rd_addr;
    assign rvfi_bus.rvfi_rd_wdata   = rvfi_rd_wdata;
    assign rvfi_bus.rvfi_pc_rdata   = rvfi_pc_rdata;
    assign rvfi_bus.rvfi_pc_wdata   = rvfi_pc_wdata;
    assign rvfi_bus.rvfi_mem_addr   = rvfi_mem_addr;
    assign rvfi_bus.rvfi_mem_rmask  = rvfi_mem_rmask;
    assign rvfi_bus.rvfi_mem_wmask  = rvfi_mem_wmask;
    assign rvfi_bus.rvfi_mem_rdata  = rvfi_mem_rdata;
    assign rvfi_bus.rvfi_mem_wdata  = rvfi_mem_wdata;

    // ── Control interface (driver uses this for rst_n) ────────
    ibex_ctrl_if ctrl_bus (.clk(clk));
    assign rst_n = ctrl_bus.rst_n;

    // ── Memory backdoor interface (driver writes IMEM here) ───
    ibex_mem_if mem_bus ();
    assign mem_bus.imem = imem;   // shared reference — driver writes, DUT reads

    // ── UVM config_db setup ───────────────────────────────────
    initial begin
        uvm_config_db #(virtual rvfi_if)::set(
            null, "uvm_test_top.*", "rvfi_vif", rvfi_bus);
        uvm_config_db #(virtual ibex_ctrl_if)::set(
            null, "uvm_test_top.*", "ctrl_vif", ctrl_bus);
        uvm_config_db #(virtual ibex_mem_if)::set(
            null, "uvm_test_top.*", "mem_vif",  mem_bus);
        run_test();
    end

    // ── Waveform dump ─────────────────────────────────────────
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb_top);
    end

    // ── Timeout watchdog ─────────────────────────────────────
    initial begin
        #500_000;
        `uvm_fatal("TB_TOP", "Simulation timeout — test hung")
    end

endmodule


// ── Interface definitions ─────────────────────────────────────

interface rvfi_if (input logic clk, input logic rst_n);
    logic        rvfi_valid;
    logic [31:0] rvfi_insn;
    logic [31:0] rvfi_rs1_rdata;
    logic [31:0] rvfi_rs2_rdata;
    logic [4:0]  rvfi_rd_addr;
    logic [31:0] rvfi_rd_wdata;
    logic [31:0] rvfi_pc_rdata;
    logic [31:0] rvfi_pc_wdata;
    logic [31:0] rvfi_mem_addr;
    logic [3:0]  rvfi_mem_rmask;
    logic [3:0]  rvfi_mem_wmask;
    logic [31:0] rvfi_mem_rdata;
    logic [31:0] rvfi_mem_wdata;
endinterface

interface ibex_ctrl_if (input logic clk);
    logic rst_n;
endinterface

interface ibex_mem_if ();
    logic [31:0] imem [0:255];
endinterface
