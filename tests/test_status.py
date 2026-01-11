"""Tests for status management functions."""
import json
import pytest
from pathlib import Path


@pytest.mark.unit
class TestStatusManagement:
    """Test status loading and writing."""
    
    def test_load_status_not_exists(self, mock_server_paths):
        """Test loading status when file doesn't exist."""
        import server
        result = server.load_status("TestProject")
        assert result == {"status": "not_started", "progress": 0}
    
    def test_load_status_exists(self, mock_server_paths, test_status_dir):
        """Test loading status when file exists."""
        import server
        status_file = test_status_dir / "TestProject.json"
        status_data = {
            "project": "TestProject",
            "status": "building",
            "progress": 50,
            "timestamp": 1234567890
        }
        status_file.write_text(json.dumps(status_data))
        
        result = server.load_status("TestProject")
        assert result["status"] == "building"
        assert result["progress"] == 50
        assert result["project"] == "TestProject"
    
    def test_load_status_invalid_json(self, mock_server_paths, test_status_dir):
        """Test loading status with invalid JSON."""
        import server
        status_file = test_status_dir / "TestProject.json"
        status_file.write_text("invalid json")
        
        result = server.load_status("TestProject")
        assert result == {"status": "unknown", "progress": 0}
    
    def test_write_status_basic(self, mock_server_paths, test_status_dir):
        """Test writing basic status."""
        import server
        server.write_status("TestProject", "building", 50)
        
        status_file = test_status_dir / "TestProject.json"
        assert status_file.exists()
        
        data = json.loads(status_file.read_text())
        assert data["project"] == "TestProject"
        assert data["status"] == "building"
        assert data["progress"] == 50
        assert "timestamp" in data
    
    def test_write_status_with_message(self, mock_server_paths, test_status_dir):
        """Test writing status with message."""
        import server
        server.write_status("TestProject", "error", 0, message="Build failed")
        
        status_file = test_status_dir / "TestProject.json"
        data = json.loads(status_file.read_text())
        assert data["message"] == "Build failed"
    
    def test_write_status_with_artifact(self, mock_server_paths, test_status_dir):
        """Test writing status with artifact."""
        import server
        server.write_status("TestProject", "done", 100, artifact="/artifacts/TestProject/app.apk")
        
        status_file = test_status_dir / "TestProject.json"
        data = json.loads(status_file.read_text())
        assert data["artifact"] == "/artifacts/TestProject/app.apk"
    
    def test_write_status_with_both(self, mock_server_paths, test_status_dir):
        """Test writing status with both message and artifact."""
        import server
        server.write_status(
            "TestProject", 
            "done", 
            100, 
            message="Build complete",
            artifact="/artifacts/TestProject/app.apk"
        )
        
        status_file = test_status_dir / "TestProject.json"
        data = json.loads(status_file.read_text())
        assert data["message"] == "Build complete"
        assert data["artifact"] == "/artifacts/TestProject/app.apk"
