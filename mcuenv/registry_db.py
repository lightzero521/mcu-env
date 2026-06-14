"""SQLite-backed registry for chips, SDK packages, and manuals."""

from __future__ import annotations

import json
import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegistryPaths:
    root: Path
    registry_dir: Path
    packages_dir: Path
    manuals_dir: Path
    database: Path


DEFAULT_CHIPS: tuple[dict[str, str], ...] = (
    {
        "id": "stm32f103c8t6",
        "family": "stm32",
        "mcu": "STM32F103C8T6",
        "series": "f1",
        "cpu": "cortex-m3",
        "probe": "stlink",
        "backend": "openocd",
        "jlink_device": "STM32F103C8",
        "openocd_interface": "stlink",
        "openocd_target": "stm32f1x",
        "pyocd_target": "stm32f103c8",
        "note": "",
    },
    {
        "id": "stm32h750xbh6",
        "family": "stm32",
        "mcu": "STM32H750XBH6",
        "series": "h7",
        "cpu": "cortex-m7",
        "probe": "stlink",
        "backend": "openocd",
        "jlink_device": "STM32H750XB",
        "openocd_interface": "stlink",
        "openocd_target": "stm32h7x",
        "pyocd_target": "stm32h750xb",
        "note": "",
    },
    {
        "id": "gd32f303vet6",
        "family": "gd32",
        "mcu": "GD32F303VET6",
        "series": "f30x",
        "cpu": "cortex-m4",
        "probe": "stlink",
        "backend": "pyocd",
        "jlink_device": "GD32F303VE",
        "openocd_interface": "stlink",
        "openocd_target": "stm32f2x",
        "pyocd_target": "gd32f303ve",
        "note": "GD32F30x can also use OpenOCD stm32f2x mapping",
    },
    {
        "id": "gd32f527zmt7",
        "family": "gd32",
        "mcu": "GD32F527ZMT7",
        "series": "f5",
        "cpu": "cortex-m33",
        "probe": "jlink",
        "backend": "jlink",
        "jlink_device": "GD32F527ZM",
        "openocd_interface": "jlink",
        "openocd_target": "",
        "pyocd_target": "gd32f527zm",
        "note": "Prefer J-Link or pyOCD for GD32F5; OpenOCD target not preset",
    },
)

_CHIPS_SCHEMA = {
    "id",
    "family",
    "mcu",
    "series",
    "cpu",
    "probe",
    "backend",
    "jlink_device",
    "openocd_interface",
    "openocd_target",
    "pyocd_target",
    "note",
}

_CREATE_CHIPS_TABLE = """
CREATE TABLE chips (
    id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    mcu TEXT NOT NULL,
    series TEXT NOT NULL DEFAULT '',
    cpu TEXT NOT NULL DEFAULT '',
    probe TEXT NOT NULL DEFAULT 'stlink',
    backend TEXT NOT NULL DEFAULT 'openocd',
    jlink_device TEXT NOT NULL DEFAULT '',
    openocd_interface TEXT NOT NULL DEFAULT 'stlink',
    openocd_target TEXT NOT NULL DEFAULT '',
    pyocd_target TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
);
"""


def resolve_registry_paths(root: Path, database: Path | None = None) -> RegistryPaths:
    registry_dir = root / "registry"
    db_path = database or (root / "data" / "registry.db")
    if not db_path.is_absolute():
        db_path = root / db_path
    return RegistryPaths(
        root=root,
        registry_dir=registry_dir,
        packages_dir=root / "packages",
        manuals_dir=root / "manuals",
        database=db_path,
    )


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])


def _ensure_chips_schema(connection: sqlite3.Connection) -> None:
    rows = connection.execute("PRAGMA table_info(chips)").fetchall()
    if not rows:
        connection.executescript(_CREATE_CHIPS_TABLE)
        return

    columns = {row["name"] for row in rows}
    if columns != _CHIPS_SCHEMA:
        connection.execute("DROP TABLE chips")
        connection.executescript(_CREATE_CHIPS_TABLE)


def init_db(paths: RegistryPaths) -> None:
    with connect(paths.database) as connection:
        _ensure_chips_schema(connection)
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS packages (
                id TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                title TEXT NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'missing',
                description TEXT NOT NULL DEFAULT '',
                targets_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS manuals (
                id TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                series TEXT NOT NULL DEFAULT '',
                target TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'missing',
                kind TEXT NOT NULL DEFAULT 'reference'
            );
            """
        )


def _insert_chip(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO chips (
            id, family, mcu, series, cpu, probe, backend,
            jlink_device, openocd_interface, openocd_target, pyocd_target, note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["id"],
            payload["family"],
            payload["mcu"],
            payload.get("series", ""),
            payload.get("cpu", ""),
            payload.get("probe", "stlink"),
            payload.get("backend", "openocd"),
            payload.get("jlink_device", ""),
            payload.get("openocd_interface", "stlink"),
            payload.get("openocd_target", ""),
            payload.get("pyocd_target", ""),
            payload.get("note", ""),
        ),
    )


def seed_default_chips(paths: RegistryPaths, *, force: bool = False) -> bool:
    init_db(paths)
    with connect(paths.database) as connection:
        if not force and _table_count(connection, "chips") > 0:
            return False

        if force:
            connection.execute("DELETE FROM chips")

        for chip in DEFAULT_CHIPS:
            _insert_chip(connection, chip)
        connection.commit()
    return True


def seed_packages_manuals_from_toml(
    paths: RegistryPaths,
    *,
    force: bool = False,
) -> bool:
    init_db(paths)
    with connect(paths.database) as connection:
        packages_empty = _table_count(connection, "packages") == 0
        manuals_empty = _table_count(connection, "manuals") == 0
        if not force and not packages_empty and not manuals_empty:
            return False

        if force:
            connection.executescript("DELETE FROM manuals; DELETE FROM packages;")

        _import_packages_toml(connection, paths.registry_dir / "packages.toml")
        _import_manuals_toml(connection, paths.registry_dir / "manuals.toml")
        connection.commit()
    return True


def init_registry(paths: RegistryPaths, *, force: bool = False) -> None:
    seed_default_chips(paths, force=force)
    seed_packages_manuals_from_toml(paths, force=force)


def _import_packages_toml(connection: sqlite3.Connection, path: Path) -> None:
    if not path.is_file():
        return
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    for key, item in data.items():
        if not key.startswith("package."):
            continue
        package_id = item.get("id") or key.removeprefix("package.")
        targets = item.get("targets", [])
        connection.execute(
            """
            INSERT OR REPLACE INTO packages
            (id, family, title, path, status, description, targets_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                package_id,
                item.get("family", ""),
                item.get("title", package_id),
                item.get("path", ""),
                item.get("status", "missing"),
                item.get("description", ""),
                json.dumps(targets),
            ),
        )


def _import_manuals_toml(connection: sqlite3.Connection, path: Path) -> None:
    if not path.is_file():
        return
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    for key, item in data.items():
        if not key.startswith("manual."):
            continue
        manual_id = key.removeprefix("manual.")
        connection.execute(
            """
            INSERT OR REPLACE INTO manuals
            (id, family, series, target, title, path, status, kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manual_id,
                item.get("family", ""),
                item.get("series", ""),
                item.get("target", ""),
                item.get("title", manual_id),
                item.get("path", ""),
                item.get("status", "missing"),
                item.get("kind", "reference"),
            ),
        )


def export_to_toml(paths: RegistryPaths) -> None:
    paths.registry_dir.mkdir(parents=True, exist_ok=True)
    with connect(paths.database) as connection:
        _export_packages_toml(connection, paths.registry_dir / "packages.toml")
        _export_manuals_toml(connection, paths.registry_dir / "manuals.toml")


def _export_packages_toml(connection: sqlite3.Connection, path: Path) -> None:
    rows = connection.execute("SELECT * FROM packages ORDER BY id").fetchall()
    lines = [
        "# SDK package registry managed by mcuenv registry.",
        "",
    ]
    for row in rows:
        targets = json.loads(row["targets_json"] or "[]")
        lines.extend(
            [
                f"[package.{row['id']}]",
                f'family = "{row["family"]}"',
                f'id = "{row["id"]}"',
                f'title = "{row["title"]}"',
                f'path = "{row["path"]}"',
                f'status = "{row["status"]}"',
                f'description = "{row["description"]}"',
            ]
        )
        if targets:
            targets_literal = ", ".join(f'"{value}"' for value in targets)
            lines.append(f"targets = [{targets_literal}]")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _export_manuals_toml(connection: sqlite3.Connection, path: Path) -> None:
    rows = connection.execute("SELECT * FROM manuals ORDER BY id").fetchall()
    lines = [
        "# Manual registry managed by mcuenv registry.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"[manual.{row['id']}]",
                f'family = "{row["family"]}"',
                f'series = "{row["series"]}"',
                f'target = "{row["target"]}"',
                f'title = "{row["title"]}"',
                f'path = "{row["path"]}"',
                f'status = "{row["status"]}"',
                f'kind = "{row["kind"]}"',
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def sync_resource_status(paths: RegistryPaths) -> dict[str, int]:
    updated = {"packages": 0, "manuals": 0}
    with connect(paths.database) as connection:
        for row in connection.execute("SELECT id, path FROM packages").fetchall():
            status = _path_status(paths.root, row["path"])
            connection.execute(
                "UPDATE packages SET status = ? WHERE id = ?",
                (status, row["id"]),
            )
            updated["packages"] += 1

        for row in connection.execute("SELECT id, path FROM manuals").fetchall():
            status = _path_status(paths.root, row["path"])
            connection.execute(
                "UPDATE manuals SET status = ? WHERE id = ?",
                (status, row["id"]),
            )
            updated["manuals"] += 1
        connection.commit()
    return updated


def _path_status(root: Path, relative_path: str) -> str:
    path = Path(relative_path)
    if not path.is_absolute():
        path = root / path
    if path.is_dir():
        return "installed" if any(path.iterdir()) else "missing"
    return "installed" if path.is_file() else "missing"


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "targets_json" in data:
        data["targets"] = json.loads(data.pop("targets_json") or "[]")
    return data


def list_records(paths: RegistryPaths, table: str) -> list[dict[str, Any]]:
    with connect(paths.database) as connection:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    return [row_to_dict(row) for row in rows]


def get_record(paths: RegistryPaths, table: str, record_id: str) -> dict[str, Any] | None:
    with connect(paths.database) as connection:
        row = connection.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (record_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def get_chip(paths: RegistryPaths, chip_id: str) -> dict[str, Any] | None:
    return get_record(paths, "chips", chip_id.lower())


def list_chips(
    paths: RegistryPaths,
    *,
    family: str | None = None,
) -> list[dict[str, Any]]:
    chips = list_records(paths, "chips")
    if family is None:
        return chips
    family_key = family.lower()
    return [chip for chip in chips if chip["family"].lower() == family_key]


def save_chip(paths: RegistryPaths, payload: dict[str, Any]) -> dict[str, Any]:
    init_db(paths)
    with connect(paths.database) as connection:
        _insert_chip(connection, payload)
        connection.commit()
    return get_record(paths, "chips", payload["id"]) or payload


def save_package(paths: RegistryPaths, payload: dict[str, Any]) -> dict[str, Any]:
    targets = payload.get("targets", [])
    with connect(paths.database) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO packages
            (id, family, title, path, status, description, targets_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload["family"],
                payload.get("title", payload["id"]),
                payload["path"],
                payload.get("status", "missing"),
                payload.get("description", ""),
                json.dumps(targets),
            ),
        )
        connection.commit()
    return get_record(paths, "packages", payload["id"]) or payload


def save_manual(paths: RegistryPaths, payload: dict[str, Any]) -> dict[str, Any]:
    with connect(paths.database) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO manuals
            (id, family, series, target, title, path, status, kind)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload["family"],
                payload.get("series", ""),
                payload.get("target", ""),
                payload.get("title", payload["id"]),
                payload["path"],
                payload.get("status", "missing"),
                payload.get("kind", "reference"),
            ),
        )
        connection.commit()
    return get_record(paths, "manuals", payload["id"]) or payload


def delete_record(paths: RegistryPaths, table: str, record_id: str) -> bool:
    with connect(paths.database) as connection:
        cursor = connection.execute(
            f"DELETE FROM {table} WHERE id = ?",
            (record_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
