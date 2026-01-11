"""Tests for ADB finding functions."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestADBFinding:
    """Test ADB executable finding."""
    
    @patch('server.shutil.which')
    @patch('server.os.path.isfile')
    @patch('server.os.access')
    def test_find_adb_in_common_path(self, mock_access, mock_isfile, mock_which):
        """Test finding ADB in common path."""
        import server
        
        mock_isfile.return_value = True
        mock_access.return_value = True
        
        result = server.find_adb()
        # Should check common paths first
        assert mock_isfile.called
    
    @patch('server.shutil.which')
    @patch('server.os.path.isfile')
    @patch('server.os.access')
    def test_find_adb_in_path(self, mock_access, mock_isfile, mock_which):
        """Test finding ADB in system PATH."""
        import server
        
        mock_isfile.return_value = False
        mock_which.return_value = "/usr/bin/adb"
        
        result = server.find_adb()
        assert result == "/usr/bin/adb"
        assert mock_which.called
    
    @patch('server.shutil.which')
    @patch('server.os.path.isfile')
    @patch('server.os.access')
    def test_find_adb_not_found(self, mock_access, mock_isfile, mock_which):
        """Test when ADB is not found."""
        import server
        
        mock_isfile.return_value = False
        mock_which.return_value = None
        
        result = server.find_adb()
        assert result is None
