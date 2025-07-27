# Note Review Scheduler

An intelligent note review scheduler that automatically scans your notes, selects the most relevant ones, and sends them via email on a configurable schedule with flexible formatting options.

**Current Status**: **Production Ready** - Full CLI setup wizard implemented with comprehensive email formatting system and robust error handling.

## Table of Contents

- [Features](#features)
  - [Flexible Email Formatting System](#flexible-email-formatting-system)
  - [Multi-Format Note Support](#multi-format-note-support)
  - [Smart Selection Algorithm](#smart-selection-algorithm)
  - [Professional Email System](#professional-email-system)
  - [Enterprise Security](#enterprise-security)
  - [Advanced Monitoring & Scheduling](#advanced-monitoring--scheduling)
  - [Complete CLI Interface](#complete-cli-interface)
- [Installation & Setup](#installation--setup)
  - [Prerequisites](#prerequisites)
  - [Terminal Support](#terminal-support)
  - [Quick Setup](#quick-setup)
  - [Gmail Setup](#gmail-setup)
  - [Interactive Setup Process](#interactive-setup-process)
- [Usage](#usage)
  - [Command Line Interface](#command-line-interface)
  - [Programmatic Usage](#programmatic-usage)
  - [Email Format Examples](#email-format-examples)
  - [Email Attachment Viewing](#email-attachment-viewing)
- [Architecture](#architecture)
  - [Core Components](#core-components)
  - [Email Processing Pipeline](#email-processing-pipeline)
  - [Email Attachment System](#email-attachment-system)
  - [Flexible Formatting System](#flexible-formatting-system)
- [Configuration](#configuration)
  - [Setup Process Validation](#setup-process-validation)
  - [Working Features Status](#working-features-status)
  - [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)
  - [Setup Issues](#setup-issues)
  - [Runtime Issues](#runtime-issues)
  - [Terminal Compatibility](#terminal-compatibility)
- [Development](#development)
  - [Adding New Format Types](#adding-new-format-types)
  - [Contributing](#contributing)
- [Support](#support)

## Features

### Flexible Email Formatting System
- **PLAIN**: Clean text formatting for standard readability
- **BIONIC**: Bold first half of words for focus and enhanced reading speed
- **STYLED**: Rich visual hierarchy with enhanced paragraph styling
- **Intelligent Markdown Cleaning**: Removes formatting while preserving lists and structure
- **Extensible Architecture**: Easy to add new formats (MINIMALIST, HIGH_CONTRAST, DARK_MODE, etc.)

### Multi-Format Note Support
- **Markdown** (.md, .markdown) with comprehensive parsing and cleaning
- **Org-mode** (.org) with tag and link extraction  
- **Plain Text** (.txt) with basic structure detection
- Advanced content analysis and metadata extraction
- **Character-based Preview**: 300-character previews with intelligent word boundary detection

### Smart Selection Algorithm
- **Content Analysis**: Importance scoring, readability metrics
- **Freshness Tracking**: Prioritizes recently modified notes
- **Diversity Scoring**: Ensures varied content in emails
- **Send History**: Avoids sending same notes repeatedly
- **Configurable Selection**: 1-20 notes per email with intelligent scoring

### Professional Email System
- **Rich HTML Templates**: Beautiful, responsive email formatting with mobile support
- **File Attachments**: Full note files attached with original filenames
- **Rate Limiting**: Configurable email sending limits (50/hour default)
- **Retry Logic**: Automatic retry on failures with exponential backoff
- **Gmail Integration**: Secure app password authentication with immediate validation

### Enterprise Security
- **Military-grade Encryption**: AES-256 with PBKDF2 key derivation (100,000 iterations)
- **Secure Credential Storage**: Master password protected configuration
- **Safe File Operations**: Secure deletion and encrypted file handling
- **Input Validation**: Comprehensive validation with retry loops for all user input

### Advanced Monitoring & Scheduling
- **Health Checks**: System resource monitoring with CPU and memory tracking
- **Performance Metrics**: Operation timing and statistics
- **Structured Logging**: Comprehensive event tracking with log rotation
- **Automated Scheduling**: Daily, weekly, hourly, or custom interval scheduling
- **Graceful Shutdown**: Proper signal handling with Ctrl+C confirmation

### Complete CLI Interface
- **Interactive Setup Wizard**: Fully implemented with step-by-step configuration
- **Input Validation**: Robust error handling with retry loops for all inputs
- **Format Selection**: Interactive choice of email formatting styles during setup
- **Immediate Testing**: Gmail credential validation during setup process
- **Status Commands**: Comprehensive system health and configuration display

## Installation & Setup

### Prerequisites

1. **Python 3.9+** required
2. **Gmail Account** with 2-factor authentication enabled
3. **Gmail App Password** (not your regular password)
4. **Terminal Compatibility**: Works with PowerShell, Command Prompt, and Git Bash

### Terminal Support

The application supports all major Windows terminals with enhanced Ctrl+C handling:

- **PowerShell**: Full hidden password input support
- **Command Prompt**: Full hidden password input support  
- **Git Bash/MSYS2**: Uses visible password input with security notices
- **WSL**: Full support via standard Unix tools

**Enhanced Ctrl+C Handling**: Press Ctrl+C then Enter to confirm exit.

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/pixelynx/note-review-scheduler.git
cd note-review-scheduler

# Install dependencies
pip install -e .

# Run the interactive setup wizard
notes setup

# Important: Run initial scan to populate database
notes scan
```

### Notes Directory Configuration

The system supports several ways to configure your notes directory:

1. **Default Locations** (auto-discovered):
   - `notes/` in repository root
   - `docs/` in repository root
   - `wiki/` in repository root
   - `content/` in repository root
   - Custom directory specified during setup

2. **GitHub Actions Configuration**:
   If using GitHub Actions for automated note review:
   - Set `NOTES_DIRECTORY` secret in repository settings
   - Path should be relative to repository root
   - Example: `src/note_reviewer/database/tmp/Study`

3. **Manual Configuration**:
   ```bash
   # View current configuration
   notes config --show

   # Update notes directory
   notes setup --force
   ```

### Gmail Setup

**Required**: Set up Gmail app password before running setup.

1. Go to Google Account settings
2. Enable 2-factor authentication if not already enabled
3. Generate an app password:
   - Go to "Security" → "App passwords"  
   - Select "Mail" as the app
   - Generate password (format: xxxx xxxx xxxx xxxx)
   - Save this password for the setup wizard

### Interactive Setup Process

The setup wizard will guide you through:

1. **Master Password**: Create secure encryption password
2. **Gmail Configuration**: 
   - Gmail address validation
   - App password with immediate testing
   - Display name configuration
3. **Notes Directory**: Path validation with auto-creation option
4. **Schedule Configuration**: Daily email time (HH:MM format)
5. **Email Settings**: Number of notes per email (1-20)
6. **Format Selection**: Choose email formatting style:
   - **PLAIN**: Clean text formatting (default)
   - **BIONIC**: Bold first half of words for ADHD focus
   - **STYLED**: Enhanced visual hierarchy
7. **Initial Scan**: Optional notes directory scanning
8. **Scheduler Launch**: Option to start scheduler immediately

```bash
# Complete setup with wizard
notes setup

# View configuration
notes config --show

# Check system status
notes status

# Start the scheduler
notes start

# Reset configuration if needed
notes reset
```

## Usage

### Command Line Interface

```bash
# Setup and Configuration
notes setup                    # Interactive setup wizard
notes setup --force            # Reconfigure existing setup
notes config --show            # View current configuration
notes reset                    # Reset all configuration
notes status                   # System health and status

# Note Management
notes scan                     # Scan notes directory
notes scan /custom/path        # Scan specific directory
notes send --preview           # Preview next email
notes send --max-notes 5       # Send specific number of notes
notes send --force             # Send even if sent recently

# Scheduler Control
notes start                    # Start scheduler (foreground)
notes start --daemon           # Start as background daemon
notes stop                     # Stop running scheduler

# Statistics and Analytics
notes stats                    # Usage statistics
notes stats --days 7           # Last 7 days statistics
notes stats --detailed         # Detailed analytics
```

### Programmatic Usage

```python
from pathlib import Path
from src.note_reviewer.main import NoteReviewApplication
from src.note_reviewer.selection.text_formatter import EmailFormatType

# Initialize application
config_file = Path("config/credentials.json")
app = NoteReviewApplication(config_file)

if app.initialize("your_master_password"):
    # Manual operations
    app.run_scan()
    app.send_manual_email(max_notes=3, preview_only=True)
    
    # Start scheduler
    app.start_scheduler(daemon_mode=False)  # Foreground
    app.start_scheduler(daemon_mode=True)   # Background
```

### Email Format Examples

#### PLAIN Format
```
Meeting Notes
Words: 156 | 2 days ago | Score: 8.5
--------------------------------------------------
Project kickoff meeting with team leads discussing 
Q4 roadmap and resource allocation priorities...

• Action items for next week
• Budget review scheduled  
• Technical architecture decisions pending
```

#### BIONIC Format  
**Email Preview (300 characters):**
```
Meeting Notes - Words: 156 | 2 days ago | Score: 8.5
Project kickoff meeting with team leads discussing Q4 roadmap 
and resource allocation priorities. Action items for next week...
```

**HTML Attachment (my-notes.html):**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My Notes</title>
    <style>
        /* Bionic reading CSS with enhanced typography */
        .note-content { font-size: 18px; line-height: 1.8; }
        .note-content strong { font-weight: 700; color: #2c3e50; }
    </style>
</head>
<body>
    <div class="container">
        <main class="note-content">
            **Mee**ting **No**tes<br>
            **Pro**ject **kick**off **mee**ting **wi**th **te**am **lea**ds 
            **disc**ussing Q4 **road**map **a**nd **reso**urce **allo**cation...
            <ul>
                <li>**Act**ion **ite**ms **f**or **ne**xt **we**ek</li>
                <li>**Bud**get **rev**iew **sche**duled</li>
            </ul>
        </main>
    </div>
</body>
</html>
```

#### STYLED Format (Enhanced Visual Hierarchy)
**Email Preview (300 characters):**
```
Meeting Notes - Words: 156 | 2 days ago | Score: 8.5
Project kickoff meeting with team leads discussing Q4 roadmap 
and resource allocation priorities. Action items for next week...
```

**HTML Attachment (my-notes.html):**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>My Notes</title>
    <style>
        /* Styled format CSS with enhanced visual hierarchy */
        .note-content { 
            font-size: 16px; line-height: 1.7; color: #2d3748;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            border: 1px solid #e9ecef; border-radius: 8px; padding: 25px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .note-content p { margin-bottom: 15px; color: #34495e; }
        .header-style { 
            font-size: 18px; color: #2c3e50; font-weight: 600;
            border-bottom: 2px solid #3498db; padding-bottom: 8px;
            margin-bottom: 20px; margin-top: 25px; 
        }
        .enhanced-paragraph {
            background-color: #f8f9fa; padding: 15px; border-radius: 6px;
            border-left: 4px solid #e74c3c; margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <main class="note-content">
            <p class="header-style">Meeting Notes</p>
            <p class="enhanced-paragraph">
                Project kickoff meeting with team leads discussing Q4 roadmap 
                and resource allocation priorities.
            </p>
            <ul style="margin: 15px 0; padding-left: 25px; color: #34495e;">
                <li style="margin-bottom: 8px; line-height: 1.6;">Action items for next week</li>
                <li style="margin-bottom: 8px; line-height: 1.6;">Budget review scheduled</li>
            </ul>
        </main>
    </div>
</body>
</html>
```

### Email Attachment Viewing

**Gmail Compatibility Enhancements:**

The system now includes intelligent features to address Gmail's HTML attachment preview limitations:

**Email Content Options:**
- **Embedded Content Mode** (Default): Full formatted notes are embedded directly in the email body for immediate viewing
- **Attachment Mode**: Full notes available as downloadable attachments with format-specific styling  
- **Hybrid Mode**: Both embedded content and attachments for maximum compatibility

**Viewing Experience by Client:**
- **Gmail Mobile**: Perfect rendering of embedded content and HTML attachments
- **Gmail Desktop**: Embedded content displays perfectly, attachments show raw HTML (Gmail limitation)
- **Other Email Clients** (Outlook, Apple Mail): Full support for both embedded content and HTML attachments

**Format-Specific Behavior:**
- **Plain Format**: Always displays correctly across all clients (plain text)
- **Bionic Format**: Embedded content renders perfectly, attachments work best in mobile/browser
- **Styled Format**: Embedded content renders perfectly, attachments work best in mobile/browser

**Recommended Usage:**
1. **Primary**: Use embedded content (automatically enabled) for immediate note access
2. **Secondary**: Download attachments for offline reading or better formatting in browsers
3. **Fallback**: Forward emails to other clients for improved HTML attachment support

**Smart Preview Control:**
- When full content is embedded in email body, note previews are automatically disabled to avoid redundancy
- Cleaner email presentation focusing on full content rather than showing both previews and complete notes
- Intelligent content management for better user experience across all email clients

## Architecture

### Core Components

```
src/note_reviewer/
├── cli.py                 # Complete CLI with interactive setup
├── main.py                # Application orchestration
├── config/                # Configuration and logging
├── database/              # SQLite operations and models
├── email/                 # Email service and templates  
├── scanner/               # File scanning and parsing
├── security/              # Encryption and credentials
├── selection/             # Note selection and formatting
│   ├── text_formatter.py  # Flexible formatting system
│   └── email_formatter.py # Email template integration
├── scheduler/             # Scheduling and monitoring
└── utils/                 # Common utilities
```

### Email Processing Pipeline

1. **File Discovery**: Scanner finds and analyzes note files
2. **Content Analysis**: Metadata extraction and importance scoring
3. **Database Storage**: Notes stored with send history tracking
4. **Selection Algorithm**: Intelligent note scoring and selection
5. **Markdown Cleaning**: Remove formatting while preserving structure
6. **Format Application**: Apply PLAIN, BIONIC, or STYLED formatting
7. **HTML Attachment Generation**: Create complete HTML documents with CSS styling
8. **Email Generation**: Create HTML content with formatted attachments
9. **Delivery**: Gmail SMTP with rate limiting and retry logic

### Email Attachment System

- **Email Preview**: Clean 300-character preview in email body (markdown removed)
- **HTML Attachments**: Complete formatted documents with CSS styling
- **File Conversion**: `.txt` and `.md` files become `.html` attachments when formatted
- **Responsive Design**: Mobile-friendly HTML with proper typography
- **Format Support**: 
  - **PLAIN**: Clean text formatting
  - **BIONIC**: Bold first half of words for ADHD focus (fully implemented)
  - **STYLED**: Enhanced visual hierarchy with gradient backgrounds and professional styling

### Flexible Formatting System

```
Raw Note → Markdown Cleaner → Format Selector → Email Template
    ↓              ↓               ↓              ↓
"# Header       "Header        BIONIC:         Beautiful
**bold**        bold text      "**Hea**der     HTML Email
- list"         - list"        **bo**ld **te**xt  + Attachments
                               <ul><li>**li**st</li></ul>"
```

## Configuration

### Setup Process Validation

The setup wizard validates all inputs with retry loops:

- **Email Format**: Gmail address format with @gmail.com validation
- **Time Format**: HH:MM validation (24-hour format)
- **Directory Access**: Path validation with creation option
- **Number Ranges**: 1-20 notes per email validation
- **Gmail Credentials**: Immediate SMTP connection testing
- **Format Selection**: Interactive choice with clear descriptions

### Working Features Status

| Component | Status | Description |
|-----------|--------|-------------|
| Interactive Setup | Complete | Full wizard with validation and testing |
| File Scanner | Complete | Multi-format parsing with auto-discovery and configurable directories |
| Database Operations | Complete | SQLite with proper schema and send tracking |
| Email System | Complete | Gmail SMTP with attachments and formatting |
| Security | Complete | AES-256 encryption and secure credential storage |
| Selection Algorithm | Complete | Intelligent scoring and diversity selection |
| Flexible Formatting | Complete | PLAIN, BIONIC, STYLED with extensible architecture |
| Scheduler | Complete | Multiple schedule types with GitHub Actions support |
| CLI Interface | Complete | All commands implemented with proper error handling |
| Email Templates | Complete | Mobile-responsive HTML and text templates |
| Monitoring | Complete | Health checks, metrics, and structured logging |
| GitHub Actions | Complete | Automated scheduling with configurable directory support |

### Advanced Configuration

```bash
# Example .env file for development
MASTER_PASSWORD=your_secure_password
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
NOTES_DIRECTORY=/path/to/notes  # Local development
RECIPIENT_EMAIL=recipient@email.com
SCHEDULE_TIME=09:00
NOTES_PER_EMAIL=3
EMAIL_FORMAT_TYPE=bionic

# For GitHub Actions, set these as repository secrets:
# MASTER_PASSWORD
# EMAIL_ADDRESS
# EMAIL_APP_PASSWORD
# NOTES_DIRECTORY (if using custom directory)
```

## Troubleshooting

### Setup Issues

**"Configuration not found" Error**
```bash
# Run the setup wizard
notes setup

# Or reset and reconfigure
notes reset
notes setup

# Important: Always run scan after setup
notes scan
```

**Gmail Authentication Failed**
- Verify Gmail app password format: "xxxx xxxx xxxx xxxx"
- Ensure 2-factor authentication is enabled
- Test credentials during setup - wizard validates immediately

**Format Selection Issues**
- Choose 1-3 during setup for format type
- Default is PLAIN format if selection fails
- Change format by running `notes setup --force`

### Runtime Issues

**Ctrl+C Issues**

*Setup and Scan Commands (Working):*
- Press Ctrl+C then Enter to confirm exit
- Enhanced signal handling prevents accidental shutdown

*Scheduler (`notes start`) - Known Issue:*
- **Ctrl+C confirmation not currently working**
- Use Task Manager (Windows) or `kill` command (Unix) to force stop
- Issue being addressed in upcoming release
- Run in foreground mode for now: avoid `--daemon` flag

**Email Not Sending**
```bash
# Check system status
notes status

# Preview next email
notes send --preview

# Check Gmail rate limits
notes stats
```

**Notes Not Found**
```bash
# Check if notes directory is configured correctly
notes config --show

# Run initial scan to populate database
notes scan

# For GitHub Actions:
# 1. Check NOTES_DIRECTORY secret is set correctly
# 2. Verify directory exists in repository
# 3. Check workflow logs for scanning results

# Verify directory permissions and file formats (.md, .txt, .org)
```

**GitHub Actions Workflow Issues**
- Ensure `NOTES_DIRECTORY` secret is set if using custom directory
- Default auto-discovery looks in standard locations (notes/, docs/, etc.)
- Check workflow logs for scanning results and directory detection
- Manual scan can be triggered with workflow_dispatch

**Scheduler Not Finding Notes**
1. Verify database is populated:
   ```bash
   # Run scan to populate database
   notes scan
   ```
2. Check notes directory configuration:
   ```bash
   # View current settings
   notes config --show
   ```
3. For GitHub Actions:
   - Set `NOTES_DIRECTORY` secret if notes are in custom location
   - Check workflow logs for scanning results
   - Verify notes exist in specified directory

### Terminal Compatibility

| Terminal | Setup Wizard | Password Input | Ctrl+C Support | Status |
|----------|-------------|---------------|----------------|---------|
| PowerShell | Full | Hidden | Enhanced | Recommended |
| Command Prompt | Full | Hidden | Enhanced | Fully Supported |
| Git Bash | Full | Visible* | Enhanced | Supported |
| WSL | Full | Hidden | Enhanced | Fully Supported |

*Password visible during input in Git Bash for compatibility - still secure.

## Development

### Adding New Format Types

```python
# 1. Add to EmailFormatType enum
class EmailFormatType(Enum):
    PLAIN = "plain"
    BIONIC = "bionic" 
    STYLED = "styled"
    MINIMALIST = "minimalist"  # New format

# 2. Add formatting method
@staticmethod
def format_minimalist(text: str) -> str:
    """Apply minimalist formatting."""
    # Implementation here
    pass

# 3. Update format_text method
def format_text(self, text: str) -> str:
    if self.format_type == EmailFormatType.MINIMALIST:
        formatted_text = self.formatter.format_minimalist(text_without_lists)
    # ... existing code
```

### Contributing

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Pull Requests**: Welcome for new formatting styles and improvements
- **Testing**: Comprehensive test coverage for all formatting styles

## Support

**Ready for Production**: All core features implemented and tested
- Complete interactive setup wizard
- Flexible email formatting system  
- Robust error handling and validation
- Comprehensive CLI interface
- Advanced scheduling and monitoring

For support, please use GitHub Issues with:
- Terminal type and OS version
- Complete error messages
- Steps to reproduce issues
- Configuration details (without sensitive data)

### GitHub Actions Configuration

The system can be automated using GitHub Actions with the following considerations:

1. **Timezone Configuration**
   - GitHub Actions uses UTC (Coordinated Universal Time)
   - You need to convert your local time to UTC when setting the schedule
   - Example conversions for New York (ET):
     ```
     Local Time (ET)  |  UTC Time (Workflow Config)
     -----------------|--------------------------
     9:00 AM ET      |  13:00 UTC (EDT) or 14:00 UTC (EST)
     12:00 PM ET     |  16:00 UTC (EDT) or 17:00 UTC (EST)
     3:00 PM ET      |  19:00 UTC (EDT) or 20:00 UTC (EST)
     ```
   - To update the schedule:
     1. Edit `.github/workflows/scheduled-note-review.yml`
     2. Modify the cron expression: `cron: '0 16 * * *'` (for 12 PM EDT)
   - Common timezone offsets:
     ```
     Timezone        | UTC Offset
     ----------------|------------
     Eastern (ET)    | UTC-4 (EDT) / UTC-5 (EST)
     Central (CT)    | UTC-5 (CDT) / UTC-6 (CST)
     Mountain (MT)   | UTC-6 (MDT) / UTC-7 (MST)
     Pacific (PT)    | UTC-7 (PDT) / UTC-8 (PST)
     ```

2. **Directory Configuration**
   - Set `NOTES_DIRECTORY` secret for custom directory location
   - Default auto-discovery of standard directories (notes/, docs/, etc.)

3. **Required Secrets**
   ```
   MASTER_PASSWORD          # Encryption master password
   EMAIL_ADDRESS           # Gmail address
   EMAIL_APP_PASSWORD      # Gmail app password
   NOTES_DIRECTORY        # Optional: Custom notes directory
   MAX_NOTES_PER_EMAIL    # Optional: Maximum notes per email (default: 5)
   ```

4. **Configuration Priority**
   - Manual workflow trigger inputs override repository secrets
   - Repository secrets override default values
   - Default values:
     ```
     MAX_NOTES_PER_EMAIL = 5
     FORCE_SEND = false
     ```

5. **Manual Trigger**
   - Use GitHub Actions UI to trigger workflow manually
   - Available parameters:
     - `max_notes`: Override number of notes to send
     - `force_send`: Send even if notes were recently sent
