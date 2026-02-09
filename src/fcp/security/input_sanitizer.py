"""Input sanitization to prevent prompt injection attacks.

CRITICAL: This module prevents prompt injection attacks by sanitizing
user-provided input before including it in AI prompts.

Vulnerabilities prevented:
- Prompt injection (CVSS 8.6): Malicious instructions in user input
- Data exfiltration: Prompts designed to leak system instructions

Unicode bypass protections:
- Zero-width character removal (U+200B, U+200C, U+200D, U+2060, etc.)
- Unicode normalization (NFC) before pattern matching
- Whitespace variant normalization
- Bidirectional text control character removal
"""

import re
import unicodedata

# Maximum lengths for different input types
MAX_SEARCH_QUERY_LENGTH = 500
MAX_NOTES_LENGTH = 2000
MAX_VENUE_LENGTH = 200
MAX_DISH_NAME_LENGTH = 200


# Patterns that indicate potential prompt injection
INJECTION_PATTERNS = [
    # Common injection attempts
    r"ignore\s+(previous|above|all)\s+(instructions|prompts?)",
    r"disregard\s+(previous|above|all)",
    r"forget\s+(everything|all|previous)",
    r"new\s+instructions?:",
    r"system\s*:",
    r"<\s*system\s*>",
    r"\[\s*system\s*\]",
    r"assistant\s*:",
    r"<\s*assistant\s*>",
    r"\[\s*assistant\s*\]",
    # Attempts to manipulate output format
    r"respond\s+(only\s+)?with",
    r"output\s+(only\s+)?:",
    r"return\s+(only\s+)?:",
    r"print\s+(only\s+)?:",
    # Attempts to access internal info
    r"(reveal|show|display|print)\s+(your|the)\s+(prompt|instructions|system)",
    r"what\s+(are|is)\s+your\s+(prompt|instructions|system)",
]

# Compiled regex for efficiency
_injection_regex = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# Zero-width and invisible characters that should be removed
# These can be inserted between letters to bypass regex patterns
ZERO_WIDTH_CHARS = {
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u2060",  # Word joiner
    "\u2061",  # Function application
    "\u2062",  # Invisible times
    "\u2063",  # Invisible separator
    "\u2064",  # Invisible plus
    "\ufeff",  # Byte order mark (zero-width no-break space)
}

# Bidirectional text control characters that can manipulate display
BIDI_CONTROL_CHARS = {
    "\u200e",  # Left-to-right mark
    "\u200f",  # Right-to-left mark
    "\u202a",  # Left-to-right embedding
    "\u202b",  # Right-to-left embedding
    "\u202c",  # Pop directional formatting
    "\u202d",  # Left-to-right override
    "\u202e",  # Right-to-left override
    "\u2066",  # Left-to-right isolate
    "\u2067",  # Right-to-left isolate
    "\u2068",  # First strong isolate
    "\u2069",  # Pop directional isolate
}

# Unicode whitespace characters that should be normalized to regular space
UNICODE_WHITESPACE = {
    "\u00a0",  # Non-breaking space
    "\u2000",  # En quad
    "\u2001",  # Em quad
    "\u2002",  # En space
    "\u2003",  # Em space
    "\u2004",  # Three-per-em space
    "\u2005",  # Four-per-em space
    "\u2006",  # Six-per-em space
    "\u2007",  # Figure space
    "\u2008",  # Punctuation space
    "\u2009",  # Thin space
    "\u200a",  # Hair space
    "\u2028",  # Line separator
    "\u2029",  # Paragraph separator
    "\u202f",  # Narrow no-break space
    "\u205f",  # Medium mathematical space
    "\u3000",  # Ideographic space
}


def _normalize_unicode(text: str) -> str:
    """
    Normalize Unicode text to prevent bypass attacks.

    Applies:
    1. NFC normalization (canonical composition)
    2. Zero-width character removal
    3. Bidirectional control character removal
    4. Whitespace variant normalization

    Args:
        text: The text to normalize

    Returns:
        Normalized text
    """
    # Apply NFC normalization first (composes characters into canonical form)
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width characters (can be inserted between letters to bypass regex)
    for char in ZERO_WIDTH_CHARS:
        text = text.replace(char, "")

    # Remove bidirectional control characters (can manipulate text display)
    for char in BIDI_CONTROL_CHARS:
        text = text.replace(char, "")

    # Normalize Unicode whitespace to regular space
    for char in UNICODE_WHITESPACE:
        text = text.replace(char, " ")

    return text


def sanitize_user_input(
    text: str | None,
    max_length: int = 1000,
    field_name: str = "input",
    strip_injection_patterns: bool = True,
) -> str:
    """
    Sanitize user input for safe inclusion in AI prompts.

    Args:
        text: The user-provided text
        max_length: Maximum allowed length
        field_name: Name of the field (for error messages)
        strip_injection_patterns: Whether to remove detected injection patterns

    Returns:
        Sanitized text
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Strip whitespace
    text = text.strip()

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]

    # Remove null bytes and other control characters (except newline, tab)
    text = "".join(char for char in text if char == "\n" or char == "\t" or (ord(char) >= 32 and ord(char) != 127))

    # Normalize Unicode to prevent bypass attacks (zero-width chars, bidi, etc.)
    text = _normalize_unicode(text)

    # Optionally strip injection patterns
    if strip_injection_patterns and _injection_regex.search(text):
        # Replace detected patterns with [REDACTED]
        text = _injection_regex.sub("[REDACTED]", text)

    return text


def sanitize_search_query(query: str | None) -> str:
    """
    Sanitize a search query for safe use in prompts.

    Args:
        query: The search query

    Returns:
        Sanitized query
    """
    return sanitize_user_input(
        query,
        max_length=MAX_SEARCH_QUERY_LENGTH,
        field_name="search query",
    )


def sanitize_notes(notes: str | None) -> str:
    """
    Sanitize user notes for safe use in prompts.

    Args:
        notes: The user notes

    Returns:
        Sanitized notes
    """
    return sanitize_user_input(
        notes,
        max_length=MAX_NOTES_LENGTH,
        field_name="notes",
    )


def sanitize_venue_name(venue: str | None) -> str:
    """
    Sanitize a venue name for safe use in prompts.

    Args:
        venue: The venue name

    Returns:
        Sanitized venue name
    """
    return sanitize_user_input(
        venue,
        max_length=MAX_VENUE_LENGTH,
        field_name="venue name",
    )


def sanitize_dish_name(dish_name: str | None) -> str:
    """
    Sanitize a dish name for safe use in prompts.

    Args:
        dish_name: The dish name

    Returns:
        Sanitized dish name
    """
    return sanitize_user_input(
        dish_name,
        max_length=MAX_DISH_NAME_LENGTH,
        field_name="dish name",
    )


def escape_for_prompt(text: str) -> str:
    """
    Escape text for safe inclusion in a prompt template.

    This adds additional escaping for text that will be inserted into
    prompt templates using .format() or f-strings.

    Args:
        text: The text to escape

    Returns:
        Escaped text
    """
    return text.replace("{", "{{").replace("}", "}}")


def check_for_injection(text: str) -> bool:
    """
    Check if text contains potential prompt injection patterns.

    Applies Unicode normalization before checking to prevent bypass attacks
    using zero-width characters, homoglyphs, or other Unicode tricks.

    Args:
        text: The text to check

    Returns:
        True if injection patterns detected, False otherwise
    """
    if not text:
        return False
    # Normalize Unicode before checking to catch bypass attempts
    normalized = _normalize_unicode(text)
    return bool(_injection_regex.search(normalized))
