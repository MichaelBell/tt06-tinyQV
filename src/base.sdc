read_sdc $::env(OPENLANE_ROOT)/scripts/base.sdc

# Add duty cycle uncertainty - due to the high capacitance of the TT mux 
# we're pretty uncertain about the duty cycle
set_clock_uncertainty 2.5 -rise_from clk -fall_to clk
set_clock_uncertainty 2.5 -fall_from clk -rise_to clk

# Fix reset delay
set_input_delay 1.5 -clock [get_clocks $::env(CLOCK_PORT)] {rst_n}
