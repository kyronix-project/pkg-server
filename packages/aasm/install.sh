#!/bin/sh

install_dir="$4"

mkdir -p "$install_dir"
cp "$1/payload/aasm" "$install_dir/aasm"
chmod 775 "$install_dir/aasm"