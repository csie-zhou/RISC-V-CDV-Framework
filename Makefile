# Makefile — cocotb / Verilator build
# Usage:
#   make          → build libisa.so + run sanity test
#   make test     → run sanity test only (no rebuild)
#   make waves    → open waveform in GTKWave
#   make clean    → remove all build artefacts

SIM        ?= verilator
TOPLEVEL   ?= tb_top
MODULE     ?= tests.test_sanity
TOPLEVEL_LANG ?= verilog

# Ibex RTL files — same list as main branch Makefile
VERILOG_SOURCES += \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_util_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_mubi_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_cipher_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_alert_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_esc_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_count_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_secded_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_sha2_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_ascon_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_trivium_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_subreg_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_ram_1p_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_ram_2p_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_rom_pkg.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_buf.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_clock_gating.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim_generic/rtl/prim_flop.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_count.sv \
    dut/ibex/vendor/lowrisc_ip/ip/prim/rtl/prim_lfsr.sv \
    dut/ibex/rtl/ibex_pkg.sv \
    dut/ibex/rtl/ibex_branch_predict.sv \
    dut/ibex/rtl/ibex_compressed_decoder.sv \
    dut/ibex/rtl/ibex_counter.sv \
    dut/ibex/rtl/ibex_csr.sv \
    dut/ibex/rtl/ibex_dummy_instr.sv \
    dut/ibex/rtl/ibex_icache.sv \
    dut/ibex/rtl/ibex_lockstep.sv \
    dut/ibex/rtl/ibex_multdiv_fast.sv \
    dut/ibex/rtl/ibex_pmp.sv \
    dut/ibex/rtl/ibex_fetch_fifo.sv \
    dut/ibex/rtl/ibex_prefetch_buffer.sv \
    dut/ibex/rtl/ibex_register_file_fpga.sv \
    dut/ibex/rtl/ibex_register_file_latch.sv \
    dut/ibex/rtl/ibex_top.sv \
    dut/ibex/rtl/ibex_core.sv \
    dut/ibex/rtl/ibex_if_stage.sv \
    dut/ibex/rtl/ibex_id_stage.sv \
    dut/ibex/rtl/ibex_ex_block.sv \
    dut/ibex/rtl/ibex_load_store_unit.sv \
    dut/ibex/rtl/ibex_wb_stage.sv \
    dut/ibex/rtl/ibex_alu.sv \
    dut/ibex/rtl/ibex_multdiv_slow.sv \
    dut/ibex/rtl/ibex_decoder.sv \
    dut/ibex/rtl/ibex_controller.sv \
    dut/ibex/rtl/ibex_cs_registers.sv \
    dut/ibex/rtl/ibex_register_file_ff.sv \
    tb_top.sv

# Verilator-specific flags
EXTRA_ARGS += --trace --assert --timing -Wall -Wno-fatal
EXTRA_ARGS += +define+RVFI
EXTRA_ARGS += +define+SIM
EXTRA_ARGS += +incdir+dut/ibex/vendor/lowrisc_ip/ip/prim/rtl
EXTRA_ARGS += +incdir+dut/ibex/vendor/lowrisc_ip/dv/sv/dv_utils

# Build ISA shared library first, then run cocotb
all: libisa sim

libisa:
	cd isa_model && gcc -O2 -shared -fPIC -o libisa.so isa_model.c
	@echo "libisa.so built"

# Pull in cocotb's Makefile rules
include $(shell cocotb-config --makefiles)/Makefile.sim

# ── Convenience targets ───────────────────────────────────────
sanity:
	$(MAKE) MODULE=tests.test_sanity

rand:
	$(MAKE) MODULE=tests.test_rand \
	    PLUSARGS="+num_instrs=1000"

rand-hazard:
	$(MAKE) MODULE=tests.test_rand \
	    PLUSARGS="+num_instrs=500 +hazard_mode=heavy"

rand-branch:
	$(MAKE) MODULE=tests.test_rand \
	    PLUSARGS="+num_instrs=500 +branch_pct=40"

stress:
	$(MAKE) MODULE=tests.test_stress

# Run all three with 10 different seeds
regression:
	@for s in 1 2 3 4 5 6 7 8 9 10; do \
	    echo "=== seed $$s ==="; \
	    $(MAKE) MODULE=tests.test_rand \
	        PLUSARGS="+num_instrs=500 +seed=$$s" || exit 1; \
	done
	@echo "=== All seeds passed ==="

waves:
	gtkwave dump.vcd &

clean::
	rm -rf sim_build __pycache__ results.xml dump.vcd
	rm -f isa_model/libisa.so

.PHONY: all libisa sanity rand rand-hazard rand-branch stress regression waves clean
