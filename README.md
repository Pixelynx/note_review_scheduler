# Note Review Scheduler

An intelligent note review scheduler that automatically scans your notes, selects the most relevant ones, and sends them via email on a configurable schedule.

**Current Status**: This project has a robust backend implementation but requires manual setup. The CLI setup wizard is not yet implemented.

## Features

### Multi-Format Note Support
- **Markdown** (.md, .markdown) with full parsing
- **Org-mode** (.org) with tag and link extraction  
- **Plain Text** (.txt) with basic structure detection
- Advanced content analysis and metadata extraction

### Smart Selection Algorithm
- **Content Analysis**: Importance scoring, readability metrics
- **Freshness Tracking**: Prioritizes recently modified notes
- **Diversity Scoring**: Ensures varied content in emails
- **Send History**: Avoids sending same notes repeatedly

### Professional Email System
- **Rich HTML Templates**: Beautiful, responsive email formatting
- **Rate Limiting**: Configurable email sending limits
- **Retry Logic**: Automatic retry on failures
- **Gmail Integration**: App password authentication

### Enterprise Security
- **Military-grade Encryption**: AES-256 with PBKDF2 key derivation
- **Secure Credential Storage**: Master password protected
- **Safe File Operations**: Secure deletion and handling

### Advanced Monitoring
- **Health Checks**: System resource monitoring
- **Performance Metrics**: Operation timing and statistics
- **Structured Logging**: Comprehensive event tracking
- **Backup System**: Automated database backups

### CLI Interface Status
- **Backend**: Fully implemented and functional
- **CLI Commands**: Basic structure exists but setup wizard needs manual configuration
- **Manual Controls**: Core functionality works when properly configured

## Installation & Setup

### Prerequisites

1. **Python 3.9+** required
2. **Gmail Account** with 2-factor authentication enabled
3. **Gmail App Password** (not your regular password)
4. **Terminal Compatibility**: Works with PowerShell, Command Prompt, and Git Bash

### Terminal Support

The application now supports all major Windows terminals:

- **PowerShell**: Full hidden password input support
- **Command Prompt**: Full hidden password input support  
- **Git Bash/MSYS2**: Uses visible password input (prevents hanging)
- **WSL**: Full support via standard Unix tools

**Git Bash Note**: Password input will be visible while typing in Git Bash terminals. This is normal and your password remains secure.

### Installation

```bash
# Clone the repository
git clone https://github.com/pixelynx/note-review-scheduler.git
cd note-review-scheduler

# Install dependencies
pip install -e .                    # Using pyproject.toml
```

### Gmail Setup

**Required**: Set up Gmail app password before configuration.

1. Go to Google Account settings
2. Enable 2-factor authentication
3. Generate an app password:
   - Go to "Security" → "App passwords"
   - Create a key name and generate password
   - Save this password (you'll need it for setup)

### Manual Configuration

Since the setup wizard is not yet implemented, you need to configure manually:

#### Option 1: Using the Setup Script

```bash
# Set environment variables
export MASTER_PASSWORD="your_secure_master_password"
export EMAIL_ADDRESS="your_email@gmail.com"
export EMAIL_APP_PASSWORD="your_gmail_app_password"
export NOTES_DIRECTORY="/path/to/your/notes"

# Run setup script
python scripts/setup_github_credentials.py
```

#### Option 2: Programmatic Setup

```python
from pathlib import Path
from src.note_reviewer.security.credentials import CredentialManager

# Setup credentials
config_file = Path("config/credentials.json")
master_password = "your_secure_master_password"

manager = CredentialManager.setup_wizard(
    config_file=config_file,
    master_password=master_password,
    gmail_username="your_email@gmail.com",
    gmail_app_password="your_gmail_app_password",
    recipient_email="recipient@email.com",
    notes_directory="/path/to/your/notes",
    from_name="Your Name"
)
```

## Usage

### Command Line Interface

**Note**: Some CLI commands are not fully implemented yet.

```bash
# Basic operations (working)
python -m src.note_reviewer.cli setup
python -m src.note_reviewer.cli scan /path/to/notes    # Scan notes
python -m src.note_reviewer.cli status                 # System status
python -m src.note_reviewer.cli config --show          # View configuration

# Planned commands (not fully implemented)
notes setup                    # Setup wizard (placeholder)
notes start                    # Start scheduler 
notes send                     # Send email manually
```

### Programmatic Usage

```python
from src.note_reviewer.main import NoteReviewApplication

# Initialize application
app = NoteReviewApplication()
if app.initialize("your_master_password"):
    # Run operations
    app.run_scan()
    app.send_manual_email(max_notes=3, preview_only=True)
    app.start_scheduler()
```

### Working Features

[x] **File Scanning**: Comprehensive note discovery and analysis  
[x] **Database Operations**: Note storage and send history tracking  
[x] **Email Service**: Gmail SMTP with templates and rate limiting  
[x] **Security**: Encrypted credential storage  
[x] **Selection Algorithm**: Intelligent note prioritization  
[x] **Scheduler Backend**: Configurable scheduling system  

[-] **Partial Implementation**: CLI setup wizard, some CLI commands  
[] **Not Working**: Automatic setup wizard, daemon mode  

## Architecture

### Core Components

```
src/note_reviewer/
├── cli.py                 # Command line interface
├── config/                # Configuration and logging
├── database/              # SQLite operations and models
├── email/                 # Email service and templates
├── scanner/               # File scanning and parsing
├── security/              # Encryption and credentials
├── selection/             # Note selection algorithms
├── scheduler/             # Scheduling and monitoring
└── utils/                 # Common utilities
```

### Data Flow

1. **Scanner** discovers and analyzes note files
2. **Database** stores metadata and send history
3. **Selection Algorithm** chooses optimal notes
4. **Email Formatter** creates rich HTML content
5. **Email Service** delivers to recipients
6. **Monitor** tracks system health and metrics

## Configuration

### Required Settings

- **Master Password**: Secure password for encryption
- **Gmail Credentials**: Username and app password
- **Notes Directory**: Path to your notes folder
- **Recipient Email**: Where to send note reviews
- **Schedule**: When to send emails

### File Format Support

| Format | Extensions | Features |
|--------|------------|----------|
| Markdown | .md, .markdown | Headers, links, code blocks, YAML frontmatter |
| Org-mode | .org | Headers, tags, TODO items, links |
| Plain Text | .txt, .text | Basic structure detection |

### Advanced Features

- **Tag Extraction**: `#hashtags`, `@mentions`, YAML tags
- **Link Validation**: HTTP status checking (optional)
- **Content Summarization**: Automatic excerpts
- **Duplicate Detection**: SHA-256 content hashing

## Development Status

### Implemented Components

| Component | Status | Description |
|-----------|--------|-------------|
| File Scanner | Complete | Multi-format parsing with metadata extraction |
| Database | Complete | SQLite with proper schema and operations |
| Email Service | Complete | Gmail SMTP with rate limiting |
| Security | Complete | AES-256 encryption and credential management |
| Selection Algorithm | Complete | Intelligent note scoring and selection |
| Scheduler | Complete | Background scheduling with multiple types |
| CLI Backend | Complete | Core functionality implemented |
| CLI Interface | Partial | Commands exist but setup wizard incomplete |
| Email Templates | Complete | HTML and text templates ready |

### Known Issues

1. **Setup Wizard**: CLI setup command is placeholder
2. **Entry Points**: Package installation needs refinement  
3. **Documentation**: Some examples reference unimplemented features

### Next Development Steps

1. Implement interactive setup wizard in CLI
2. Fix package entry points and installation
3. Add daemon mode for background operation
4. Complete remaining CLI command implementations
5. Add configuration validation and migration

## Troubleshooting

### Terminal & Setup Issues

**Git Bash Hanging or Not Responding**
- Fixed in latest version - password input now uses visible mode in Git Bash
- Use Ctrl+C followed by Enter to safely exit during setup
- Passwords are still secure even when visible during input

**Ctrl+C Not Working**
- Press Ctrl+C then hit Enter to confirm exit
- For immediate termination, press Ctrl+C twice quickly
- This prevents accidental process termination during configuration

**"Configuration not found" Error**
- Run manual setup using scripts or programmatic method
- Ensure config/credentials.json exists and is accessible

**Gmail Authentication Failed**
- Verify Gmail app password is correct (not regular password)
- Check 2-factor authentication is enabled
- Ensure username is full Gmail address

**CLI Commands Not Working**
- Many CLI commands are placeholders - use programmatic interface
- Check Python path includes src/ directory
- Use full module path: `python -m src.note_reviewer.cli`

### Terminal Compatibility

| Terminal | Password Input | Ctrl+C Support | Status |
|----------|---------------|----------------|---------|
| PowerShell | Hidden | Full | Fully Supported |
| Command Prompt | Hidden | Full | Fully Supported |
| Git Bash | Visible | Confirmation Required | Supported |
| WSL | Hidden | Full | Fully Supported |

## Support

- **Issues**: GitHub Issues for bug reports
- **Status**: This is a development version - expect incomplete CLI features
- **Contributing**: CLI implementation help needed

**Ready for Use**: Backend components, programmatic interface  
**Needs Work**: CLI setup wizard, package installation
