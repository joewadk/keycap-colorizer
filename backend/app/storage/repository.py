from contextlib import contextmanager
from pathlib import Path
import sqlite3
from uuid import uuid4

from pydantic import ValidationError

from app.ingestion.models import PageEvidence
from app.ingestion.urls import normalize_url
from app.models.configuration import Configuration
from app.models.compatibility import CompatibilityResult
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.services.compatibility import check_compatibility
from app.storage.models import ConfigurationCreate, KeyboardImport, KeycapImport, RestoredConfiguration


class NotFound(ValueError):
    pass


class Conflict(ValueError):
    pass


class InvalidConfiguration(ValueError):
    pass


class StorageError(RuntimeError):
    pass


class Repository:
    """Per-operation connections; immutable product records keep saved references stable."""

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connection(self):
        connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise StorageError("Unsupported database schema version. Use the matching application version.")
            # Lazy initialization avoids creating a user database merely by importing the app.
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('keyboard','keycaps')),
                    url TEXT NOT NULL, data TEXT NOT NULL, evidence TEXT,
                    UNIQUE(kind, url)
                );
                CREATE TABLE IF NOT EXISTS configurations (
                    id TEXT PRIMARY KEY,
                    keyboard_id TEXT NOT NULL REFERENCES products(id),
                    keycap_set_id TEXT NOT NULL REFERENCES products(id),
                    data TEXT NOT NULL, compatibility TEXT NOT NULL
                );
                PRAGMA user_version=1;
            """)
            with connection:
                yield connection
        except (sqlite3.Error, OSError):
            raise StorageError("Local database could not be read or written. Check DATABASE_PATH and file permissions.") from None
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _product(row):
        if row is None:
            raise NotFound("Product not found.")
        try:
            if row["kind"] == "keyboard":
                return KeyboardDefinition.model_validate_json(row["data"])
            return KeycapSet.model_validate_json(row["data"])
        except ValidationError:
            raise StorageError("Stored product data is invalid; restore a database backup.") from None

    def save_product(self, product: KeyboardDefinition | KeycapSet, evidence: PageEvidence | None = None):
        # Revalidate callers' objects; assignment validation alone does not protect nested lists/maps.
        product = type(product).model_validate_json(product.model_dump_json())
        kind = "keyboard" if isinstance(product, KeyboardDefinition) else "keycaps"
        url = normalize_url(str(product.source_url))
        product = type(product).model_validate({**product.model_dump(), "sourceUrl": url})
        payload = product.model_dump_json()
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM products WHERE id=? OR (kind=? AND url=?)", (product.id, kind, url)).fetchall()
            if existing:
                if len(existing) == 1 and existing[0]["id"] == product.id and existing[0]["kind"] == kind and existing[0]["data"] == payload:
                    return self._product(existing[0])
                raise Conflict("A product with this ID or URL already exists with different data. Saved products cannot be overwritten.")
            db.execute("INSERT INTO products(id,kind,url,data,evidence) VALUES(?,?,?,?,?)",
                       (product.id, kind, url, payload, evidence.model_dump_json() if evidence else None))
        return product

    def get_product(self, product_id: str):
        with self._connection() as db:
            return self._product(db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone())

    def find_product(self, url: str, kind: str):
        with self._connection() as db:
            row = db.execute("SELECT * FROM products WHERE url=? AND kind=?", (normalize_url(url), kind)).fetchone()
            return self._product(row) if row is not None else None

    def get_evidence(self, product_id: str) -> PageEvidence | None:
        with self._connection() as db:
            row = db.execute("SELECT evidence FROM products WHERE id=?", (product_id,)).fetchone()
            if row is None:
                raise NotFound("Product not found.")
            try:
                return PageEvidence.model_validate_json(row["evidence"]) if row["evidence"] else None
            except ValidationError:
                raise StorageError("Stored evidence is invalid; restore a database backup.") from None

    @staticmethod
    def _validate_mapping(configuration, keyboard, keycaps):
        if not isinstance(keyboard, KeyboardDefinition) or not isinstance(keycaps, KeycapSet):
            raise InvalidConfiguration("Choose a keyboard product and a keycap product, in that order.")
        keys = {key.id for key in keyboard.keys}
        colors = {color.id for color in keycaps.colors}
        if not set(configuration.key_color_map).issubset(keys):
            raise InvalidConfiguration("Color map contains keys not present on this keyboard.")
        if not set(configuration.key_color_map.values()).issubset(colors):
            raise InvalidConfiguration("Color map contains colors not present in this keycap set.")

    def save_configuration(self, request: ConfigurationCreate) -> RestoredConfiguration:
        configuration = Configuration(id=str(uuid4()), **request.model_dump())
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            keyboard = self._product(db.execute("SELECT * FROM products WHERE id=?", (request.keyboard_id,)).fetchone())
            keycaps = self._product(db.execute("SELECT * FROM products WHERE id=?", (request.keycap_set_id,)).fetchone())
            self._validate_mapping(configuration, keyboard, keycaps)
            compatibility = check_compatibility(keyboard, keycaps)
            db.execute("INSERT INTO configurations VALUES(?,?,?,?,?)",
                (configuration.id, keyboard.id, keycaps.id, configuration.model_dump_json(), compatibility.model_dump_json()))
        return RestoredConfiguration(configuration=configuration, keyboard=keyboard, keycap_set=keycaps, compatibility=compatibility)

    def get_configuration(self, configuration_id: str) -> RestoredConfiguration:
        with self._connection() as db:
            row = db.execute("SELECT * FROM configurations WHERE id=?", (configuration_id,)).fetchone()
            if row is None:
                raise NotFound("Configuration not found.")
            try:
                config = Configuration.model_validate_json(row["data"])
                if config.keyboard_id != row["keyboard_id"] or config.keycap_set_id != row["keycap_set_id"] or config.id != row["id"]:
                    raise StorageError("Stored configuration references are inconsistent.")
                keyboard = self._product(db.execute("SELECT * FROM products WHERE id=?", (config.keyboard_id,)).fetchone())
                keycaps = self._product(db.execute("SELECT * FROM products WHERE id=?", (config.keycap_set_id,)).fetchone())
                self._validate_mapping(config, keyboard, keycaps)
                compatibility = CompatibilityResult.model_validate_json(row["compatibility"])
                return RestoredConfiguration(configuration=config, keyboard=keyboard, keycap_set=keycaps, compatibility=compatibility)
            except (ValidationError, InvalidConfiguration, NotFound):
                raise StorageError("Stored configuration is invalid; restore a database backup.") from None

    def list_configurations(self, *, limit: int = 50, offset: int = 0) -> list[Configuration]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid pagination")
        with self._connection() as db:
            rows = db.execute("SELECT data FROM configurations ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            try:
                return [Configuration.model_validate_json(row["data"]) for row in rows]
            except ValidationError:
                raise StorageError("Stored configuration list is invalid; restore a database backup.") from None


def product_record(product):
    return (KeyboardImport(kind="keyboard", product=product) if isinstance(product, KeyboardDefinition)
            else KeycapImport(kind="keycaps", product=product))
