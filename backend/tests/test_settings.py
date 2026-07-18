from app.config.settings import Settings


def test_database_url_escapes_password_without_logging_it():
    settings = Settings(
        _env_file=None,
        API_TITLE="AeroC API",
        API_VERSION="2.0.0",
        DATABASE_HOST="localhost",
        DATABASE_PORT=5432,
        DATABASE_NAME="aeroc",
        DATABASE_USER="aeroc",
        DATABASE_PASSWORD="pa:ss@word",
    )

    assert settings.database_url.render_as_string(hide_password=False) == (
        "postgresql+psycopg://aeroc:pa%3Ass%40word@localhost:5432/aeroc"
    )
