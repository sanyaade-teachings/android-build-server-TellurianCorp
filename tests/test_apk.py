"""Tests for APK finding functions."""
import pytest
from pathlib import Path
import time


@pytest.mark.unit
class TestAPKFinding:
    """Test APK finding functions."""
    
    def test_find_latest_apk_standard_path(self, mock_server_paths, test_projects_dir):
        """Test finding APK in standard path."""
        import server
        
        project_dir = test_projects_dir / "TestProject"
        project_dir.mkdir()
        apk_dir = project_dir / "app" / "build" / "outputs" / "apk" / "debug"
        apk_dir.mkdir(parents=True)
        
        # Create two APKs with different timestamps
        apk1 = apk_dir / "app-debug.apk"
        apk1.write_bytes(b"apk1")
        time.sleep(0.1)  # Ensure different mtime
        apk2 = apk_dir / "app-debug-v2.apk"
        apk2.write_bytes(b"apk2")
        
        result = server.find_latest_apk(project_dir, "debug")
        assert result == apk2  # Should be the newest
    
    def test_find_latest_apk_glob_path(self, mock_server_paths, test_projects_dir):
        """Test finding APK using glob search."""
        import server
        
        project_dir = test_projects_dir / "TestProject"
        project_dir.mkdir()
        # Create non-standard path
        apk_dir = project_dir / "custom" / "build" / "outputs" / "apk" / "debug"
        apk_dir.mkdir(parents=True)
        
        apk = apk_dir / "app.apk"
        apk.write_bytes(b"apk")
        
        result = server.find_latest_apk(project_dir, "debug")
        assert result == apk
    
    def test_find_latest_apk_not_found(self, mock_server_paths, test_projects_dir):
        """Test finding APK when none exists."""
        import server
        
        project_dir = test_projects_dir / "TestProject"
        project_dir.mkdir()
        
        result = server.find_latest_apk(project_dir, "debug")
        assert result is None
    
    def test_latest_artifact_path_exists(self, mock_server_paths, test_artifacts_dir):
        """Test finding latest artifact when it exists."""
        import server
        
        project_artifacts = test_artifacts_dir / "TestProject"
        project_artifacts.mkdir()
        
        apk1 = project_artifacts / "app-debug.apk"
        apk1.write_bytes(b"apk1")
        time.sleep(0.1)
        apk2 = project_artifacts / "app-debug-v2.apk"
        apk2.write_bytes(b"apk2")
        
        result = server.latest_artifact_path("TestProject")
        assert result == apk2
    
    def test_latest_artifact_path_not_exists(self, mock_server_paths):
        """Test finding latest artifact when directory doesn't exist."""
        import server
        result = server.latest_artifact_path("NonExistent")
        assert result is None
    
    def test_latest_artifact_path_no_apks(self, mock_server_paths, test_artifacts_dir):
        """Test finding latest artifact when no APKs exist."""
        import server
        
        project_artifacts = test_artifacts_dir / "TestProject"
        project_artifacts.mkdir()
        
        result = server.latest_artifact_path("TestProject")
        assert result is None
