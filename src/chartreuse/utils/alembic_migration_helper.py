# -*- coding: utf-8 -*-
from future.standard_library import install_aliases

install_aliases()

import os
import re
import socket
import urllib.parse

import sqlalchemy

from wiremind_kubernetes import _run_command


class AlembicMigrationHelper(object):
    database_url = None
    allow_migration_for_empty_database = False

    def __init__(self, database_url, allow_migration_for_empty_database=False):
        if not database_url:
            raise EnvironmentError("database_url not set, not upgrading database.")

        self.database_url = database_url
        self.allow_migration_for_empty_database = allow_migration_for_empty_database

        self._configure()

    def _configure(self):
        os.chdir("/app/alembic")
        cleaned_url = self.database_url.replace("/", r"\/")
        _run_command(
            "sed -i -e 's/sqlalchemy.url.*=.*/sqlalchemy.url=%s/' %s"
            % (cleaned_url, "alembic.ini")
        )

    def check_migration_possible(self):
        if not self.is_postgres_domain_name_resolvable():
            print("Postgres server does not exist yet, not upgrading database.")
            return False
        if not self.is_postgres_reachable():
            print("Postgres server does not answer, not upgrading database.")
            return False
        if (not self.allow_migration_for_empty_database and self.is_postgres_empty()):
            print("Database is not populated yet, not upgrading it.")
            return False
        if not self.is_migration_needed():
            print("Database does not need migration.")
            return False
        return True

    def is_postgres_domain_name_resolvable(self):
        os.chdir("/app/alembic")
        hostname = urllib.parse.urlparse(self.database_url).hostname
        try:
            socket.gethostbyname(hostname)
        except socket.gaierror:
            print(
                "Could not resolve hostname %s, assuming postgres server does not exist yet."
                % hostname
            )
            return False
        return True

    def is_postgres_reachable(self):
        os.chdir("/app/alembic")
        try:
            sqlalchemy.create_engine(self.database_url).table_names()
        except sqlalchemy.exc.OperationalError:
            print(
                "Could not reach postgresql, assuming postgres server does not exist yet or is down."
            )
            return False
        return True

    def is_postgres_empty(self):
        os.chdir("/app/alembic")
        table_list = sqlalchemy.create_engine(self.database_url).table_names()
        self._is_postgres_empty(table_list)

    def _is_postgres_empty(self, table_list):
        """
        Internal method called by is_postgres_empty to ease testing.
        """
        print("Tables in database: %s" % table_list)
        # Don't count "alembic" table
        table_name = "alembic_version"
        if table_name in table_list:
            table_list.remove(table_name)
        if table_list:
            return False
        return True

    def is_migration_needed(self):
        os.chdir("/app/alembic")
        head_re = re.compile(r"\(head\)", re.MULTILINE)
        alembic_current, _ = _run_command("alembic current")
        if head_re.search(alembic_current):
            return False
        return True

    def migrate_db(self):
        os.chdir("/app/alembic")
        print("Database needs to be upgraded. Proceeding.")
        _run_command("alembic history -r current:head")

        print("Upgrading database...")
        _run_command("alembic upgrade head")

        print("Done upgrading database.")
