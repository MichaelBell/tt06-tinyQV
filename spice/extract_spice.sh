#! /bin/bash
rm -rf extfiles

magic -dnull -noconsole -rcfile $PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc << EOF
gds read tt_um_MichaelBell_tinyQV.gds
load tt_um_MichaelBell_tinyQV
readspice tt_um_MichaelBell_tinyQV_ports.spice
extract path extfiles
extract all
ext2spice lvs
ext2spice -p extfiles
EOF
