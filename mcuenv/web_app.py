"""FastAPI web backend for registry management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcuenv.registry_db import (
    RegistryPaths,
    delete_record,
    export_to_toml,
    get_record,
    init_db,
    init_registry,
    list_records,
    save_chip,
    save_manual,
    save_package,
    seed_packages_manuals_from_toml,
    sync_resource_status,
)


def create_app(paths: RegistryPaths):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import FileResponse, HTMLResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise SystemExit(
            "Web server dependencies are missing. Install them with:\n"
            "  python -m pip install -r requirements-web.txt"
        ) from exc

    init_registry(paths)

    class ChipPayload(BaseModel):
        id: str
        family: str
        mcu: str
        series: str = ""
        cpu: str = ""
        probe: str = "stlink"
        backend: str = "openocd"
        jlink_device: str = ""
        openocd_interface: str = "stlink"
        openocd_target: str = ""
        pyocd_target: str = ""
        note: str = ""

    class PackagePayload(BaseModel):
        id: str
        family: str
        title: str = ""
        path: str
        status: str = "missing"
        description: str = ""
        targets: list[str] = Field(default_factory=list)

    class ManualPayload(BaseModel):
        id: str
        family: str
        series: str = ""
        target: str = ""
        title: str = ""
        path: str
        status: str = "missing"
        kind: str = "reference"

    app = FastAPI(title="mcuenv registry", version="0.1.0")
    static_dir = Path(__file__).resolve().parent.parent / "web" / "static"

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        admin_page = static_dir / "admin.html"
        if not admin_page.is_file():
            raise HTTPException(status_code=500, detail="Missing web/static/admin.html")
        return FileResponse(admin_page)

    @app.get("/api/chips")
    def api_list_chips() -> list[dict[str, Any]]:
        return list_records(paths, "chips")

    @app.post("/api/chips")
    def api_create_chip(payload: ChipPayload) -> dict[str, Any]:
        return save_chip(paths, payload.model_dump())

    @app.put("/api/chips/{chip_id}")
    def api_update_chip(chip_id: str, payload: ChipPayload) -> dict[str, Any]:
        if chip_id != payload.id:
            raise HTTPException(status_code=400, detail="Chip id mismatch")
        return save_chip(paths, payload.model_dump())

    @app.delete("/api/chips/{chip_id}")
    def api_delete_chip(chip_id: str) -> dict[str, str]:
        if not delete_record(paths, "chips", chip_id):
            raise HTTPException(status_code=404, detail="Chip not found")
        return {"status": "deleted"}

    @app.get("/api/packages")
    def api_list_packages() -> list[dict[str, Any]]:
        return list_records(paths, "packages")

    @app.post("/api/packages")
    def api_create_package(payload: PackagePayload) -> dict[str, Any]:
        return save_package(paths, payload.model_dump())

    @app.put("/api/packages/{package_id}")
    def api_update_package(package_id: str, payload: PackagePayload) -> dict[str, Any]:
        if package_id != payload.id:
            raise HTTPException(status_code=400, detail="Package id mismatch")
        return save_package(paths, payload.model_dump())

    @app.delete("/api/packages/{package_id}")
    def api_delete_package(package_id: str) -> dict[str, str]:
        if not delete_record(paths, "packages", package_id):
            raise HTTPException(status_code=404, detail="Package not found")
        return {"status": "deleted"}

    @app.get("/api/manuals")
    def api_list_manuals() -> list[dict[str, Any]]:
        return list_records(paths, "manuals")

    @app.post("/api/manuals")
    def api_create_manual(payload: ManualPayload) -> dict[str, Any]:
        return save_manual(paths, payload.model_dump())

    @app.put("/api/manuals/{manual_id}")
    def api_update_manual(manual_id: str, payload: ManualPayload) -> dict[str, Any]:
        if manual_id != payload.id:
            raise HTTPException(status_code=400, detail="Manual id mismatch")
        return save_manual(paths, payload.model_dump())

    @app.delete("/api/manuals/{manual_id}")
    def api_delete_manual(manual_id: str) -> dict[str, str]:
        if not delete_record(paths, "manuals", manual_id):
            raise HTTPException(status_code=404, detail="Manual not found")
        return {"status": "deleted"}

    @app.post("/api/registry/sync-status")
    def api_sync_status() -> dict[str, Any]:
        counts = sync_resource_status(paths)
        return {"status": "ok", "updated": counts}

    @app.post("/api/registry/export-toml")
    def api_export_toml() -> dict[str, str]:
        export_to_toml(paths)
        return {"status": "ok", "registry_dir": str(paths.registry_dir)}

    @app.post("/api/registry/import-toml")
    def api_import_toml() -> dict[str, str]:
        seed_packages_manuals_from_toml(paths, force=True)
        return {"status": "ok"}

    @app.get("/api/registry/summary")
    def api_summary() -> dict[str, Any]:
        return {
            "database": str(paths.database),
            "registry_dir": str(paths.registry_dir),
            "packages_dir": str(paths.packages_dir),
            "manuals_dir": str(paths.manuals_dir),
            "chips": len(list_records(paths, "chips")),
            "packages": len(list_records(paths, "packages")),
            "manuals": len(list_records(paths, "manuals")),
        }

    return app


def run_web_server(
    paths: RegistryPaths,
    *,
    host: str = "127.0.0.1",
    port: int = 7654,
) -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Web server dependencies are missing. Install them with:\n"
            "  python -m pip install -r requirements-web.txt"
        ) from exc

    init_db(paths)
    app = create_app(paths)
    print(f"mcuenv registry web: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
