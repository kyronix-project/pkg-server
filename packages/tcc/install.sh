#!/bin/sh

install_dir="$4"
mkdir -p "$install_dir"
cp "$1/payload/tcc" "$install_dir/tcc"
chmod 775 "$install_dir/tcc"

