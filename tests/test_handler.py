"""Tests for HTTP handler."""
import pytest
from unittest.mock import MagicMock, patch, Mock
from io import BytesIO
from http.server import SimpleHTTPRequestHandler


@pytest.mark.unit
class TestHandler:
    """Test HTTP request handler."""
    
    def _create_handler(self):
        """Helper to create a handler with properly mocked socket."""
        import server
        
        # Patch the parent class __init__ to skip request handling
        original_init = SimpleHTTPRequestHandler.__init__
        def mock_init(self, *args, **kwargs):
            pass
        
        SimpleHTTPRequestHandler.__init__ = mock_init
        
        try:
            mock_socket = MagicMock()
            handler = server.Handler(mock_socket, ("127.0.0.1", 8000), None)
            handler.raw_requestline = b'GET / HTTP/1.1'
            handler.requestline = 'GET / HTTP/1.1'
            handler.command = 'GET'
            handler.path = '/'
            handler.request_version = 'HTTP/1.1'
            handler.headers = {}
            handler.close_connection = False
            handler.rfile = BytesIO()
            handler.wfile = MagicMock()
            return handler
        finally:
            SimpleHTTPRequestHandler.__init__ = original_init
    
    def test_send_json(self, mock_server_paths):
        """Test JSON response sending."""
        handler = self._create_handler()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        
        handler._send_json({"test": "data"})
        
        handler.send_response.assert_called_once()
        handler.send_header.assert_any_call("Content-type", "application/json")
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_once()
    
    @patch('server.list_projects')
    def test_get_projects(self, mock_list_projects, mock_server_paths):
        """Test GET /api/projects endpoint."""
        mock_list_projects.return_value = ["Project1", "Project2"]
        handler = self._create_handler()
        handler.path = "/api/projects"
        handler._send_json = MagicMock()
        handler.log_message = MagicMock()
        handler.do_GET()
        handler._send_json.assert_called_once_with({"projects": ["Project1", "Project2"]})
    
    @patch('server.load_device')
    def test_get_device(self, mock_load_device, mock_server_paths):
        """Test GET /api/device endpoint."""
        mock_load_device.return_value = {"address": "192.168.1.1:5555"}
        handler = self._create_handler()
        handler.path = "/api/device"
        handler._send_json = MagicMock()
        handler.log_message = MagicMock()
        handler.do_GET()
        handler._send_json.assert_called_once_with({"address": "192.168.1.1:5555"})
    
    @patch('server.load_status')
    @patch('server.project_path')
    def test_get_status(self, mock_project_path, mock_load_status, mock_server_paths, test_project):
        """Test GET /api/status endpoint."""
        mock_project_path.return_value = test_project
        mock_load_status.return_value = {"status": "building", "progress": 50}
        handler = self._create_handler()
        handler.path = "/api/status?project=TestProject"
        handler._send_json = MagicMock()
        handler.log_message = MagicMock()
        handler.do_GET()
        handler._send_json.assert_called_once_with({"status": "building", "progress": 50})
    
    @patch('server.save_device')
    def test_post_device(self, mock_save_device, mock_server_paths):
        """Test POST /api/device endpoint."""
        mock_save_device.return_value = {"address": "192.168.1.1:5555"}
        handler = self._create_handler()
        handler.path = "/api/device"
        json_data = b'{"address": "192.168.1.1:5555"}'
        handler.headers = {"Content-Length": str(len(json_data))}
        handler.rfile = BytesIO(json_data)
        handler._send_json = MagicMock()
        handler.log_message = MagicMock()
        handler.do_POST()
        mock_save_device.assert_called_once_with("192.168.1.1:5555")
        handler._send_json.assert_called_once()
    
    @patch('server.run_build')
    @patch('server.has_gradlew')
    @patch('server.project_path')
    def test_post_start_build(self, mock_project_path, mock_has_gradlew, mock_run_build, mock_server_paths, test_project):
        """Test POST /api/start-build endpoint."""
        mock_project_path.return_value = test_project
        mock_has_gradlew.return_value = True
        with patch('server.BUILD_LOCK') as mock_lock, patch('server.ACTIVE_BUILDS', {}) as mock_builds, patch('server.threading.Thread') as mock_thread:
            mock_lock.__enter__ = Mock(return_value=None)
            mock_lock.__exit__ = Mock(return_value=None)
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            handler = self._create_handler()
            handler.path = "/api/start-build"
            json_data = b'{"project": "TestProject", "build_type": "debug"}'
            handler.headers = {"Content-Length": str(len(json_data))}
            handler.rfile = BytesIO(json_data)
            handler._send_json = MagicMock()
            handler.log_message = MagicMock()
            handler.do_POST()
            handler._send_json.assert_called_once_with({"message": "Build started"})
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    @patch('server.load_device')
    @patch('server.project_path')
    def test_post_deploy(self, mock_project_path, mock_load_device, mock_server_paths, test_project):
        """Test POST /api/deploy endpoint."""
        mock_project_path.return_value = test_project
        mock_load_device.return_value = {"address": "192.168.1.1:5555"}
        with patch('server.threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            handler = self._create_handler()
            handler.path = "/api/deploy"
            json_data = b'{"project": "TestProject", "build_type": "debug"}'
            handler.headers = {"Content-Length": str(len(json_data))}
            handler.rfile = BytesIO(json_data)
            handler._send_json = MagicMock()
            handler.log_message = MagicMock()
            handler.do_POST()
            handler._send_json.assert_called_once_with({"message": "Deploy started"})
            mock_thread.assert_called_once()
