"""Tests for build functions."""
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path


@pytest.mark.unit
class TestBuildFunctions:
    """Test build execution functions."""
    
    @patch('server.subprocess.run')
    @patch('server.find_latest_apk')
    @patch('server.shutil.copy2')
    def test_run_build_success(self, mock_copy, mock_find_apk, mock_subprocess, 
                                mock_server_paths, test_project):
        """Test successful build execution."""
        import server
        
        # Setup mocks
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        apk_path = test_project / "app" / "build" / "outputs" / "apk" / "debug" / "app.apk"
        apk_path.parent.mkdir(parents=True)
        apk_path.write_bytes(b"apk")
        mock_find_apk.return_value = apk_path
        
        server.run_build("TestProject", "debug")
        
        # Verify subprocess was called
        assert mock_subprocess.called
        # Verify APK was copied
        assert mock_copy.called
    
    @patch('server.subprocess.run')
    def test_run_build_invalid_project(self, mock_subprocess, mock_server_paths):
        """Test build with invalid project."""
        import server
        
        server.run_build("NonExistent", "debug")
        
        # Should not call subprocess for invalid project
        assert not mock_subprocess.called
    
    @patch('server.subprocess.run')
    @patch('server.find_latest_apk')
    def test_run_build_failure(self, mock_find_apk, mock_subprocess, 
                               mock_server_paths, test_project):
        """Test build failure handling."""
        import server
        from subprocess import CalledProcessError
        
        # Setup mocks
        mock_subprocess.return_value = MagicMock(returncode=1, stdout="Error", stderr="Build failed")
        mock_subprocess.side_effect = CalledProcessError(1, "gradlew", "Error", "Build failed")
        
        server.run_build("TestProject", "debug")
        
        # Verify error was handled
        status = server.load_status("TestProject")
        assert status["status"] == "error"
    
    @patch('server.subprocess.run')
    @patch('server.find_latest_apk')
    def test_run_build_apk_not_found(self, mock_find_apk, mock_subprocess,
                                     mock_server_paths, test_project):
        """Test build when APK is not found."""
        import server
        
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        mock_find_apk.return_value = None
        
        server.run_build("TestProject", "debug")
        
        status = server.load_status("TestProject")
        assert status["status"] == "error"
        assert "APK not found" in status.get("message", "")
