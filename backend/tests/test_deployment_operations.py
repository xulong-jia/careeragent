from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_production_like_deployment_files_exist():
    expected_files = [
        ROOT_DIR / ".env.production.example",
        ROOT_DIR / "docker-compose.prod-like.yml",
        ROOT_DIR / "frontend" / "Dockerfile.production",
        ROOT_DIR / "frontend" / "nginx.conf",
        ROOT_DIR / "scripts" / "db_migrate.sh",
        ROOT_DIR / "scripts" / "db_backup.sh",
        ROOT_DIR / "scripts" / "db_restore.sh",
        ROOT_DIR / "scripts" / "run_quality_gates.sh",
    ]

    for path in expected_files:
        assert path.exists(), path


def test_operations_scripts_are_executable_and_guard_destructive_restore():
    scripts = [
        ROOT_DIR / "scripts" / "db_migrate.sh",
        ROOT_DIR / "scripts" / "db_backup.sh",
        ROOT_DIR / "scripts" / "db_restore.sh",
        ROOT_DIR / "scripts" / "run_quality_gates.sh",
    ]

    for script in scripts:
        assert os.access(script, os.X_OK), script

    restore_script = (ROOT_DIR / "scripts" / "db_restore.sh").read_text()
    assert "CONFIRM_RESTORE=restore" in restore_script
    assert "SQLite is local/dev only" in restore_script


def test_production_like_compose_uses_postgres_pgvector_and_required_secrets():
    compose = (ROOT_DIR / "docker-compose.prod-like.yml").read_text()

    assert "pgvector/pgvector:pg16" in compose
    assert "AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:?" in compose
    assert "DATA_ENCRYPTION_KEY: ${DATA_ENCRYPTION_KEY:?" in compose
    assert "DB_ECHO_SQL: ${DB_ECHO_SQL:-false}" in compose
    assert "/ready" in compose
    assert "Dockerfile.production" in compose


def test_gitignore_keeps_production_env_template_but_blocks_backups():
    gitignore = (ROOT_DIR / ".gitignore").read_text()

    assert "!.env.production.example" in gitignore
    assert "backups/" in gitignore
    assert "*.dump" in gitignore


def test_production_env_template_contains_no_concrete_provider_secret():
    template = (ROOT_DIR / ".env.production.example").read_text()

    assert "OPENAI_API_KEY=" not in template
    assert "sk-" not in template
    assert "xoxb-" not in template
    assert "AKIA" not in template
    assert "APP_ENV=production" in template
    assert "VECTOR_STORE=local" in template
