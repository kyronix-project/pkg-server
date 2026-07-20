#!/bin/sh

install_dir="$4"
lib64="/usr/lib64"

mkdir -p "$install_dir"
cp "$1/payload/libc.a" "$install_dir/libc.a"
cp "$1/payload/crt1.o" "$install_dir/crt1.o"
cp "$1/payload/crti.o" "$install_dir/crti.o"
cp "$1/payload/crtn.o" "$install_dir/crtn.o"
cp "$1/payload/Scrt1.o" "$install_dir/Scrt1.o"

mkdir -p "$lib64"
cp "$1/payload/libc.a" "$lib64/libc.a"
cp "$1/payload/crt1.o" "$lib64/crt1.o"
cp "$1/payload/crti.o" "$lib64/crti.o"
cp "$1/payload/crtn.o" "$lib64/crtn.o"
cp "$1/payload/Scrt1.o" "$lib64/Scrt1.o"
