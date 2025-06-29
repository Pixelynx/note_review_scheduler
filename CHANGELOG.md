## Changelog

### [Unreleased]

### [2025-29-06]
#### Added
- **Smart Selection Logic**: Intelligent note selection and content management system
  
  **Content Analysis Engine**:
  - `src/note_reviewer/selection/content_analyzer.py`: Advanced content analysis with SHA-256 hashing
    - `ContentAnalyzer` class with comprehensive content metrics and importance scoring
    - `ContentMetrics` dataclass with content quality scoring (structure, depth, importance)
    - `NoteImportance` enum with CRITICAL, HIGH, MEDIUM, LOW levels
    - Content hashing (SHA-256) for reliable change detection
    - Duplicate content detection and tracking across notes
    - Content freshness calculations with time-based scoring
    - Readability analysis using simplified Flesch Reading Ease formula
    - Importance keyword detection with weighted categorization
    - Structural analysis (headers, code blocks, links, TODO items)
  
  **Selection Algorithm**:
  - `src/note_reviewer/selection/selection_algorithm.py`: Priority-based intelligent note selection
    - `SelectionAlgorithm` class with weighted multi-criteria scoring system
    - `SelectionCriteria` configurable parameters for fine-tuned selection
    - `NoteScore` comprehensive scoring with breakdown by category
    - Priority queue implementation using heapq for efficient top-k selection
    - Weighted scoring: content (30%), freshness (25%), importance (20%), send history (15%), diversity (10%)
    - Email length optimization with character count estimation
    - Directory diversity promotion to avoid monotonous selections
    - Configurable importance level multipliers and filtering criteria
    - Selection history tracking to prevent over-selection
  
  **Email Formatting System**:
  - `src/note_reviewer/selection/email_formatter.py`: Rich HTML email templates with markdown conversion
    - `EmailFormatter` class with intelligent content organization
    - `EmailContent` complete email package with metadata
    - `NoteGroup` categorization system for organized display
    - Beautiful responsive HTML emails with modern CSS styling
    - Markdown-to-HTML conversion supporting headers, links, code blocks, lists
    - Automatic note categorization (Work, Personal, Learning, Ideas, Technical, Planning)
    - Table of contents generation with importance indicators
    - Content preview with configurable word limits
    - Importance-based visual styling and grouping
    - Plain text email generation for accessibility
    - Email statistics and estimated read time calculation
  
  **Advanced Features**:
  - Comprehensive content analysis with 10+ metrics per note
  - Multi-level importance detection with keyword-based classification
  - Duplicate content prevention with SHA-256 fingerprinting
  - Batch size optimization for email length constraints
  - Mobile-responsive email templates with gradient headers
  - Structured logging integration for all selection operations
  - Type-safe implementation with frozen dataclasses
  - Error handling and graceful degradation for missing files
  
  This implementation provides enterprise-grade note selection with military-grade content analysis, beautiful email formatting, and intelligent prioritization algorithms. The system can handle thousands of notes efficiently while maintaining high-quality, personalized email content.

### [2025-28-06]
#### Added
- **Email System & Security Implementation**: Implement comprehensive email functionality and security features
  
  **Email Service Module**:
  - `src/note_reviewer/email/service.py`: Gmail SMTP service with app password authentication
    - `EmailService` class with rate limiting (50 emails/hour default) and retry logic (3 attempts with 5s delay)
    - `EmailConfig` dataclass for secure configuration management
    - Support for both HTML and plain text email formats
    - Optional file attachment functionality for note files
    - Connection testing and rate limit monitoring
    - Comprehensive error handling with custom exceptions (`EmailError`, `RateLimitError`, `AuthenticationError`)
  
  **Email Template System**:
  - `src/note_reviewer/email/templates.py`: Advanced template management with fallback support
    - `EmailTemplateManager` with built-in and custom template support
    - `SimpleTemplateEngine` for variable substitution with nested dictionary access
    - `TemplateContext` for structured email data with note metadata
    - Beautiful responsive HTML templates with modern styling
    - Plain text templates for accessibility
    - Automatic HTML escaping and content preview generation
    - Custom template file creation and management
  
  **Security Implementation**:
  - `src/note_reviewer/security/encryption.py`: Fernet encryption for credential storage
    - `EncryptionManager` using PBKDF2 key derivation (100,000 iterations) with SHA-256
    - Secure file encryption/decryption with salt generation
    - Password verification and secure file deletion
    - Strong password generation utilities
  - `src/note_reviewer/security/credentials.py`: Secure credential management system
    - `CredentialManager` for encrypted configuration storage
    - `EmailCredentials` and `AppConfig` dataclasses with validation
    - Master password-based encryption with setup wizard
    - Configuration backup and restore functionality
  
  **Comprehensive Logging & Error Handling**:
  - `src/note_reviewer/config/logging_config.py`: Advanced structured logging with loguru
    - `StructuredLogger` with performance monitoring and metrics
    - Automatic log rotation (10MB files, 10 retention, ZIP compression)
    - Separate error logging with full context and tracebacks
    - Operation timing and slow operation detection (>1s threshold)
    - Context managers for automatic operation logging
    - Specialized logging for database, email, and security events
  - `src/note_reviewer/config/settings.py`: Centralized configuration management
  
  **Email Templates**:
  - `src/note_reviewer/email/templates/notes_review.html`: Modern responsive HTML template
  - `src/note_reviewer/email/templates/notes_review.text`: Clean plain text template
  
  **Type Safety & Modern Python**:
  - Complete type annotations with modern union syntax (`str | bytes`)
  - Immutable frozen dataclasses for configuration objects
  - Comprehensive input validation and error handling
  - Context managers for resource management
  - Zero implicit `Any` types throughout codebase
  
  This implementation provides enterprise-grade email functionality with military-grade security, comprehensive logging, and beautiful email templates. The system is ready for production use with Gmail SMTP integration.


### [2025-24-06]
#### Added
- **Database Operations**: Added `limit` parameter to `get_notes_never_sent()` function
  - Enables batch processing of notes to prevent overwhelming email sends
  - Maintains backward compatibility with optional parameter `limit: int | None = None`
  - Includes comprehensive input validation and enhanced logging
  - Added detailed documentation with usage examples

### [2025-22-06]
#### Added
- **Database Foundation**: Created SQLite database schema and operations
  - `src/note_reviewer/database/models.py`: Defined `notes` and `send_history` table schemas with proper data models
  - `src/note_reviewer/database/operations.py`: Implemented core database operations with context managers and error handling
    - `initialize_database()`: Creates tables if they don't exist
    - `add_or_update_note()`: Upserts note records based on file_path
    - `get_notes_never_sent()`: Returns notes with no send history
    - `get_notes_not_sent_recently(days)`: Returns notes not sent in X days
    - `record_email_sent()`: Adds send history records
  - `src/note_reviewer/database/__init__.py`: Clean package imports
  - All functions use modern Python practices with type hints, pathlib, and loguru logging
  - **Strict Typing Compliance**: Enhanced all database code to meet strict typing guidelines
    - Complete type annotations with modern union syntax (`int | None` vs `Optional[int]`)
    - Explicit variable type declarations for all assignments
    - Custom typed exceptions (`DatabaseError`, `NoteNotFoundError`)
    - Immutable frozen dataclasses to prevent accidental mutations
    - Input validation with proper error messages
    - Zero implicit `Any` types - complete type coverage
    - `Final` constants and proper generic usage