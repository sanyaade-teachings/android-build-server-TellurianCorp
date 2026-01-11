"""Pytest configuration and fixtures."""
import json
import tempfile
import shutil
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def test_projects_dir(temp_dir):
    """Create a test projects directory."""
    projects_dir = temp_dir / "projects"
    projects_dir.mkdir()
    return projects_dir


@pytest.fixture
def test_project(test_projects_dir):
    """Create a test Android project with gradlew."""
    project_dir = test_projects_dir / "TestProject"
    project_dir.mkdir()
    (project_dir / "gradlew").write_text("#!/bin/bash\necho 'gradle'")
    (project_dir / "gradlew").chmod(0o755)
    return project_dir


@pytest.fixture
def test_status_dir(temp_dir):
    """Create a test status directory."""
    status_dir = temp_dir / "status"
    status_dir.mkdir()
    return status_dir


@pytest.fixture
def test_artifacts_dir(temp_dir):
    """Create a test artifacts directory."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    return artifacts_dir


@pytest.fixture
def test_logs_dir(temp_dir):
    """Create a test logs directory."""
    logs_dir = temp_dir / "logs"
    logs_dir.mkdir()
    return logs_dir


@pytest.fixture
def test_device_file(temp_dir):
    """Create a test device.json file."""
    device_file = temp_dir / "device.json"
    return device_file


@pytest.fixture
def mock_server_paths(monkeypatch, test_projects_dir, test_status_dir, 
                      test_artifacts_dir, test_logs_dir, test_device_file):
    """Mock server paths for testing."""
    import server
    
    monkeypatch.setattr(server, "BASE_PROJECT_DIR", test_projects_dir)
    monkeypatch.setattr(server, "STATUS_DIR", test_status_dir)
    monkeypatch.setattr(server, "ARTIFACT_DIR", test_artifacts_dir)
    monkeypatch.setattr(server, "LOGS_DIR", test_logs_dir)
    monkeypatch.setattr(server, "DEVICE_FILE", test_device_file)
    
    return {
        "projects": test_projects_dir,
        "status": test_status_dir,
        "artifacts": test_artifacts_dir,
        "logs": test_logs_dir,
        "device": test_device_file,
    }
