# Package Manager Kyronix - Operation Manual

## System Architecture

The package management system comprises two distinct components:

- Server component (server/) - FastAPI-based HTTP daemon responsible for package distribution
- Client component (client/) - Statically compiled C binary named 'pkg'

Packages are stored as directories within server/packages/<package_name>/, each containing exactly four mandatory files.

## Package Structure

Each package directory must contain the following files:

```
server/packages/<package_name>/
  config.toml        # Manifesto
  package.gz         # tar.gz archive containing package payload
  package.gz.md5     # MD5 hash of the archive
  install.sh         # Installation script
```

## Config.toml Manifest
```
Required fields:
  name      = "<package_name>"
  version   = "<semantic_version>"
  revision  = <integer>           # Incremented on each package change
  arch      = "x86-64"            # Fixed value

Optional fields:
  description = "<string>"
  maintainer  = "<string>"
  license     = "<string>"
  homepage    = "<url>"
  depends     = ["pkg1", "pkg2"]  # Array of dependency package names
                                   # Client resolves and installs them recursively
                                   # before the target package, in dependency order
```
## Install.sh Script

The installation script receives four positional arguments:
```
  $1 - Extract directory (where the archive was unpacked)
  $2 - Path to downloaded archive file
  $3 - Path to checksum file
  $4 - Installation target directory (~/.local/share/pkg/packages/<name>)
```

The script executes under /bin/sh. All operations must be compatible with this environment.


Script example:
```sh
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
```

# Package Creation Procedure

## Initialize Package Directory

mkdir -p server/packages/<package_name>

## Create Config.toml

```
cat > server/packages/<package_name>/config.toml << 'EOF'
name = "<package_name>"
version = "1.0.0"
revision = 1
description = "<description>"
arch = "x86-64"
maintainer = "<maintainer_name>"
license = "<license>"
homepage = "<url>"
depends = []
EOF
```

## Prepare Payload Content

Create a staging directory with the files to be included in the package:

```
mkdir -p /tmp/<package_name>-build
# Place files into /tmp/<package_name>-build/
# Example:
echo "content" > /tmp/<package_name>-build/payload/file.txt
```

## Create Archive
```
cd /tmp/<package_name>-build
tar -czf /path/to/server/packages/<package_name>/package.gz .
cd -
```
Important: The archive must contain relative paths only. Do not use absolute paths.

## Generate Checksum
```
md5sum /path/to/server/packages/<package_name>/package.gz | awk '{print $1}' \
  > /path/to/server/packages/<package_name>/package.gz.md5
```

## Write Installation Script
```
cat > server/packages/<package_name>/install.sh << 'SCRIPT'
#!/bin/sh
install_dir="$4"
mkdir -p "$install_dir"
cp "$1/payload/file.txt" "$install_dir/file.txt"
echo "[<package_name>] installed"
SCRIPT

chmod +x server/packages/<package_name>/install.sh
```

## Verification

Verify all four required files are present:
```
ls server/packages/<package_name>/
# Should output: config.toml  install.sh  package.gz  package.gz.md5
```
