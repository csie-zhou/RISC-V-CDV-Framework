// riscv_monitor.sv
// Samples the RVFI retirement bus on every valid commit.
// Packages observed data into riscv_trans_t and writes to analysis port.

`ifndef RISCV_MONITOR_SV
`define RISCV_MONITOR_SV

class riscv_monitor extends uvm_monitor;
    `uvm_component_utils(riscv_monitor)

    virtual rvfi_if vif;
    uvm_analysis_port #(riscv_trans_t) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
        if (!uvm_config_db #(virtual rvfi_if)::get(this, "", "rvfi_vif", vif))
            `uvm_fatal("MON", "No RVFI virtual interface")
    endfunction

    task run_phase(uvm_phase phase);
        riscv_trans_t trans;
        @(posedge vif.clk);
        wait (vif.rst_n === 1'b1);

        forever begin
            @(posedge vif.clk);
            // RVFI: rvfi_valid pulses for exactly one cycle per committed instruction
            if (vif.rvfi_valid) begin
                trans.instr        = vif.rvfi_insn;
                trans.rd           = vif.rvfi_rd_addr;
                trans.rd_wdata     = vif.rvfi_rd_wdata;
                trans.pc_rdata     = vif.rvfi_pc_rdata;   // PC of this instr
                trans.pc_wdata     = vif.rvfi_pc_wdata;   // next PC
                trans.rs1_rdata    = vif.rvfi_rs1_rdata;
                trans.rs2_rdata    = vif.rvfi_rs2_rdata;
                trans.mem_addr     = vif.rvfi_mem_addr;
                trans.mem_rmask    = vif.rvfi_mem_rmask;
                trans.mem_wmask    = vif.rvfi_mem_wmask;
                trans.mem_rdata    = vif.rvfi_mem_rdata;
                trans.mem_wdata    = vif.rvfi_mem_wdata;
                trans.cycle        = $time;

                `uvm_info("MON", $sformatf(
                    "Committed: PC=0x%08h instr=0x%08h rd=x%0d wdata=0x%08h next_pc=0x%08h",
                    trans.pc_rdata, trans.instr, trans.rd,
                    trans.rd_wdata, trans.pc_wdata), UVM_HIGH)

                ap.write(trans);
            end
        end
    endtask
endclass

`endif
