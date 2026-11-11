"""The schema steps of the module's migrations, written once for MySQL in production and SQLite in the tests."""

from __future__ import annotations

from sqlalchemy import Table, inspect, text
from sqlalchemy.engine import Engine

from core.database import Base


class SiteCareSchemaChanges:
    """
    Creates the module's missing tables and columns, and leaves alone what already exists.

    ``init_db()`` runs before the migrations and creates every missing table from the models, so on an up-to-date
    database each step finds its work done: every step can run any number of times.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine: Engine = engine

    def create_missing_tables(self, *models: type[Base]) -> list[str]:
        """
        Create the table of each model that has none yet, in the given order.

        Args:
            models: The module's ORM classes.

        Returns:
            The names of the tables created.
        """
        created: list[str] = []
        for model in models:
            table: Table = Base.metadata.tables[model.__tablename__]
            if inspect(self._engine).has_table(table.name):
                continue
            table.create(self._engine)
            created.append(table.name)
        return created

    def add_missing_columns(self, table_name: str, definitions: dict[str, str]) -> list[str]:
        """
        Add to a table the columns it does not have yet.

        Args:
            table_name: The table, one of the module's (never a user's text).
            definitions: Each column's name with its SQL definition, written so MySQL and SQLite both read it.

        Returns:
            The names of the columns added.
        """
        present: set[str] = {column["name"] for column in inspect(self._engine).get_columns(table_name)}
        missing: dict[str, str] = {name: sql for name, sql in definitions.items() if name not in present}
        if missing:
            with self._engine.begin() as connection:
                for name, sql in missing.items():
                    connection.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN `{name}` {sql}"))
        return list(missing)
