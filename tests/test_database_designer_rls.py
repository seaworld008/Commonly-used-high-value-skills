"""Regression tests for database-designer multi-tenant RLS and PR #164 fixes."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL = REPO_ROOT / "skills/developer-engineering/database-designer/SKILL.md"
CANONICAL_RLS = (
    REPO_ROOT
    / "skills/developer-engineering/database-designer/references/orm-and-rls-patterns.md"
)
OPENCLAW_SKILL = REPO_ROOT / "openclaw-skills/database-designer/SKILL.md"
OPENCLAW_RLS = (
    REPO_ROOT / "openclaw-skills/database-designer/references/orm-and-rls-patterns.md"
)
LARK_CONTACT_SKILL = (
    REPO_ROOT / "skills/knowledge-and-pm-integrations/lark-contact/SKILL.md"
)
LARK_SKILL_MAKER = (
    REPO_ROOT / "skills/knowledge-and-pm-integrations/lark-skill-maker/SKILL.md"
)
FIND_SKILLS_RECIPES = (
    REPO_ROOT / "skills/ai-workflow/find-skills/references/catalog-query-recipes.md"
)


def _extract_sql_ddl_block(markdown_text: str) -> str:
    blocks = re.findall(r"```sql\n(.*?)```", markdown_text, flags=re.DOTALL)
    for block in blocks:
        if "CREATE TABLE projects" in block and "CREATE POLICY tasks_read" in block:
            return block
    raise AssertionError("Missing executable multi-tenant RLS SQL block in orm-and-rls-patterns.md")


def test_database_designer_rls_and_openclaw_mirror_include_project_membership() -> None:
    canonical_skill = CANONICAL_SKILL.read_text(encoding="utf-8")
    openclaw_skill = OPENCLAW_SKILL.read_text(encoding="utf-8")
    assert "organization_members" in canonical_skill
    assert "set_config('app.current_user_id'" in canonical_skill
    assert canonical_skill == openclaw_skill

    canonical_rls = CANONICAL_RLS.read_text(encoding="utf-8")
    openclaw_rls = OPENCLAW_RLS.read_text(encoding="utf-8")
    assert canonical_rls == openclaw_rls

    sql_block = _extract_sql_ddl_block(canonical_rls)
    for required in (
        "ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE projects ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;",
        "CREATE POLICY organizations_member_read ON organizations",
        "CREATE POLICY projects_member_read ON projects",
        "CREATE POLICY tasks_read ON tasks",
        "CREATE POLICY tasks_insert ON tasks",
        "CREATE POLICY tasks_update ON tasks",
        "CREATE POLICY tasks_delete ON tasks",
        "NOBYPASSRLS",
        "GRANT UPDATE (title, status, position, version, updated_by_id, updated_at) ON tasks TO app_user;",
        "CREATE OR REPLACE FUNCTION soft_delete_task",
        "SECURITY DEFINER",
        "SET search_path = pg_catalog, public, pg_temp",
        "UPDATE public.tasks t",
        "FROM public.projects p",
        "JOIN public.organization_members om",
        "current_setting('app.current_user_id', true)",
    ):
        assert required in sql_block


def test_pr164_lark_and_find_skills_examples_are_valid() -> None:
    contact_text = LARK_CONTACT_SKILL.read_text(encoding="utf-8")
    assert "contact +search-user" in contact_text
    assert "--queries 'alice@example.com,bob@example.com'" in contact_text
    assert "--emails" not in contact_text

    maker_text = LARK_SKILL_MAKER.read_text(encoding="utf-8")
    assert "calendar +create" in maker_text
    assert "--attendee-ids 'ou_example_target'" in maker_text
    assert "+event-create" not in maker_text
    assert "--attendees " not in maker_text

    recipes_text = FIND_SKILLS_RECIPES.read_text(encoding="utf-8")
    bash_blocks = re.findall(r"```bash\n(.*?)```", recipes_text, flags=re.DOTALL)
    assert len(bash_blocks) == 2
    for idx, script in enumerate(bash_blocks):
        result = subprocess.run(
            ["bash", "-lc", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Recipe {idx + 1} failed: {result.stderr}"
        if idx == 0:
            assert "neon-postgres" in result.stdout
            assert "supabase-postgres-best-practices" in result.stdout
        else:
            assert "database-schema-designer -> database-designer" in result.stdout


class _LocalPostgres:
    """Ephemeral PostgreSQL backend using local initdb/pg_ctl or Docker."""

    def __init__(self) -> None:
        self.mode: str | None = None
        self.tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self.bin_dir: Path | None = None
        self.socket_dir: Path | None = None
        self.container_id: str | None = None
        self.superuser: str = "postgres"

    def _find_pg_bin(self) -> Path | None:
        initdb = shutil.which("initdb")
        if initdb:
            candidate = Path(initdb).parent
            if (candidate / "pg_ctl").exists() and (candidate / "psql").exists():
                return candidate
        for candidate in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True):
            if (candidate / "initdb").exists() and (candidate / "pg_ctl").exists() and (candidate / "psql").exists():
                return candidate
        return None

    def _find_docker_image(self) -> str | None:
        docker = shutil.which("docker")
        if not docker:
            return None
        info = subprocess.run([docker, "info"], capture_output=True, text=True, check=False)
        if info.returncode != 0:
            return None
        imgs = subprocess.run(
            [docker, "images", "--format", "{{.Repository}}:{{.Tag}} {{.ID}}", "postgres"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in imgs.stdout.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            repo_tag, image_id = parts[0], parts[-1]
            return image_id if "<none>" in repo_tag else repo_tag
        return None

    def __enter__(self) -> _LocalPostgres:
        # On Linux non-root hosts (such as CI ubuntu-latest), prefer native initdb.
        pg_bin = self._find_pg_bin()
        if pg_bin is not None and (not hasattr(os, "geteuid") or os.geteuid() != 0):
            self.mode = "native"
            self.bin_dir = pg_bin
            socket_parent = "/tmp" if Path("/tmp").is_dir() else None
            self.tmpdir = tempfile.TemporaryDirectory(prefix="hvs-pg-", dir=socket_parent)
            base = Path(self.tmpdir.name)
            data_dir = base / "data"
            self.socket_dir = base / "sock"
            self.socket_dir.mkdir()
            self.superuser = "postgres"
            subprocess.run(
                [
                    str(pg_bin / "initdb"),
                    "-D",
                    str(data_dir),
                    "-U",
                    self.superuser,
                    "--auth=trust",
                    "--encoding=UTF8",
                    "--locale=C",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            start_res = subprocess.run(
                [
                    str(pg_bin / "pg_ctl"),
                    "-D",
                    str(data_dir),
                    "-l",
                    str(base / "pg.log"),
                    "-o",
                    f"-k {self.socket_dir} -h ''",
                    "-w",
                    "start",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if start_res.returncode != 0:
                log_file = base / "pg.log"
                pg_log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.is_file() else ""
                raise RuntimeError(
                    f"pg_ctl start failed ({start_res.returncode}): {start_res.stderr}\n{pg_log}"
                )
            return self

        image = self._find_docker_image()
        if image is not None:
            self.mode = "docker"
            name = f"hvs-pg-rls-{uuid.uuid4().hex[:8]}"
            res = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    name,
                    "-e",
                    "POSTGRES_HOST_AUTH_METHOD=trust",
                    "-e",
                    "POSTGRES_USER=postgres",
                    image,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.container_id = res.stdout.strip()
            for _ in range(60):
                ready = subprocess.run(
                    ["docker", "exec", self.container_id, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if ready.returncode == 0:
                    probe = subprocess.run(
                        [
                            "docker",
                            "exec",
                            self.container_id,
                            "psql",
                            "-h",
                            "127.0.0.1",
                            "-U",
                            "postgres",
                            "-d",
                            "postgres",
                            "-Atc",
                            "SELECT 1",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if probe.returncode == 0 and probe.stdout.strip() == "1":
                        return self
                import time
                time.sleep(0.5)
            raise RuntimeError("PostgreSQL container did not become ready in time")

        if os.environ.get("CI"):
            pytest.fail("No PostgreSQL engine (initdb or docker) available in CI for RLS regression test")
        pytest.skip("PostgreSQL (initdb or docker) is not available in this environment")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.mode == "native" and self.bin_dir and self.tmpdir:
            data_dir = Path(self.tmpdir.name) / "data"
            subprocess.run(
                [str(self.bin_dir / "pg_ctl"), "-D", str(data_dir), "-m", "immediate", "-w", "stop"],
                capture_output=True,
                check=False,
            )
            self.tmpdir.cleanup()
        elif self.mode == "docker" and self.container_id:
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True, check=False)

    def psql(self, sql: str, *, user: str | None = None, db: str = "postgres") -> subprocess.CompletedProcess[str]:
        target_user = user or self.superuser
        if self.mode == "native":
            assert self.bin_dir and self.socket_dir
            cmd = [
                str(self.bin_dir / "psql"),
                "-h",
                str(self.socket_dir),
                "-U",
                target_user,
                "-d",
                db,
                "-X",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
                "-AtF",
                "\t",
            ]
        else:
            assert self.container_id
            cmd = [
                "docker",
                "exec",
                "-i",
                self.container_id,
                "psql",
                "-h",
                "127.0.0.1",
                "-U",
                target_user,
                "-d",
                db,
                "-X",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
                "-AtF",
                "\t",
            ]
        return subprocess.run(cmd, input=sql, capture_output=True, text=True, check=False)


def _run_as_app_user(pg: _LocalPostgres, user_id: str | None, statement: str) -> subprocess.CompletedProcess[str]:
    set_actor = (
        f"DO $$ BEGIN PERFORM set_config('app.current_user_id', '{user_id}', true); END $$;\n"
        if user_id is not None
        else ""
    )
    sql = f"BEGIN;\nSET LOCAL ROLE app_user;\n{set_actor}{statement}\nCOMMIT;\n"
    return pg.psql(sql, user="schema_owner", db="rls_test")


def test_postgresql_non_owner_tenant_isolation_end_to_end() -> None:
    sql_ddl = _extract_sql_ddl_block(CANONICAL_RLS.read_text(encoding="utf-8"))

    with _LocalPostgres() as pg:
        bootstrap = """
        CREATE ROLE schema_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
        CREATE ROLE app_user NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
        GRANT app_user TO schema_owner;
        CREATE DATABASE rls_test OWNER schema_owner;
        """
        res = pg.psql(bootstrap)
        assert res.returncode == 0, res.stderr

        # Execute the exact documented schema + grants + RLS policies as non-superuser schema_owner.
        ddl_res = pg.psql(sql_ddl, user="schema_owner", db="rls_test")
        assert ddl_res.returncode == 0, ddl_res.stderr

        # Confirm schema tables are owned by schema_owner (not app_user) and app_user has no bypass.
        owner_check = pg.psql(
            "SELECT tablename, tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename IN ('organizations','organization_members','projects','tasks') "
            "ORDER BY tablename;",
            user="schema_owner",
            db="rls_test",
        )
        assert owner_check.returncode == 0, owner_check.stderr
        assert owner_check.stdout.strip().splitlines() == [
            "organization_members\tschema_owner",
            "organizations\tschema_owner",
            "projects\tschema_owner",
            "tasks\tschema_owner",
        ]

        role_check = pg.psql(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app_user';",
            user="schema_owner",
            db="rls_test",
        )
        assert role_check.returncode == 0, role_check.stderr
        assert role_check.stdout.strip() == "f\tf"

        seed = """
        INSERT INTO organizations (id, name) VALUES ('org_a', 'Tenant A'), ('org_b', 'Tenant B');
        INSERT INTO users (id, email) VALUES
          ('alice', 'alice@a.test'),
          ('carol', 'carol@a.test'),
          ('viewer_a', 'viewer@a.test'),
          ('bob', 'bob@b.test');
        INSERT INTO organization_members (id, organization_id, user_id, role) VALUES
          ('m_a1', 'org_a', 'alice', 'member'),
          ('m_a2', 'org_a', 'carol', 'admin'),
          ('m_a3', 'org_a', 'viewer_a', 'viewer'),
          ('m_b1', 'org_b', 'bob', 'member');
        INSERT INTO projects (id, organization_id, owner_id, name, deleted_at) VALUES
          ('proj_a', 'org_a', 'carol', 'Alpha', NULL),
          ('proj_a_deleted', 'org_a', 'carol', 'Archived Alpha', NOW()),
          ('proj_b', 'org_b', 'bob', 'Beta', NULL);
        INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id, deleted_at) VALUES
          ('task_a_alice', 'proj_a', 'Alice Task', 'alice', 'alice', NULL),
          ('task_a_carol', 'proj_a', 'Carol Task', 'carol', 'carol', NULL),
          ('task_a_deleted', 'proj_a', 'Deleted Task', 'alice', 'alice', NOW()),
          ('task_b_bob', 'proj_b', 'Bob Secret Task', 'bob', 'bob', NULL);
        """
        seed_res = pg.psql(seed, user="schema_owner", db="rls_test")
        assert seed_res.returncode == 0, seed_res.stderr

        # 1. Fail-closed when no actor is configured
        unauth = _run_as_app_user(
            pg,
            None,
            "SELECT count(*) FROM organizations; SELECT count(*) FROM projects; SELECT count(*) FROM tasks;",
        )
        assert unauth.returncode == 0, unauth.stderr
        assert unauth.stdout.strip().splitlines() == ["0", "0", "0"]
        unauth_insert = _run_as_app_user(
            pg,
            None,
            "INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id) "
            "VALUES ('t_unauth', 'proj_a', 'No Actor', 'alice', 'alice');",
        )
        assert unauth_insert.returncode != 0
        assert "row-level security" in unauth_insert.stderr

        # 2. Same-tenant reads exclude foreign-tenant and soft-deleted rows
        read_a = _run_as_app_user(
            pg,
            "alice",
            "SELECT id FROM organizations ORDER BY id;\nSELECT id FROM projects ORDER BY id;\nSELECT id FROM tasks ORDER BY id;",
        )
        assert read_a.returncode == 0, read_a.stderr
        assert read_a.stdout.strip().splitlines() == [
            "org_a",
            "proj_a",
            "task_a_alice",
            "task_a_carol",
        ]

        # 3. Same-tenant insert, column update, and controlled soft-delete RPC succeed
        write_a = _run_as_app_user(
            pg,
            "alice",
            "INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id) "
            "VALUES ('task_a_new', 'proj_a', 'New Task', 'alice', 'alice') RETURNING id;\n"
            "UPDATE tasks SET title = 'Updated Task', status = 'in_progress', updated_by_id = 'alice' "
            "WHERE id = 'task_a_new' RETURNING title;\n"
            "SELECT soft_delete_task('task_a_new');\n"
            "SELECT count(*) FROM tasks WHERE id = 'task_a_new';",
        )
        assert write_a.returncode == 0, write_a.stderr
        assert write_a.stdout.strip().splitlines() == [
            "task_a_new",
            "Updated Task",
            "t",
            "0",
        ]

        # Unauthorized / cross-tenant soft-delete calls must return false
        bad_soft_del = _run_as_app_user(
            pg,
            "alice",
            "SELECT soft_delete_task('task_b_bob');\nSELECT soft_delete_task('task_a_carol');",
        )
        assert bad_soft_del.returncode == 0, bad_soft_del.stderr
        assert bad_soft_del.stdout.strip().splitlines() == ["f", "f"]

        # 4. Cross-tenant SELECT / UPDATE / DELETE affect 0 rows
        cross_rw = _run_as_app_user(
            pg,
            "alice",
            "SELECT count(*) FROM tasks WHERE id = 'task_b_bob';\n"
            "WITH u AS (UPDATE tasks SET title = 'Hacked' WHERE id = 'task_b_bob' RETURNING id) SELECT count(*) FROM u;\n"
            "WITH d AS (DELETE FROM tasks WHERE id = 'task_b_bob' RETURNING id) SELECT count(*) FROM d;",
        )
        assert cross_rw.returncode == 0, cross_rw.stderr
        assert cross_rw.stdout.strip().splitlines() == ["0", "0", "0"]

        # 5. Cross-tenant INSERT is rejected by RLS
        cross_ins = _run_as_app_user(
            pg,
            "alice",
            "INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id) "
            "VALUES ('t_cross', 'proj_b', 'Cross Tenant', 'alice', 'alice');",
        )
        assert cross_ins.returncode != 0
        assert "row-level security" in cross_ins.stderr

        # 6. Spoofed created_by_id INSERT is rejected by RLS
        spoof_ins = _run_as_app_user(
            pg,
            "alice",
            "INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id) "
            "VALUES ('t_spoof', 'proj_a', 'Spoofed Creator', 'carol', 'alice');",
        )
        assert spoof_ins.returncode != 0
        assert "row-level security" in spoof_ins.stderr

        # 7. Read-only viewer can read own tenant but cannot INSERT or UPDATE
        viewer_read = _run_as_app_user(pg, "viewer_a", "SELECT id FROM tasks ORDER BY id;")
        assert viewer_read.returncode == 0, viewer_read.stderr
        assert viewer_read.stdout.strip().splitlines() == ["task_a_alice", "task_a_carol"]

        viewer_ins = _run_as_app_user(
            pg,
            "viewer_a",
            "INSERT INTO tasks (id, project_id, title, created_by_id, updated_by_id) "
            "VALUES ('t_view', 'proj_a', 'Viewer Write', 'viewer_a', 'viewer_a');",
        )
        assert viewer_ins.returncode != 0
        assert "row-level security" in viewer_ins.stderr

        viewer_upd = _run_as_app_user(
            pg,
            "viewer_a",
            "WITH u AS (UPDATE tasks SET title = 'Viewer Edit' WHERE id = 'task_a_alice' RETURNING id) SELECT count(*) FROM u;",
        )
        assert viewer_upd.returncode == 0, viewer_upd.stderr
        assert viewer_upd.stdout.strip() == "0"

        # 8. Ownership column UPDATE tampering and self-membership escalation are rejected
        tamper_proj = _run_as_app_user(
            pg,
            "alice",
            "UPDATE tasks SET project_id = 'proj_b' WHERE id = 'task_a_alice';",
        )
        assert tamper_proj.returncode != 0
        assert "permission denied" in tamper_proj.stderr

        tamper_member = _run_as_app_user(
            pg,
            "alice",
            "INSERT INTO organization_members (id, organization_id, user_id, role) "
            "VALUES ('m_hack', 'org_b', 'alice', 'admin');",
        )
        assert tamper_member.returncode != 0
        assert "permission denied" in tamper_member.stderr

        # 9. Creator vs. admin delete boundaries
        member_del_other = _run_as_app_user(
            pg,
            "alice",
            "WITH d AS (DELETE FROM tasks WHERE id = 'task_a_carol' RETURNING id) SELECT count(*) FROM d;",
        )
        assert member_del_other.returncode == 0, member_del_other.stderr
        assert member_del_other.stdout.strip() == "0"

        admin_del_member = _run_as_app_user(
            pg,
            "carol",
            "WITH d AS (DELETE FROM tasks WHERE id = 'task_a_alice' RETURNING id) SELECT count(*) FROM d;",
        )
        assert admin_del_member.returncode == 0, admin_del_member.stderr
        assert admin_del_member.stdout.strip() == "1"

        # 10. Temp-table shadowing attack inside pg_temp cannot escalate soft_delete_task
        shadow_attack = _run_as_app_user(
            pg,
            "alice",
            "CREATE TEMP TABLE organization_members ("
            "id TEXT, organization_id TEXT, user_id TEXT, role TEXT"
            ");\n"
            "INSERT INTO pg_temp.organization_members VALUES ('m_evil', 'org_b', 'alice', 'admin');\n"
            "GRANT SELECT ON pg_temp.organization_members TO schema_owner;\n"
            "SELECT public.soft_delete_task('task_b_bob');",
        )
        assert shadow_attack.returncode == 0, shadow_attack.stderr
        assert shadow_attack.stdout.strip() == "f"

        # Confirm Tenant B's org and task visibility remained completely isolated & untouched
        verify_b = _run_as_app_user(
            pg,
            "bob",
            "SELECT id FROM organizations ORDER BY id;\nSELECT id || ':' || title FROM tasks ORDER BY id;",
        )
        assert verify_b.returncode == 0, verify_b.stderr
        assert verify_b.stdout.strip().splitlines() == [
            "org_b",
            "task_b_bob:Bob Secret Task",
        ]
