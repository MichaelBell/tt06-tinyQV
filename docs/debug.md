# How to debug

In order to help debug the internals of TinyQV, various signals can be exposed on out7.  in3-in6 are used to select the signal that it output.

If in4 is held high on reset, then this debug on out7 is enabled, otherwise out7 defaults to a general purpose output.  The debug mode can be selected by clearing the GP out sel bit in the register at 0x800_000C

| in3-in6 | Signal |
| ------- | ------ |
| 0000 | Instruction complete |
| 0001 | Instruction ready |
| 0010 | Instruction valid |
| 0011 | Instruction fetch restart |
| 0100 | Read req |
| 0101 | Write req |
| 0110 | Data ready |
| 0111 | Interrupt pending |
| 1000 | Branch |
| 1001 | Early branch |
| 1010 | Ret |
| 1101 | Register write enable |
| 1100 | Counter == 0 |
| 1101 | Data continue |
| 1110 | Stall txn |
| 1111 | Stop txn |

## Register value debug

When in3 is held high on leaving reset, SPI is disconnected, and instead out5 to out2 reflect the value being written to the register file.  Note this output is registered, unlike the signal debug above, so appears one clock later.

This mode can also be enabled or disabled by writing the low bit of 0x800_0030.