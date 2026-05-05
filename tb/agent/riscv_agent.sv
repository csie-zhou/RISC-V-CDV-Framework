`ifndef RISCV_AGENT_SV
`define RISCV_AGENT_SV

class riscv_agent extends uvm_agent;
    `uvm_component_utils(riscv_agent)

    riscv_monitor                   monitor;
    uvm_sequencer #(uvm_sequence_item) sequencer;
    riscv_driver                    driver;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        monitor   = riscv_monitor::type_id::create("monitor", this);
        sequencer = uvm_sequencer #(uvm_sequence_item)::type_id::create("sequencer", this);
        driver    = riscv_driver::type_id::create("driver", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        driver.seq_item_port.connect(sequencer.seq_item_export);
    endfunction
endclass

`endif
