"""Tests for project-related functions."""
import pytest
from pathlib import Path


@pytest.mark.unit
class TestProjectPath:
    """Test project path validation."""
    
    def test_project_path_valid(self, mock_server_paths, test_project):
        """Test valid project path."""
        import server
        result = server.project_path("TestProject")
        assert result == test_project
        assert result.is_dir()
    
    def test_project_path_invalid_name(self, mock_server_paths):
        """Test invalid project name with path traversal."""
        import server
        assert server.project_path("../other") is None
        assert server.project_path("project/name") is None
        assert server.project_path("project\\name") is None
    
    def test_project_path_nonexistent(self, mock_server_paths):
        """Test project path for non-existent project."""
        import server
        assert server.project_path("NonExistent") is None
    
    def test_project_path_empty(self, mock_server_paths):
        """Test project path with empty name."""
        import server
        assert server.project_path("") is None
        assert server.project_path(None) is None
    
    def test_has_gradlew_true(self, mock_server_paths, test_project):
        """Test has_gradlew returns True when gradlew exists."""
        import server
        assert server.has_gradlew(test_project) is True
    
    def test_has_gradlew_false(self, mock_server_paths, test_projects_dir):
        """Test has_gradlew returns False when gradlew doesn't exist."""
        import server
        project_dir = test_projects_dir / "NoGradlew"
        project_dir.mkdir()
        assert server.has_gradlew(project_dir) is False
    
    def test_list_projects(self, mock_server_paths, test_project):
        """Test listing projects."""
        import server
        # Create another project without gradlew (shouldn't be listed)
        no_gradlew = mock_server_paths["projects"] / "NoGradlew"
        no_gradlew.mkdir()
        
        projects = server.list_projects()
        assert "TestProject" in projects
        assert "NoGradlew" not in projects
    
    def test_list_projects_empty(self, mock_server_paths, monkeypatch):
        """Test listing projects when directory doesn't exist."""
        import server
        from pathlib import Path
        
        # Temporarily set to non-existent directory
        nonexistent = Path("/nonexistent/directory/that/does/not/exist")
        monkeypatch.setattr(server, "BASE_PROJECT_DIR", nonexistent)
        
        projects = server.list_projects()
        assert projects == []
