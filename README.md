# Android Build Server

[![Tests](https://github.com/USERNAME/android-build/actions/workflows/test.yml/badge.svg)](https://github.com/USERNAME/android-build/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/USERNAME/android-build/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/android-build)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A web-based Android build server that provides a modern interface for building and deploying Android APKs remotely. This server manages Android projects, builds APKs, and can deploy directly to connected devices.

## Features

- 🚀 **Web-based Interface**: Modern, responsive web UI for managing builds
- 📦 **APK Building**: Build debug and release APKs from Android projects
- 📱 **Device Deployment**: Deploy APKs directly to Android devices via ADB
- 📊 **Build Status**: Real-time build progress and status tracking
- 📝 **Build Logs**: View detailed build logs for troubleshooting
- 🔒 **Project Isolation**: Secure project path validation
- ⚡ **Async Builds**: Non-blocking build execution with threading

## Requirements

- Python 3.6+
- Android SDK with platform-tools (for ADB deployment)
- Gradle-based Android projects
- Nginx (optional, for reverse proxy)

## Installation

### Quick Start

1. Clone this repository:
```bash
git clone <repository-url>
cd android-build
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure your Android projects are located in `/home/projects/` directory. Each project should:
   - Have a `gradlew` executable
   - Be a valid Gradle-based Android project

4. Start the server:
```bash
python3 server.py
```

The web interface will be available at `http://localhost:8000`

### Using the Installer Script

Run the interactive installer:
```bash
./install.sh
```

The installer will:
- Check for required tools (rsync, ssh, scp, python3)
- Configure remote build settings
- Set up helper scripts
- Start the web server

### Installing as a Systemd Service

To run the server as a systemd service (recommended for production):

```bash
sudo ./install-service.sh
```

The installer will:
- Create a systemd service file
- Configure the service to run as a specific user
- Set proper file permissions
- Enable the service to start on boot
- Optionally start the service immediately

**Service Management:**
```bash
# Start the service
sudo systemctl start android-build

# Stop the service
sudo systemctl stop android-build

# Restart the service
sudo systemctl restart android-build

# Check service status
sudo systemctl status android-build

# View logs
sudo journalctl -u android-build -f

# Enable/disable auto-start on boot
sudo systemctl enable android-build
sudo systemctl disable android-build
```

## Configuration

### Project Directory

By default, the server looks for Android projects in `/home/projects/`. Each project directory should:
- Contain a `gradlew` executable
- Be a valid Android Gradle project
- Have the standard Android project structure

### Device Configuration

To deploy APKs to devices, configure the device address via the web interface or by editing `device.json`:

```json
{
  "address": "192.168.0.148:43419"
}
```

**Note**: `device.json` is git-ignored as it contains deployment-specific configuration.

### Nginx Configuration (Optional)

If using Nginx as a reverse proxy, create an `nginx.conf` file (template provided but git-ignored):

```nginx
server {
    listen 80;
    server_name localhost;

    root /var/www/html/android-build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Select a project from the dropdown
3. Choose build type (debug or release)
4. Click "Start Build" to begin building
5. Monitor build progress in real-time
6. Download the APK when the build completes

### Device Deployment

1. Configure your device address in the web interface
2. Ensure your Android device is connected via ADB (USB or network)
3. Build an APK or use an existing one
4. Click "Deploy" to install the APK on your device

### API Endpoints

The server provides REST API endpoints:

- `GET /api/projects` - List available projects
- `GET /api/device` - Get device configuration
- `POST /api/device` - Update device configuration
- `GET /api/status?project=<name>` - Get build status for a project
- `GET /api/logs?project=<name>` - Get build logs for a project
- `POST /api/start-build` - Start a build
  ```json
  {
    "project": "MyProject",
    "build_type": "debug"
  }
  ```
- `POST /api/deploy` - Deploy APK to device
  ```json
  {
    "project": "MyProject",
    "build_type": "debug"
  }
  ```

## Project Structure

```
android-build/
├── server.py              # Main server application
├── index.html             # Web interface
├── script.js              # Frontend JavaScript
├── install.sh             # Installation script
├── install-service.sh     # Systemd service installer
├── android-build.service  # Systemd service template
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── .coveragerc            # Coverage configuration
├── Makefile               # Make commands for testing
├── .gitignore             # Git ignore rules
├── .github/
│   └── workflows/         # GitHub Actions CI/CD workflows
│       ├── test.yml       # Test workflow
│       └── lint.yml      # Lint workflow
├── tests/                 # Unit tests
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
├── artifacts/             # Built APK files (git-ignored)
├── logs/                  # Build logs (git-ignored)
└── status/                # Build status files (git-ignored)
```

## Build Process

1. **Preparing**: Validates project and prepares build environment
2. **Building**: Executes Gradle build command
3. **Finding APK**: Locates the generated APK file
4. **Copying**: Copies APK to artifacts directory
5. **Done**: Build complete, APK available for download

## Deployment Process

1. **Connecting Device**: Connects to Android device via ADB
2. **Finding APK**: Locates the APK to deploy
3. **Installing APK**: Installs APK on the device
4. **Deployed**: Installation complete

## Security Considerations

- Project paths are validated to prevent directory traversal attacks
- Only projects in `/home/projects/` are accessible
- Build commands are executed in isolated project directories
- Device addresses are validated before deployment

## Troubleshooting

### Build Fails

- Check build logs via the web interface
- Ensure the project has a valid `gradlew` file
- Verify the project structure is correct
- Check that all dependencies are available

### Device Not Found

- Ensure ADB is installed and in PATH
- Verify device is connected (USB or network)
- Check device address format: `IP:PORT` or device ID
- Test connection manually: `adb connect <address>`

### Projects Not Showing

- Verify projects are in `/home/projects/` directory
- Ensure each project has a `gradlew` executable
- Check file permissions on project directories

## Testing

The project includes comprehensive unit tests with coverage reporting.

### Running Tests

Install test dependencies:
```bash
pip install -r requirements.txt
```

Run all tests:
```bash
pytest
```

Or use the Makefile:
```bash
make test              # Run tests
make test-cov          # Run tests with coverage
make test-html         # Generate HTML coverage report
make test-verbose      # Run tests in verbose mode
make test-file FILE=tests/test_device.py  # Run specific test file
```

### Test Coverage

Generate coverage report:
```bash
pytest --cov=. --cov-report=html
```

View the HTML report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest fixtures and configuration
├── test_device.py       # Device configuration tests
├── test_project.py      # Project path validation tests
├── test_status.py       # Status management tests
├── test_logs.py         # Build log tests
├── test_apk.py          # APK finding tests
├── test_adb.py           # ADB finding tests
├── test_build.py         # Build execution tests
└── test_handler.py      # HTTP handler tests
```

### Writing Tests

Tests use `pytest` with fixtures for isolated test environments. Each test file focuses on a specific module or functionality. Mocking is used for external dependencies like subprocess calls and file system operations.

## Development

### Running in Development

```bash
python3 server.py
```

The server runs on port 8000 by default. Logs are written to `server.log`.

### Adding New Features

The server is built with Python's `http.server` module. Key components:
- `Handler` class: Handles HTTP requests
- `run_build()`: Executes Gradle builds
- `run_deploy()`: Handles device deployment
- Status tracking: JSON files in `status/` directory

When adding new features:
1. Write unit tests first (TDD approach)
2. Ensure tests pass: `make test`
3. Check coverage: `make test-cov`
4. Update documentation as needed

## CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment.

### Workflows

- **Tests** (`.github/workflows/test.yml`): Runs tests on multiple Python versions (3.9, 3.10, 3.11, 3.12)
  - Executes all unit tests with coverage
  - Uploads coverage reports to Codecov
  - Generates HTML coverage reports as artifacts
  - Runs on push and pull requests

- **Lint** (`.github/workflows/lint.yml`): Code quality checks
  - Runs flake8 for style and error checking
  - Runs pylint for code analysis
  - Runs on push and pull requests

### Coverage Reports

Coverage reports are automatically generated and uploaded to:
- **Codecov**: [View coverage dashboard](https://codecov.io/gh/USERNAME/android-build)
- **GitHub Actions Artifacts**: Download HTML reports from workflow runs

### Setting Up CI/CD

1. **Enable Codecov** (optional but recommended):
   - Sign up at [codecov.io](https://codecov.io)
   - Add your repository
   - Update the badge URLs in README.md with your username/organization

2. **Update Badge URLs**:
   - Replace `USERNAME` in the badge URLs with your GitHub username or organization
   - Update the repository name if different

3. **Push to GitHub**:
   - The workflows will automatically run on push and pull requests
   - Check the Actions tab in GitHub to view workflow runs

### Local CI Simulation

To simulate CI locally:

```bash
# Run tests like CI does
pytest --cov=. --cov-report=xml --cov-report=term-missing

# Run linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pylint server.py
```

## License

[Add your license here]

## Author

Edward Facundo <edward@telluriancorp.com>
