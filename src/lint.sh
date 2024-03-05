#!/bin/bash

verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-MULTITOP project.v tinyQV/cpu/*.v tinyQV/peri/*/*.v
