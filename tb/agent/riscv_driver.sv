// riscv_driver.sv
// Backdoor-writes the directed program into Ibex IMEM, then deasserts reset.
// Week 1: drives a fixed program loaded via config_db from the test.
// Week 2+: will be extended to drive constrained-random instruction streams.

`ifndef RISCV_DRIVER_SV
`define RISCV_DRIVER_SV

class riscv_driver extends uvm_driver #(uvm_sequence_item);
    `uvm_component_utils(riscv_driver)

    virtual ibex_mem_if mem_vif;   // backdoor access to IMEM
    virtual ibex_ctrl_if ctrl_vif; // reset + clock control

    // Program image — loaded from test via config_db before run_phase
    logic [31:0] imem [0:255];
    int          imem_size;

    function new(string name, uvm_component parent);
        super.new(name, parent);
        imem_size = 0;
        foreach (imem[i]) imem[i] = 32'h0000_0013; // fill with NOP
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);

        if (!uvm_config_db #(virtual ibex_mem_if)::get(
                this, "", "mem_vif", mem_vif))
            `uvm_fatal("DRV", "No mem_vif in config_db")

        if (!uvm_config_db #(virtual ibex_ctrl_if)::get(
                this, "", "ctrl_vif", ctrl_vif))
            `uvm_fatal("DRV", "No ctrl_vif in config_db")

        // Pull program words from config_db (set by the test)
        begin
            logic [31:0] word;
            for (int i = 0; i < 256; i++) begin
                if (uvm_config_db #(logic[31:0])::get(
                        this, "", $sformatf("imem[%0d]", i), word)) begin
                    imem[i]  = word;
                    imem_size = i + 1;
                end
            end
        end

        `uvm_info("DRV", $sformatf("Loaded %0d instructions into IMEM", imem_size), UVM_MEDIUM)
    endfunction

    task run_phase(uvm_phase phase);
        // 1. Assert reset
        ctrl_vif.rst_n = 1'b0;
        repeat (5) @(posedge ctrl_vif.clk);

        // 2. Backdoor-write program into IMEM
        //    Ibex fetches from instruction memory on every cycle;
        //    we write directly to the sim memory model before releasing reset.
        for (int i = 0; i < 256; i++) begin
            mem_vif.imem[i] = imem[i];
        end
        `uvm_info("DRV", "IMEM loaded, releasing reset", UVM_MEDIUM)

        // 3. Release reset — pipeline starts fetching
        @(posedge ctrl_vif.clk);
        ctrl_vif.rst_n = 1'b1;

        // 4. Driver is passive from here.
        //    The monitor watches RVFI; scoreboard does all checking.
        //    We just hold until the test drops its objection.
        wait (phase.get_objection_count(this) == 0);
    endtask

endclass

`endif
