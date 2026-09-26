#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    build-essential clang llvm lld libclang-dev \
    bison flex gawk gettext git gperf help2man \
    autoconf automake autopoint libtool cmake ninja-build \
    libncurses-dev libssl-dev libelf-dev libfuse-dev libglib2.0-dev \
    libgmp-dev libmpc-dev libmpfr-dev libreadline-dev zlib1g-dev \
    python3 python3-setuptools python3-pyelftools python3-dev \
    python3-yaml python3-packaging python3-ply \
    asciidoc antlr3 device-tree-compiler ecj fastjar \
    unzip zip zstd xz-utils bzip2 cpio rsync curl wget jq \
    bc file patch quilt subversion swig texinfo time xsltproc \
    libgnutls28-dev libyaml-dev liblzma-dev libltdl-dev \
    pkgconf ccache dos2unix xxd dwarves
