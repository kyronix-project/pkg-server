#!/bin/sh

install_dir="$4"
tcc_lib="/usr/lib/tcc"

mkdir -p "$install_dir"
cp "$1/payload/tcc" "$install_dir/tcc"
chmod 775 "$install_dir/tcc"

rm -rf "$tcc_lib"
mkdir -p "$tcc_lib"
cat "$1/payload/tcc-lib/libtcc1.a" > "$tcc_lib/libtcc1.a"
