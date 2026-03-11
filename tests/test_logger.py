from pathlib import Path

from zarus_core.logging import CustomLogging


def test_shared_project_context_writes_single_file(tmp_path: Path):
    log_path = tmp_path / "shared.log"

    CustomLogging.configure_project(
        project_name="host_project",
        log_file=str(log_path),
        level="INFO",
        force_reconfigure=True,
    )

    logger_a = CustomLogging(component_name="Config").get_logger()
    logger_b = CustomLogging(component_name="Mqtt").get_logger()

    logger_a.info("config loaded")
    logger_b.info("mqtt started")

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "host_project.Config" in content
    assert "host_project.Mqtt" in content
