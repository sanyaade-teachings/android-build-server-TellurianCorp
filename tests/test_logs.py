"""Tests for build log functions."""
import pytest
from pathlib import Path


@pytest.mark.unit
class TestBuildLogs:
    """Test build log saving and retrieval."""
    
    def test_save_build_log(self, mock_server_paths, test_logs_dir):
        """Test saving build log."""
        import server
        log_content = "Build started\nCompiling...\nBuild complete"
        server.save_build_log("TestProject", log_content)
        
        log_file = test_logs_dir / "TestProject.log"
        assert log_file.exists()
        assert log_file.read_text() == log_content
    
    def test_get_build_log_exists(self, mock_server_paths, test_logs_dir):
        """Test retrieving existing build log."""
        import server
        log_content = "Build log content"
        log_file = test_logs_dir / "TestProject.log"
        log_file.write_text(log_content)
        
        result = server.get_build_log("TestProject")
        assert result == log_content
    
    def test_get_build_log_not_exists(self, mock_server_paths):
        """Test retrieving non-existent build log."""
        import server
        result = server.get_build_log("NonExistent")
        assert result is None
    
    def test_get_build_log_invalid_file(self, mock_server_paths, test_logs_dir):
        """Test retrieving log from invalid file."""
        import server
        # Create a directory with the log name (invalid)
        log_file = test_logs_dir / "TestProject.log"
        log_file.mkdir()
        
        result = server.get_build_log("TestProject")
        assert result is None
    
    def test_build_log_path(self, mock_server_paths):
        """Test build log path generation."""
        import server
        path = server.build_log_path("TestProject")
        assert path == mock_server_paths["logs"] / "TestProject.log"
