`ifndef RISCV_SANITY_TEST_SV
`define RISCV_SANITY_TEST_SV

class riscv_sanity_test extends uvm_test;
    `uvm_component_utils(riscv_sanity_test)

    riscv_env env;

    // 20-instruction directed program loaded into Ibex IMEM
    // Encoding: hand-assembled RV32I
    // Expected final state documented below each instruction
    localparam logic [31:0] PROGRAM [0:19] = '{
        // ADDI x1, x0, 10       → x1 = 10
        32'h00A00093,
        // ADDI x2, x0, 20       → x2 = 20
        32'h01400113,
        // ADD  x3, x1, x2       → x3 = 30
        32'h002081B3,
        // SUB  x4, x2, x1       → x4 = 10
        32'h40110233,
        // AND  x5, x1, x2       → x5 = 0  (10 & 20 = 0b01010 & 0b10100 = 0)
        32'h0020F2B3,
        // OR   x6, x1, x2       → x6 = 30 (0b01010 | 0b10100 = 0b11110)
        32'h0020E333,
        // XOR  x7, x3, x4       → x7 = 20 (30 ^ 10)
        32'h004183B3,
        // ADDI x8, x0, -1       → x8 = 0xFFFFFFFF (sign extension check)
        32'hFFF00413,
        // SRLI x9, x8, 1        → x9 = 0x7FFFFFFF (logical right shift)
        32'h0014D493,
        // SRAI x10, x8, 1       → x10 = 0xFFFFFFFF (arithmetic right shift, keeps sign)
        32'h4014D513,
        // SLL  x11, x1, x2      → x11 = 10 << 20 (shift by rs2[4:0]=20)
        32'h002095B3,
        // SLTI x12, x4, 20      → x12 = 1 (10 < 20)
        32'h01422613,
        // SLTIU x13, x4, 5      → x13 = 0 (10 >= 5 unsigned)
        32'h005236B3,
        // LUI  x14, 0xABCDE     → x14 = 0xABCDE000
        32'hABCDE737,
        // SW   x1, 0(x0)        → mem[0] = 10
        32'h00102023,
        // SW   x2, 4(x0)        → mem[1] = 20
        32'h00202223,
        // LW   x15, 0(x0)       → x15 = 10 (load back)
        32'h00002783,
        // LW   x16, 4(x0)       → x16 = 20
        32'h00402803,
        // BEQ  x15, x1, +8      → branch taken (10 == 10), skip next
        32'h00178463,
        // ADDI x17, x0, 99      → should be SKIPPED (branch taken)
        32'h06300893
        // After BEQ: PC jumps over ADDI x17, so x17 must remain 0
    };

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env = riscv_env::type_id::create("env", this);
    endfunction

    task run_phase(uvm_phase phase);
        phase.raise_objection(this);

        // Load program into Ibex instruction memory via backdoor
        for (int i = 0; i < 20; i++) begin
            uvm_config_db #(logic[31:0])::set(this, "env.agent.driver",
                $sformatf("imem[%0d]", i), PROGRAM[i]);
        end

        // Run for enough cycles for all instructions to retire
        // 20 instructions × (worst case 5 cycles each) + 20 flush cycles
        #(20 * 5 * 10 + 200);

        phase.drop_objection(this);
    endtask

    function void report_phase(uvm_phase phase);
        `uvm_info("TEST", "=== SANITY TEST COMPLETE ===", UVM_NONE)
        `uvm_info("TEST",
            "Expected final state:\n" +
            "  x1=10  x2=20  x3=30  x4=10  x5=0   x6=30\n" +
            "  x7=20  x8=0xFFFFFFFF  x9=0x7FFFFFFF  x10=0xFFFFFFFF\n" +
            "  x14=0xABCDE000  x15=10  x16=20  x17=0 (branch skipped)",
            UVM_NONE)
    endfunction

endclass

`endif
