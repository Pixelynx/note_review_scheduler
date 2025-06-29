"""Email package for note review scheduler."""

from .service import EmailService, EmailConfig, EmailError
from .templates import EmailTemplateManager, TemplateContext, TemplateError

__all__ = [
    # Service
    "EmailService",
    "EmailConfig", 
    "EmailError",
    # Templates
    "EmailTemplateManager",
    "TemplateContext",
    "TemplateError",
] 