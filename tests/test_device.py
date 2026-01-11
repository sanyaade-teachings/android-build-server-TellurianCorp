"""Tests for device configuration functions."""
import json
import pytest
from pathlib import Path


@pytest.mark.unit
class TestDeviceConfig:
    """Test device configuration loading and saving."""
    
    def test_load_device_not_exists(self, mock_server_paths):
        """Test loading device when file doesn't exist."""
        import server
        result = server.load_device()
        assert result == {"address": ""}
    
    def test_load_device_exists(self, mock_server_paths, test_device_file):
        """Test loading device when file exists."""
        import server
        test_device_file.write_text(json.dumps({"address": "192.168.1.1:5555"}))
        result = server.load_device()
        assert result == {"address": "192.168.1.1:5555"}
    
    def test_load_device_invalid_json(self, mock_server_paths, test_device_file):
        """Test loading device with invalid JSON."""
        import server
        test_device_file.write_text("invalid json")
        result = server.load_device()
        assert result == {"address": ""}
    
    def test_save_device(self, mock_server_paths, test_device_file):
        """Test saving device configuration."""
        import server
        result = server.save_device("192.168.1.1:5555")
        assert result == {"address": "192.168.1.1:5555"}
        assert test_device_file.exists()
        content = json.loads(test_device_file.read_text())
        assert content == {"address": "192.168.1.1:5555"}
    
    def test_save_device_empty(self, mock_server_paths, test_device_file):
        """Test saving empty device address."""
        import server
        result = server.save_device("")
        assert result == {"address": ""}
        content = json.loads(test_device_file.read_text())
        assert content == {"address": ""}
