from __future__ import annotations

import os
import time
from hashlib import md5
from pathlib import Path
from typing import Any

import anyio
import tomllib
from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

APP_ROOT = Path(__file__).resolve().parent
PACKAGES_DIR = APP_ROOT / "packages"
ALLOWED_ARCH = "x86-64"
PACKAGE_MANAGER_USER_AGENT = "K9PackageManager/2.0"
PACKAGE_ARCHIVE_NAME = "package.gz"
PACKAGE_CHECKSUM_NAME = "package.gz.md5"
PACKAGE_INSTALL_SCRIPT_NAME = "install.sh"
MANIFEST_CACHE_TTL = 300  # seconds

app = FastAPI(title="Package Manager Server", version="0.2.0")

_manifest_cache: dict[str, tuple[float, PackageInfo]] = {}


class PackageInfo(BaseModel):
    name: str
    version: str
    description: str | None = None
    arch: str
    revision: int = 1
    maintainer: str | None = None
    license: str | None = None
    homepage: str | None = None
    depends: list[str] = []
    archive_name: str = PACKAGE_ARCHIVE_NAME
    checksum_name: str = PACKAGE_CHECKSUM_NAME
    install_script_name: str = PACKAGE_INSTALL_SCRIPT_NAME
    checksum_valid: bool


class PackageList(BaseModel):
    packages: list[PackageInfo]


class PackageInstallResult(BaseModel):
    detail: str
    package: PackageInfo

def validate_package_name(name: str) -> None:
    """Reject package names that could escape the packages/ directory."""
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Package name required")
    if name in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package name")
    for forbidden in ("/", "\\", "\x00"):
        if forbidden in name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid package name")


def safe_package_dir(name: str) -> Path:
    """Return the package directory only if it resolves inside PACKAGES_DIR."""
    resolved = (PACKAGES_DIR / name).resolve()
    packages_resolved = PACKAGES_DIR.resolve()
    if not str(resolved).startswith(str(packages_resolved) + os.sep) and resolved != packages_resolved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if not resolved.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return resolved

async def require_package_manager_user_agent(
    user_agent: str | None = Header(default=None, alias="User-Agent"),
) -> None:
    if user_agent != PACKAGE_MANAGER_USER_AGENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden client")

async def _read_text(path: Path) -> str:
    async with await anyio.open_file(path, "r", encoding="utf-8") as f:
        return (await f.read()).strip()


async def _read_bytes(path: Path) -> bytes:
    async with await anyio.open_file(path, "rb") as f:
        return await f.read()


async def _compute_md5(path: Path) -> str:
    def _blocking() -> str:
        digest = md5()
        with path.open("rb") as h:
            for chunk in iter(lambda: h.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return await anyio.to_thread.run_sync(_blocking)

def package_dirs() -> list[Path]:
    if not PACKAGES_DIR.exists():
        return []
    return sorted(p for p in PACKAGES_DIR.iterdir() if p.is_dir())

async def load_manifest(package_dir: Path) -> PackageInfo:
    config_path = package_dir / "config.toml"
    archive_path = package_dir / PACKAGE_ARCHIVE_NAME
    checksum_path = package_dir / PACKAGE_CHECKSUM_NAME
    install_script_path = package_dir / PACKAGE_INSTALL_SCRIPT_NAME

    for label, path in [("config.toml", config_path), ("package.gz", archive_path),
                        ("package.gz.md5", checksum_path), ("install.sh", install_script_path)]:
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{label} missing")

    raw_bytes = await _read_bytes(config_path)
    raw: dict[str, Any] = tomllib.loads(raw_bytes.decode("utf-8"))

    name = str(raw.get("name", "")).strip()
    version = str(raw.get("version", "")).strip()
    description = raw.get("description")
    arch = str(raw.get("arch", "")).strip()
    revision = int(raw.get("revision", 1))
    maintainer = raw.get("maintainer")
    license_val = raw.get("license")
    homepage = raw.get("homepage")
    depends_raw = raw.get("depends", [])
    depends = [str(d).strip() for d in depends_raw if str(d).strip()]

    if not name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Package name missing in {package_dir.name}")
    if name != package_dir.name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Package directory mismatch for {package_dir.name}")
    if not version:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Package version missing in {package_dir.name}")
    if arch != ALLOWED_ARCH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported architecture in {package_dir.name}")
    if description is not None:
        description = str(description)
    if maintainer is not None:
        maintainer = str(maintainer)
    if license_val is not None:
        license_val = str(license_val)
    if homepage is not None:
        homepage = str(homepage)

    recorded_checksum = await _read_text(checksum_path)
    actual_checksum = await _compute_md5(archive_path)

    return PackageInfo(
        name=name,
        version=version,
        description=description,
        arch=arch,
        revision=revision,
        maintainer=maintainer,
        license=license_val,
        homepage=homepage,
        depends=depends,
        checksum_valid=recorded_checksum == actual_checksum,
    )


async def get_cached_manifest(name: str) -> PackageInfo:
    now = time.time()
    if name in _manifest_cache:
        ts, pkg = _manifest_cache[name]
        if now - ts < MANIFEST_CACHE_TTL:
            return pkg
    package_dir = PACKAGES_DIR / name
    if not package_dir.exists() or not package_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    pkg = await load_manifest(package_dir)
    _manifest_cache[name] = (now, pkg)
    return pkg

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/packages", response_model=PackageList)
async def list_packages() -> PackageList:
    manifests: list[PackageInfo] = []
    for package_dir in package_dirs():
        try:
            manifests.append(await get_cached_manifest(package_dir.name))
        except HTTPException:
            continue
    return PackageList(packages=manifests)


@app.get("/packages/{name}", response_model=PackageInfo)
async def get_package(name: str) -> PackageInfo:
    validate_package_name(name)
    return await get_cached_manifest(name)


@app.get("/packages/{name}/archive")
async def download_package_archive(
    name: str, _: None = Depends(require_package_manager_user_agent)
) -> FileResponse:
    validate_package_name(name)
    pkg_dir = safe_package_dir(name)
    await get_cached_manifest(name)
    return FileResponse(pkg_dir / PACKAGE_ARCHIVE_NAME, filename=PACKAGE_ARCHIVE_NAME, media_type="application/gzip")


@app.get("/packages/{name}/install.sh")
async def download_install_script(
    name: str, _: None = Depends(require_package_manager_user_agent)
) -> FileResponse:
    validate_package_name(name)
    pkg_dir = safe_package_dir(name)
    await get_cached_manifest(name)
    return FileResponse(pkg_dir / PACKAGE_INSTALL_SCRIPT_NAME, filename=PACKAGE_INSTALL_SCRIPT_NAME, media_type="text/x-sh")


@app.get("/packages/{name}/checksum")
async def get_package_checksum(
    name: str, _: None = Depends(require_package_manager_user_agent)
) -> dict[str, str]:
    validate_package_name(name)
    pkg_dir = safe_package_dir(name)
    await get_cached_manifest(name)
    checksum = await _read_text(pkg_dir / PACKAGE_CHECKSUM_NAME)
    return {"checksum": checksum}

@app.exception_handler(HTTPException)
async def http_exception_handler(_: Any, exc: HTTPException) -> Response:
    detail = exc.detail if isinstance(exc.detail, str) else "error"
    return Response(content=detail, status_code=exc.status_code, media_type="text/plain")
