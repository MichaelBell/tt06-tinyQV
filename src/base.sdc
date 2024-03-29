read_sdc $::env(OPENLANE_ROOT)/scripts/base.sdc

# Add duty cycle uncertainty - due to the high capacitance of the TT mux 
# we're pretty uncertain about the duty cycle
set_clock_uncertainty 2.5 -rise_from clk -fall_to clk
set_clock_uncertainty 2 -fall_from clk -rise_to clk

# Fix reset delay
set_input_delay 1.5 -clock [get_clocks $::env(CLOCK_PORT)] {rst_n}

# Longer delays for input IOs as we expect to drive them on clock falling edge
set bidi_delay_value [expr $::env(CLOCK_PERIOD) * 0.6]
set_input_delay $bidi_delay_value -clock [get_clocks $::env(CLOCK_PORT)] {uio_in ui_in}

# Longer output delay on bidi IOs to improve coherence
set_output_delay $bidi_delay_value -clock [get_clocks $::env(CLOCK_PORT)] {uio_out uio_oe}

# No delay on output 7 as this is used for deubg signals
set_output_delay 0 -clock [get_clocks $::env(CLOCK_PORT)] {uo_out[7]}