![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# TinyQV - A Risc-V SoC for Tiny Tapeout

- [TinyQV Programmer](https://tinyqv.rebel-lion.uk/), for using TinyQV on TT06
- [Documentation for project](docs/info.md)
- [More details about tinyQV](https://github.com/MichaelBell/tinyQV)
- [tinyQV-sdk for building tinyQV programs](https://github.com/MichaelBell/tinyQV-sdk)
- [Example tinyQV programs](https://github.com/MichaelBell/tinyQV-projects)

## How To Build a Program for TinyQV

In summary:

1. Download this [build of gcc for TinyQV](https://github.com/MichaelBell/riscv-gnu-toolchain/releases/tag/13.2.0-tqv-1.0) and extract it to `/opt/tinyQV`
2. Clone the [tinyQV-sdk](https://github.com/MichaelBell/tinyQV-sdk) and build it
3. Clone the [example projects repo](https://github.com/MichaelBell/tinyQV-projects) and build `donut.bin`
4. Use the [TinyQV Programmer](https://tinyqv.rebel-lion.uk/) to flash and run `donut.bin`

On a Linux system with developer tools installed, that should go something like this:

    sudo mkdir /opt/tinyQV
    sudo chown `whoami` /opt/tinyQV
    pushd /opt/tinyQV
    wget https://github.com/MichaelBell/riscv-gnu-toolchain/releases/download/13.2.0-tqv-1.0/riscv32ec-13.2.0-tqv-1.0.tar.gz
    tar xf riscv32ec-13.2.0-tqv-1.0.tar.gz
    popd

    git clone https://github.com/MichaelBell/tinyQV-sdk
    cd tinyQV-sdk
    make
    cd ..

    git clone https://github.com/MichaelBell/tinyQV-projects
    cd tinyQV-projects/donut
    make

If that all went well you should now have a `donut.bin` built.  Try running that in the [TinyQV Programmer](https://tinyqv.rebel-lion.uk/) using the Custom option.

## What is Tiny Tapeout?

TinyTapeout is an educational project that aims to make it easier and cheaper than ever to get your digital designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Verilog Projects

1. Add your Verilog files to the `src` folder.
2. Edit the [info.yaml](info.yaml) and update information about your project, paying special attention to the `source_files` and `top_module` properties. If you are upgrading an existing Tiny Tapeout project, check out our [online info.yaml migration tool](https://tinytapeout.github.io/tt-yaml-upgrade-tool/).
3. Edit [docs/info.md](docs/info.md) and add a description of your project.
4. Optionally, add a testbench to the `test` folder. See [test/README.md](test/README.md) for more information.

The GitHub action will automatically build the ASIC files using [OpenLane](https://www.zerotoasiccourse.com/terminology/openlane/).

## Enable GitHub actions to build the results page

- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)
- [Build your design locally](https://docs.google.com/document/d/1aUUZ1jthRpg4QURIIyzlOaPWlmQzr-jBn3wZipVUPt4)

## What next?

- [Submit your design to the next shuttle](https://app.tinytapeout.com/).
- Edit [this README](README.md) and explain your design, how it works, and how to test it.
- Share your project on your social network of choice:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [@TinyTapeout](https://www.linkedin.com/company/100708654/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - X (formerly Twitter) [#tinytapeout](https://twitter.com/hashtag/tinytapeout) [@matthewvenn](https://twitter.com/matthewvenn)
