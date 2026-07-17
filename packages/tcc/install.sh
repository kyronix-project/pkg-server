#!/bin/sh

install_dir="$4"
tcc_lib="/usr/lib/tcc"
lib64="/usr/lib64"

mkdir -p "$install_dir"
cp "$1/payload/tcc" "$install_dir/tcc"
chmod 775 "$install_dir/tcc"

rm -rf "$tcc_lib"
mkdir -p "$tcc_lib"
cat "$1/payload/tcc-lib/libtcc1.a" > "$tcc_lib/libtcc1.a"

mkdir -p "$lib64"
cat "$1/payload/tcc-lib/crt1.o" > "$lib64/crt1.o"
cat "$1/payload/tcc-lib/crti.o" > "$lib64/crti.o"
cat "$1/payload/tcc-lib/crtn.o" > "$lib64/crtn.o"
cat "$1/payload/tcc-lib/Scrt1.o" > "$lib64/Scrt1.o"
cat "$1/payload/tcc-lib/libc.a" > "$lib64/libc.a"
