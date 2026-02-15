# Android Build Server by TellurianCorp

[![Tests](https://github.com/TellurianCorp/android-build-server/actions/workflows/test.yml/badge.svg)](https://github.com/TellurianCorp/android-build-server/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/TellurianCorp/android-build-server/branch/main/graph/badge.svg?token=XSMLPRV9EH)](https://codecov.io/gh/TellurianCorp/android-build-server)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A web-based Android build server that provides a modern interface for building and deploying Android APKs remotely. This server manages Android projects, builds APKs, and can deploy directly to connected devices.

## Features

- <i class="fas fa-globe"></i> **Web-based Interface**: Modern, responsive web UI for managing builds
- <i class="fas fa-cube"></i> **APK Building**: Build debug and release APKs from Android projects
- <i class="fas fa-mobile-alt"></i> **Device Deployment**: Deploy APKs directly to Android devices via ADB
- <i class="fas fa-chart-line"></i> **Build Status**: Real-time build progress and status tracking
- <i class="fas fa-file-alt"></i> **Build Logs**: View detailed build logs for troubleshooting
- <i class="fas fa-shield-alt"></i> **Project Isolation**: Secure project path validation
- <i class="fas fa-bolt"></i> **Async Builds**: Non-blocking build execution with threading

## Requirements

- <i class="fab fa-python"></i> Python 3.6+
- <i class="fab fa-android"></i> Android SDK with platform-tools (for ADB deployment)
- <i class="fas fa-project-diagram"></i> Gradle-based Android projects
- <i class="fas fa-server"></i> Nginx (optional, for reverse proxy)

## Installation

### Quick Start

1. <i class="fas fa-clone"></i> Clone this repository:
```bash
git clone <repository-url>
cd android-build
```

2. <i class="fas fa-download"></i> Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. <i class="fas fa-folder"></i> Ensure your Android projects are located in `/home/projects/` directory. Each project should:
   - Have a `gradlew` executable
   - Be a valid Gradle-based Android project

4. <i class="fas fa-play"></i> Start the server:
```bash
python3 server.py
```

The web interface will be available at `http://localhost:8000`

### Using the Installer Script

<i class="fas fa-cog"></i> Run the interactive installer:
```bash
./install.sh
```

The installer will:
- <i class="fas fa-check-circle"></i> Check for required tools (rsync, ssh, scp, python3)
- <i class="fas fa-sliders-h"></i> Configure remote build settings
- <i class="fas fa-file-code"></i> Set up helper scripts
- <i class="fas fa-server"></i> Start the web server

### Installing as a Systemd Service

<i class="fas fa-server"></i> To run the server as a systemd service (recommended for production):

```bash
sudo ./install-service.sh
```

The installer will:
- <i class="fas fa-file"></i> Create a systemd service file
- <i class="fas fa-user"></i> Configure the service to run as a specific user
- <i class="fas fa-key"></i> Set proper file permissions
- <i class="fas fa-power-off"></i> Enable the service to start on boot
- <i class="fas fa-play-circle"></i> Optionally start the service immediately

**Service Management:**
```bash
# <i class="fas fa-play"></i> Start the service
sudo systemctl start android-build

# <i class="fas fa-stop"></i> Stop the service
sudo systemctl stop android-build

# <i class="fas fa-redo"></i> Restart the service
sudo systemctl restart android-build

# <i class="fas fa-info-circle"></i> Check service status
sudo systemctl status android-build

# <i class="fas fa-file-alt"></i> View logs
sudo journalctl -u android-build -f

# <i class="fas fa-toggle-on"></i> Enable/disable auto-start on boot
sudo systemctl enable android-build
sudo systemctl disable android-build
```

## ⚙️ Configuration

### Project Directory

By default, the server looks for Android projects in `/home/projects/`. Each project directory should:
- Contain a `gradlew` executable
- Be a valid Android Gradle project
- Have the standard Android project structure

### 📱 Device Configuration

To deploy APKs to devices, configure the device address via the web interface or by editing `device.json`:

```json
{
  "address": "192.168.0.148:43419"
}
```

**Note**: `device.json` is git-ignored as it contains deployment-specific configuration.

### 🌐 Nginx Configuration (Optional)

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

### 🌐 Web Interface

1. <i class="fas fa-globe"></i> Open `http://localhost:8000` in your browser
2. <i class="fas fa-folder"></i> Select a project from the dropdown
3. <i class="fas fa-wrench"></i> Choose build type (debug or release)
4. <i class="fas fa-play"></i> Click "Start Build" to begin building
5. <i class="fas fa-chart-line"></i> Monitor build progress in real-time
6. <i class="fas fa-download"></i> Download the APK when the build completes

### 📱 Device Deployment

1. <i class="fas fa-cog"></i> Configure your device address in the web interface
2. <i class="fas fa-plug"></i> Ensure your Android device is connected via ADB (USB or network)
3. <i class="fas fa-cube"></i> Build an APK or use an existing one
4. <i class="fas fa-rocket"></i> Click "Deploy" to install the APK on your device

### 🔧 Configure Project from Local IDE

To configure the device address from your local IDE using curl:

```bash
# Configure device address
curl -X POST http://localhost:8000/api/device \
  -H "Content-Type: application/json" \
  -d '{"address": "192.168.1.20:5555"}'
```

Replace `192.168.1.20:5555` with your actual device IP address and port.

**Example responses:**
- Success: `{"address": "192.168.1.20:5555"}`
- Error: `{"error": "Invalid device address."}`

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

## 📁 Project Structure

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

## 🏗️ Build Process

1. **Preparing**: Validates project and prepares build environment
2. **Building**: Executes Gradle build command
3. **Finding APK**: Locates the generated APK file
4. **Copying**: Copies APK to artifacts directory
5. **Done**: Build complete, APK available for download

## 🚀 Deployment Process

1. **Connecting Device**: Connects to Android device via ADB
2. **Finding APK**: Locates the APK to deploy
3. **Installing APK**: Installs APK on the device
4. **Deployed**: Installation complete

## 🔒 Security Considerations

- Project paths are validated to prevent directory traversal attacks
- Only projects in `/home/projects/` are accessible
- Build commands are executed in isolated project directories
- Device addresses are validated before deployment

## 🔧 Troubleshooting

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

## 🧪 Testing

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

**Coverage Requirements:**
- Minimum coverage threshold: **60%**
- Coverage is enforced in CI/CD pipeline
- Pull requests will be blocked if coverage falls below threshold

Generate coverage report:
```bash
pytest --cov=. --cov-report=html --cov-fail-under=60
```

View the HTML report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Check coverage locally:
```bash
# Run with coverage threshold (will fail if below 60%)
pytest --cov=. --cov-fail-under=60

# Generate detailed coverage report
pytest --cov=. --cov-report=term-missing --cov-report=html
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

## 💻 Development

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

## 🔄 CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment with **mandatory test and coverage requirements** for all submissions.

### Workflows

- **Tests** (`.github/workflows/test.yml`): Runs tests on multiple Python versions (3.9, 3.10, 3.11, 3.12)
  - Executes all unit tests with coverage
  - **Enforces 60% minimum coverage threshold**
  - Uploads coverage reports to Codecov
  - Generates HTML coverage reports as artifacts
  - Runs on push and pull requests
  - **Required for merge**

- **Coverage Gate** (`.github/workflows/coverage-gate.yml`): Enforces coverage requirements
  - Blocks PRs if coverage is below 60%
  - Compares coverage with base branch
  - Posts coverage comments on PRs
  - **Required for merge**

- **PR Checks** (`.github/workflows/pr-checks.yml`): Comprehensive PR validation
  - Runs all tests with coverage threshold
  - Validates test count
  - Runs linting checks
  - **Required for merge**

- **Lint** (`.github/workflows/lint.yml`): Code quality checks
  - Runs flake8 for style and error checking
  - Runs pylint for code analysis
  - Runs on push and pull requests

### Coverage Reports

Coverage reports are automatically generated and uploaded to:
- **Codecov**: [View coverage dashboard](https://codecov.io/gh/TellurianCorp/android-build-server)
- **GitHub Actions Artifacts**: Download HTML reports from workflow runs

### Setting Up CI/CD

1. **Enable Codecov** (optional but recommended):
   - Sign up at [codecov.io](https://codecov.io)
   - Add your repository
   - Update the badge URLs in README.md with your username/organization

2. **Badge URLs** (Already configured):
   - Organization: `TellurianCorp`
   - Repository: `android-build-server`
   - Badges are automatically updated with coverage data

3. **Configure Branch Protection** (Recommended):
   - Go to repository Settings → Branches
   - Add branch protection rule for `main`/`master`
   - Require status checks:
     - `Tests / test (3.12)`
     - `Coverage Gate / enforce-coverage`
     - `PR Checks / test-required`
     - `PR Checks / coverage-required`
   - Require branches to be up to date before merging

4. **Push to GitHub**:
   - The workflows will automatically run on push and pull requests
   - **Pull requests cannot be merged until all checks pass**
   - Check the Actions tab in GitHub to view workflow runs

### PR Submission Requirements

All pull requests must meet these requirements:

✅ **All tests must pass**
✅ **Coverage must be ≥ 60%**
✅ **Coverage must not decrease from base branch**
✅ **Linting must pass**
✅ **No merge conflicts**

The CI/CD pipeline will automatically:
- Run all tests across Python 3.9-3.12
- Check coverage threshold (60% minimum)
- Validate code quality
- Block merge if requirements are not met

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Tellurian Corp

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Author

Edward Facundo <edward@telluriancorp.com>
