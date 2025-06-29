# Note Review Scheduler

An intelligent note review scheduler that automatically scans your notes, selects the most relevant ones, and sends them via email on a configurable schedule.

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

### Modern CLI Interface
- **Interactive Setup**: Guided configuration wizard
- **Rich Output**: Beautiful terminal interface with colors and tables
- **Manual Controls**: Send notes on-demand, view statistics
- **Status Monitoring**: Real-time system health reporting

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/pixelynx/note-review-scheduler.git
cd note-review-scheduler

# Install dependencies
pip install -e ".[dev]"
```

### Initial Setup

```bash
# Run the setup wizard
notes setup

# Scan your notes directory
notes scan /path/to/your/notes

# Start the scheduler
notes start
```

### Configuration

The setup wizard will guide you through:

1. **Security Setup**: Master password for encryption
2. **Email Configuration**: Gmail credentials and settings  
3. **Note Directory**: Where your notes are stored
4. **Schedule Settings**: When to send emails

## Usage

### Command Line Interface

```bash
# Setup and configuration
notes setup                    # Initial setup wizard
notes setup --force           # Reconfigure existing setup

# Scheduler control
notes start                    # Start scheduler (foreground)
notes start --daemon          # Start as background service
notes stop                     # Stop running scheduler

# Manual operations
notes scan                     # Scan notes directory
notes send                     # Send email immediately
notes send --preview          # Preview without sending

# Monitoring and info
notes status                   # System health and status
notes stats                    # Usage statistics
notes config --show           # View current configuration
```

### Scheduling Options

- **Daily**: Send at specified time each day
- **Weekly**: Send on specific day of week
- **Custom**: Configurable intervals and conditions

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

### Email Settings

For Gmail integration:
1. Enable 2-factor authentication
2. Generate an app password
3. Use email + app password in setup

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

## Development

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/note_reviewer

# Run specific test category
pytest tests/test_scanner_system.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code  
ruff check src/ tests/

# Type checking
mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Security

- **Encryption**: AES-256 with 100,000 PBKDF2 iterations
- **Key Management**: Master password with secure derivation
- **File Security**: Secure deletion of temporary files
- **Network Security**: TLS for email transmission

## Performance

- **Efficient Scanning**: Incremental updates and caching
- **Rate Limiting**: Configurable email throttling
- **Resource Monitoring**: CPU, memory, and disk tracking
- **Batch Processing**: Optimized database operations

## Troubleshooting

### Common Issues

**Email Authentication Failed**
- Verify Gmail app password is correct
- Check 2-factor authentication is enabled
- Ensure SMTP settings are correct

**Database Errors**
- Check file permissions on database directory
- Verify disk space availability
- Review log files for detailed error messages

**Scan Failures**
- Verify notes directory exists and is readable
- Check file encoding (UTF-8 recommended)
- Review excluded file patterns

### Logging

Logs are written to:
- `logs/app.log` - Application events
- `logs/error.log` - Error details
- Console output for interactive commands

## Support

- **Issues**: GitHub Issues for bug reports
- **Documentation**: See `docs/` directory _(Updating soon)_
- **Examples**: Check `examples/` for sample configurations
