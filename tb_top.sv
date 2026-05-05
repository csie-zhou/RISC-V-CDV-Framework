// tb_top.sv — cocotb branch
// Identical to main branch EXCEPT:
//   - No `import uvm_pkg::*`
//   - No `initial begin run_test(); end`
//   - No interface config_db setup
//   cocotb drives everything from Python via Verilator DPI.
//
// All other content (Ibex instantiation, IMEM, DMEM, RVFI wiring)
// is IDENTICAL to main branch — see main branch tb_top.sv.

`timescale 1ns/1ps

module tb_top;

    logic clk  = 1'b0;
    logic rst_n;
    always #5 clk = ~clk;

    // IMEM / DMEM (cocotb driver writes these via .value deposit)
    logic [31:0] imem [0:255];
    logic [31:0] dmem [0:255];
    initial begin
        foreach (imem[i]) imem[i] = 32'h0000_0013;
        foreach (dmem[i]) dmem[i] = '0;
    end

    // --- Ibex signals (identical to main branch) ---
    logic        instr_req,  instr_gnt,  instr_rvalid;
    logic [31:0] instr_addr, instr_rdata;
    logic        instr_err;

    logic        data_req,  data_gnt,  data_rvalid, data_we;
    logic [3:0]  data_be;
    logic [31:0] data_addr, data_wdata, data_rdata;
    logic        data_err;

    // RVFI outputs — read directly by cocotb monitor via dut.rvfi_*
    logic        rvfi_valid;
    logic [31:0] rvfi_insn;
    logic [4:0]  rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rd_addr;
    logic [31:0] rvfi_rs1_rdata, rvfi_rs2_rdata, rvfi_rd_wdata;
    logic [31:0] rvfi_pc_rdata, rvfi_pc_wdata;
    logic [31:0] rvfi_mem_addr, rvfi_mem_rdata, rvfi_mem_wdata;
    logic [3:0]  rvfi_mem_rmask, rvfi_mem_wmask;

    // Ibex DUT (identical parameters to main branch)
    ibex_top #(
        .PMPEnable      (1'b0),
        .MHPMCounterNum (0),
        .RV32M          (ibex_pkg::RV32MNone),
        .RV32B          (ibex_pkg::RV32BNone),
        .WritebackStage (1'b1),
        .ICache         (1'b0)
    ) u_ibex (
        .clk_i              (clk),
        .rst_ni             (rst_n),
        .instr_req_o        (instr_req),
        .instr_gnt_i        (instr_gnt),
        .instr_rvalid_i     (instr_rvalid),
        .instr_addr_o       (instr_addr),
        .instr_rdata_i      (instr_rdata),
        .instr_rdata_intg_i ('0),
        .instr_err_i        (instr_err),
        .data_req_o         (data_req),
        .data_gnt_i         (data_gnt),
        .data_rvalid_i      (data_rvalid),
        .data_we_o          (data_we),
        .data_be_o          (data_be),
        .data_addr_o        (data_addr),
        .data_wdata_o       (data_wdata),
        .data_wdata_intg_o  (),
        .data_rdata_i       (data_rdata),
        .data_rdata_intg_i  ('0),
        .data_err_i         (data_err),
        .irq_software_i     (1'b0),
        .irq_timer_i        (1'b0),
        .irq_external_i     (1'b0),
        .irq_fast_i         (15'b0),
        .irq_nm_i           (1'b0),
        .debug_req_i        (1'b0),
        .crash_dump_o       (),
        .double_fault_seen_o(),
        .rvfi_valid         (rvfi_valid),
        .rvfi_order         (),
        .rvfi_insn          (rvfi_insn),
        .rvfi_trap          (),
        .rvfi_halt          (),
        .rvfi_intr          (),
        .rvfi_mode          (),
        .rvfi_ixl           (),
        .rvfi_rs1_addr      (rvfi_rs1_addr),
        .rvfi_rs2_addr      (rvfi_rs2_addr),
        .rvfi_rs1_rdata     (rvfi_rs1_rdata),
        .rvfi_rs2_rdata     (rvfi_rs2_rdata),
        .rvfi_rd_addr       (rvfi_rd_addr),
        .rvfi_rd_wdata      (rvfi_rd_wdata),
        .rvfi_pc_rdata      (rvfi_pc_rdata),
        .rvfi_pc_wdata      (rvfi_pc_wdata),
        .rvfi_mem_addr      (rvfi_mem_addr),
        .rvfi_mem_rmask     (rvfi_mem_rmask),
        .rvfi_mem_wmask     (rvfi_mem_wmask),
        .rvfi_mem_rdata     (rvfi_mem_rdata),
        .rvfi_mem_wdata     (rvfi_mem_wdata),
        .fetch_enable_i     (ibex_pkg::IbexMuBiOn),
        .alert_minor_o      (),
        .alert_major_internal_o(),
        .alert_major_bus_o  (),
        .core_sleep_o       ()
    );

    // Single-cycle instruction memory
    assign instr_gnt = instr_req;
    assign instr_err = 1'b0;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            instr_rvalid <= 1'b0;
            instr_rdata  <= '0;
        end else begin
            instr_rvalid <= instr_req;
            instr_rdata  <= instr_req ? imem[instr_addr[9:2]] : '0;
        end
    end

    // Single-cycle data memory
    assign data_gnt = data_req;
    assign data_err = 1'b0;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            data_rvalid <= 1'b0;
            data_rdata  <= '0;
        end else begin
            data_rvalid <= data_req;
            if (data_req && data_we) begin
                if (data_be[0]) dmem[data_addr[9:2]][7:0]   <= data_wdata[7:0];
                if (data_be[1]) dmem[data_addr[9:2]][15:8]  <= data_wdata[15:8];
                if (data_be[2]) dmem[data_addr[9:2]][23:16] <= data_wdata[23:16];
                if (data_be[3]) dmem[data_addr[9:2]][31:24] <= data_wdata[31:24];
            end
            data_rdata <= data_req ? dmem[data_addr[9:2]] : '0;
        end
    end

    // Timeout watchdog
    initial begin
        #500_000;
        $fatal(1, "Simulation timeout");
    end

endmodule
