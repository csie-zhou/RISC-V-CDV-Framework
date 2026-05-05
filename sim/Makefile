# sim/Makefile
# Tool: VCS — adjust flags for Xcelium or Questa

TEST     ?= riscv_sanity_test
SEED     ?= 1
VERBOSITY ?= UVM_MEDIUM

VCS := vcs

# Ibex source files (subset needed for simulation)
IBEX_RTL := \
    ../dut/ibex/rtl/ibex_top.sv \
    ../dut/ibex/rtl/ibex_core.sv \
    ../dut/ibex/rtl/ibex_if_stage.sv \
    ../dut/ibex/rtl/ibex_id_stage.sv \
    ../dut/ibex/rtl/ibex_ex_block.sv \
    ../dut/ibex/rtl/ibex_load_store_unit.sv \
    ../dut/ibex/rtl/ibex_wb_stage.sv \
    ../dut/ibex/rtl/ibex_alu.sv \
    ../dut/ibex/rtl/ibex_multdiv_slow.sv \
    ../dut/ibex/rtl/ibex_decoder.sv \
    ../dut/ibex/rtl/ibex_controller.sv \
    ../dut/ibex/rtl/ibex_cs_registers.sv \
    ../dut/ibex/rtl/ibex_register_file_ff.sv

TB_SV := \
    ../tb/pkg/riscv_types_pkg.sv \
    ../tb/agent/riscv_monitor.sv \
    ../tb/agent/riscv_driver.sv \
    ../tb/agent/riscv_agent.sv \
    ../tb/scoreboard/riscv_scoreboard.sv \
    ../tb/env/riscv_env.sv \
    ../tb/tests/riscv_sanity_test.sv \
    ../tb_top.sv

# DPI-C source
DPI_C := ../isa_model/isa_model.c ../isa_model/dpi_bridge.c

VCS_FLAGS := \
    -full64 -sverilog -timescale=1ns/1ps \
    -ntb_opts uvm-1.2 \
    +define+RVFI \
    +define+SIM \
    +incdir+../tb/pkg \
    +incdir+../tb \
    -debug_access+all \
    -CFLAGS "-I../isa_model" \

sim: $(IBEX_RTL) $(TB_SV)
	$(VCS) $(VCS_FLAGS) \
	    $(IBEX_RTL) $(TB_SV) \
	    -dpi $(DPI_C) \
	    -o simv 2>&1 | tee compile.log
	./simv \
	    +UVM_TESTNAME=$(TEST) \
	    +UVM_VERBOSITY=$(VERBOSITY) \
	    +ntb_random_seed=$(SEED) \
	    2>&1 | tee run_$(TEST).log

waves:
	gtkwave dump.vcd &

clean:
	rm -rf simv simv.daidir csrc *.vcd *.log ucli.key AN.DB

.PHONY: sim waves clean
