"""
emojis — A Python library for working with Unicode emoji.

Design Draft (Abstract Interface)
==================================

Scope & Use Cases
-----------------
This library targets four developer workflows:

1. **Text processing** — detect, extract, strip, or replace emoji in strings.
   Example: sanitising user content, normalising chat messages.

2. **Emoji lookup & metadata** — resolve an emoji by name, code point, or
   keyword and read its Unicode properties (category, version, skin-tone
   variants, ZWJ sequences, etc.).
   Example: building emoji pickers, content moderation, accessibility tooling.

3. **Rendering & presentation** — produce platform-safe representations:
   convert emoji to image URLs, alt-text, HTML entities, or shortcodes.
   Example: cross-platform messaging apps, email renderers, screen-reader
   helpers.

4. **Transformation** — replace shortcodes (:thumbs_up:) with emoji and vice
   versa; apply or strip skin-tone modifiers; normalise ZWJ sequences.
   Example: Slack-like messaging clients, markdown processors.

Design Principles
-----------------
* Abstract classes define the *contract*; concrete classes provide the
  implementation. Callers depend only on the abstract interface.
* Operations are grouped by responsibility area. Each area can be used
  independently — import only what is needed.
* Naming follows Python conventions (snake_case, verb-first for mutating
  operations, noun-first for lookups).
* Errors are subclasses of ``EmojiError`` and encode the recovery action.
* No global mutable state. All stateful helpers are context-manager-friendly.
* Unicode Standard version is explicit on every object that depends on it.

Module Layout
-------------
emojis/
    errors.py          — Exception hierarchy
    models.py          — Emoji, SkinTone, EmojiSequence, SearchResult
    abc/
        detector.py    — EmojiDetector  (text scanning)
        registry.py    — EmojiRegistry  (lookup & metadata)
        renderer.py    — EmojiRenderer  (output formats)
        transformer.py — EmojiTransformer (text transformation)
    shortcodes.py      — ShortcodeMap   (shortcode ↔ emoji mapping)
    version.py         — UnicodeVersion (version model)
"""

from __future__ import annotations

import abc
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional


# ---------------------------------------------------------------------------
# Shared value types
# ---------------------------------------------------------------------------

@unique
class SkinTone(Enum):
    """Fitzpatrick skin-tone modifiers defined by Unicode.

    Values are the Unicode modifier code points (U+1F3FB–U+1F3FF).
    """
    LIGHT        = 0x1F3FB  # Type I–II
    MEDIUM_LIGHT = 0x1F3FC  # Type III
    MEDIUM       = 0x1F3FD  # Type IV
    MEDIUM_DARK  = 0x1F3FE  # Type V
    DARK         = 0x1F3FF  # Type VI


@unique
class EmojiCategory(Enum):
    """Top-level Unicode emoji categories (CLDR v45)."""
    SMILEYS_AND_EMOTION   = "smileys_and_emotion"
    PEOPLE_AND_BODY       = "people_and_body"
    COMPONENT             = "component"
    ANIMALS_AND_NATURE    = "animals_and_nature"
    FOOD_AND_DRINK        = "food_and_drink"
    TRAVEL_AND_PLACES     = "travel_and_places"
    ACTIVITIES            = "activities"
    OBJECTS               = "objects"
    SYMBOLS               = "symbols"
    FLAGS                 = "flags"


@dataclass(frozen=True)
class UnicodeVersion:
    """A specific version of the Unicode Standard.

    Attributes:
        major: Major version number (e.g. 15 for Unicode 15.0).
        minor: Minor version number (e.g. 1 for Unicode 15.1).
    """
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"

    def __lt__(self, other: UnicodeVersion) -> bool:
        return (self.major, self.minor) < (other.major, other.minor)


@dataclass(frozen=True)
class CodePointSequence:
    """An ordered sequence of Unicode code points representing one emoji.

    Attributes:
        code_points: Tuple of integer code points (e.g. (0x1F44D,) for 👍).
    """
    code_points: tuple[int, ...]

    @property
    def character(self) -> str:
        """Return the emoji as a Python string."""
        return "".join(chr(cp) for cp in self.code_points)

    def __str__(self) -> str:
        return self.character

    def __len__(self) -> int:
        return len(self.code_points)


@dataclass(frozen=True)
class Emoji:
    """Immutable descriptor for a single emoji or emoji sequence.

    Attributes:
        sequence:       The canonical code-point sequence.
        cldr_name:      Human-readable CLDR short name (e.g. "thumbs up").
        category:       CLDR top-level category.
        keywords:       CLDR annotation keywords for search (e.g. ["like"]).
        unicode_version: Unicode version that introduced this emoji.
        is_fully_qualified: Whether the sequence includes all recommended
                        variation selectors (VS16).
        has_skin_tone_variants: True when Fitzpatrick modifiers are applicable.
        skin_tone:      The applied skin-tone modifier, if any.
        base_emoji:     The unmodified emoji this was derived from, or None.
    """
    sequence:               CodePointSequence
    cldr_name:              str
    category:               EmojiCategory
    keywords:               tuple[str, ...]
    unicode_version:        UnicodeVersion
    is_fully_qualified:     bool
    has_skin_tone_variants: bool
    skin_tone:              Optional[SkinTone]   = None
    base_emoji:             Optional["Emoji"]    = None

    @property
    def character(self) -> str:
        """Return the emoji character(s) as a Python string."""
        return self.sequence.character

    @property
    def code_points_hex(self) -> str:
        """Return code points as uppercase hex, e.g. '1F44D FE0F'."""
        return " ".join(f"{cp:04X}" for cp in self.sequence.code_points)


@dataclass(frozen=True)
class TextSpan:
    """The position of a single emoji within a source string.

    Attributes:
        start:       Inclusive start index (character position in source).
        end:         Exclusive end index.
        emoji:       The matched ``Emoji`` descriptor.
        source_text: The exact substring that was matched.
    """
    start:       int
    end:         int
    emoji:       Emoji
    source_text: str


@dataclass(frozen=True)
class SearchResult:
    """One item returned from an emoji search query.

    Attributes:
        emoji:          The matched emoji.
        relevance_score: Float in [0.0, 1.0]; higher is more relevant.
        matched_on:     Which field(s) produced the match
                        (e.g. ["cldr_name", "keyword"]).
    """
    emoji:           Emoji
    relevance_score: float
    matched_on:      tuple[str, ...]


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class EmojiError(Exception):
    """Base class for all errors raised by this library.

    All subclasses carry a ``recovery`` attribute that describes the
    recommended action so callers can branch programmatically.
    """
    recovery: str = "no_action"


class EmojiNotFoundError(EmojiError):
    """Raised when a lookup finds no matching emoji.

    Attributes:
        query:    The value that was looked up (name, code point, shortcode).
        recovery: Always ``"check_query_spelling_or_use_search"``.
    """
    recovery = "check_query_spelling_or_use_search"

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(f"No emoji found for query: {query!r}")


class InvalidCodePointError(EmojiError):
    """Raised when a code-point value is outside valid Unicode range or is
    not assigned to an emoji.

    Attributes:
        code_point: The offending integer value.
        recovery:   Always ``"supply_a_valid_unicode_emoji_code_point"``.
    """
    recovery = "supply_a_valid_unicode_emoji_code_point"

    def __init__(self, code_point: int) -> None:
        self.code_point = code_point
        super().__init__(
            f"Code point U+{code_point:04X} is not a valid emoji code point."
        )


class SkinToneNotSupportedError(EmojiError):
    """Raised when a skin-tone variant is requested for an emoji that does
    not support Fitzpatrick modifiers.

    Attributes:
        emoji:    The emoji for which the variant was requested.
        recovery: Always ``"check_emoji.has_skin_tone_variants_before_applying"``.
    """
    recovery = "check_emoji.has_skin_tone_variants_before_applying"

    def __init__(self, emoji: Emoji) -> None:
        self.emoji = emoji
        super().__init__(
            f"Emoji {emoji.character!r} ({emoji.cldr_name!r}) does not support "
            f"skin-tone variants."
        )


class ShortcodeNotFoundError(EmojiError):
    """Raised when a shortcode string has no registered mapping.

    Attributes:
        shortcode: The shortcode that was looked up (e.g. ':shrug:').
        recovery:  Always ``"check_shortcode_spelling_or_list_available"``.
    """
    recovery = "check_shortcode_spelling_or_list_available"

    def __init__(self, shortcode: str) -> None:
        self.shortcode = shortcode
        super().__init__(f"No emoji mapped to shortcode: {shortcode!r}")


class RenderingFormatError(EmojiError):
    """Raised when a renderer cannot produce the requested output format for
    a given emoji (e.g. image not available for the requested vendor/size).

    Attributes:
        emoji:    The emoji that could not be rendered.
        format:   The requested output format name.
        recovery: Always ``"try_a_different_format_or_vendor"``.
    """
    recovery = "try_a_different_format_or_vendor"

    def __init__(self, emoji: Emoji, format: str) -> None:
        self.emoji  = emoji
        self.format = format
        super().__init__(
            f"Cannot render {emoji.character!r} as {format!r}."
        )


# ---------------------------------------------------------------------------
# Abstract: EmojiRegistry
# ---------------------------------------------------------------------------

class EmojiRegistry(abc.ABC):
    """Read-only catalogue of all emoji defined in a Unicode data set.

    The registry is the single source of truth for emoji metadata.
    All lookups are case-insensitive and normalise input whitespace.

    Instantiation
    -------------
    Concrete implementations may load data lazily or eagerly. The caller
    should treat the registry as immutable after construction.

    Thread safety
    -------------
    All read methods must be safe to call concurrently from multiple threads.

    Unicode version
    ---------------
    The ``unicode_version`` property declares which version of the Unicode
    Standard the registry reflects. Callers that need a specific version
    should check this property before use.
    """

    @property
    @abc.abstractmethod
    def unicode_version(self) -> UnicodeVersion:
        """The Unicode Standard version reflected by this registry."""

    @property
    @abc.abstractmethod
    def emoji_count(self) -> int:
        """Total number of fully-qualified emoji in this registry."""

    # ------------------------------------------------------------------
    # Single-emoji lookups
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def lookup_by_character(self, character: str) -> Emoji:
        """Return the ``Emoji`` descriptor for the given character(s).

        The input may be a single emoji character or a multi-character
        ZWJ sequence.  Unqualified sequences (lacking VS16) are
        normalised to their fully-qualified form.

        Args:
            character: One emoji expressed as a Python string.

        Returns:
            The matching ``Emoji`` descriptor.

        Raises:
            EmojiNotFoundError:    If ``character`` is not a known emoji.
            ValueError:            If ``character`` is empty.
        """

    @abc.abstractmethod
    def lookup_by_cldr_name(self, name: str) -> Emoji:
        """Return the emoji whose CLDR short name matches ``name`` exactly.

        The match is case-insensitive.  Spaces and hyphens are treated
        as equivalent (e.g. ``"thumbs-up"`` matches ``"thumbs up"``).

        Args:
            name: CLDR short name, e.g. ``"thumbs up"`` or ``"red heart"``.

        Returns:
            The matching ``Emoji`` descriptor.

        Raises:
            EmojiNotFoundError: If no emoji has that CLDR name.
        """

    @abc.abstractmethod
    def lookup_by_code_point(self, code_point: int) -> Emoji:
        """Return the emoji for a single Unicode code point.

        For multi-code-point sequences (ZWJ, flags, keycap sequences)
        use ``lookup_by_sequence`` instead.

        Args:
            code_point: Integer code point, e.g. ``0x1F44D`` for 👍.

        Returns:
            The matching ``Emoji`` descriptor.

        Raises:
            InvalidCodePointError: If the value is not a valid emoji code
                                   point (out of range or not emoji-assigned).
            EmojiNotFoundError:    If the code point is valid Unicode but not
                                   an emoji.
        """

    @abc.abstractmethod
    def lookup_by_sequence(self, sequence: CodePointSequence) -> Emoji:
        """Return the emoji for a multi-code-point sequence.

        Covers ZWJ sequences (e.g. 👩‍💻), flag sequences (🇺🇸),
        keycap sequences, and skin-tone variants.

        Args:
            sequence: A ``CodePointSequence`` describing the emoji.

        Returns:
            The matching ``Emoji`` descriptor.

        Raises:
            EmojiNotFoundError:    If the sequence is unknown.
            InvalidCodePointError: If any code point in the sequence is
                                   outside valid Unicode range.
        """

    # ------------------------------------------------------------------
    # Skin-tone variants
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_skin_tone_variant(self, emoji: Emoji, tone: SkinTone) -> Emoji:
        """Return the skin-tone variant of ``emoji`` for the given ``tone``.

        Args:
            emoji: The base (unmodified) emoji.
            tone:  The Fitzpatrick modifier to apply.

        Returns:
            A new ``Emoji`` whose ``skin_tone`` is ``tone`` and
            ``base_emoji`` is the original ``emoji``.

        Raises:
            SkinToneNotSupportedError: If ``emoji.has_skin_tone_variants``
                                       is False.
            EmojiNotFoundError:        If the variant is not in the data set
                                       (should not happen for well-formed input).
        """

    @abc.abstractmethod
    def list_skin_tone_variants(self, emoji: Emoji) -> tuple[Emoji, ...]:
        """Return all Fitzpatrick skin-tone variants for ``emoji``.

        The returned tuple contains exactly five entries (one per
        ``SkinTone`` value) in the order defined by ``SkinTone``.

        Args:
            emoji: The base (unmodified) emoji.

        Returns:
            A tuple of five ``Emoji`` instances.

        Raises:
            SkinToneNotSupportedError: If ``emoji.has_skin_tone_variants``
                                       is False.
        """

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int = 20,
        categories: Optional[Sequence[EmojiCategory]] = None,
        unicode_version_max: Optional[UnicodeVersion] = None,
    ) -> tuple[SearchResult, ...]:
        """Search for emoji by name, keyword, or description.

        Results are ranked by relevance.  An empty query returns an
        empty tuple — it is never an error.

        Args:
            query:               Free-text search string (1–200 characters).
            max_results:         Maximum entries to return (1–100, default 20).
            categories:          Restrict results to these categories.
                                 ``None`` means all categories.
            unicode_version_max: Exclude emoji introduced after this version.
                                 Useful for targeting older rendering environments.

        Returns:
            A tuple of up to ``max_results`` ``SearchResult`` instances,
            ordered by descending ``relevance_score``.

        Raises:
            ValueError: If ``max_results`` is outside [1, 100].
        """

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def iterate_by_category(
        self,
        category: EmojiCategory,
    ) -> Iterator[Emoji]:
        """Iterate over all fully-qualified emoji in ``category``.

        The iteration order follows Unicode ordering within the category.
        The iterator is lazy; the registry does not materialise all items
        into a list unless the caller does so explicitly.

        Args:
            category: The ``EmojiCategory`` to iterate.

        Yields:
            ``Emoji`` instances in Unicode order.
        """

    @abc.abstractmethod
    def iterate_all(self) -> Iterator[Emoji]:
        """Iterate over every fully-qualified emoji in the registry.

        Order follows Unicode category ordering, then position within
        each category.

        Yields:
            ``Emoji`` instances in Unicode order.
        """


# ---------------------------------------------------------------------------
# Abstract: EmojiDetector
# ---------------------------------------------------------------------------

class EmojiDetector(abc.ABC):
    """Scans text to find, count, and classify emoji occurrences.

    All methods treat their input as a read-only string and never mutate it.
    Multi-codepoint sequences (ZWJ, flags, skin-tone variants) are matched
    as a single unit.

    The detector resolves emoji metadata through the ``EmojiRegistry``
    supplied at construction time.
    """

    @property
    @abc.abstractmethod
    def registry(self) -> EmojiRegistry:
        """The ``EmojiRegistry`` used for resolving metadata."""

    # ------------------------------------------------------------------
    # Presence checks
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def contains_emoji(self, text: str) -> bool:
        """Return ``True`` if ``text`` contains at least one emoji.

        This is a short-circuit scan and does not enumerate all matches.

        Args:
            text: Input string of any length.

        Returns:
            ``True`` when any emoji is found; ``False`` otherwise.
        """

    @abc.abstractmethod
    def is_only_emoji(self, text: str) -> bool:
        """Return ``True`` when ``text`` consists entirely of emoji and
        optional whitespace — no plain text characters.

        Useful for applying large-emoji rendering in chat interfaces.

        Args:
            text: Input string to test.

        Returns:
            ``True`` when every non-whitespace character belongs to an emoji.
        """

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def find_all(self, text: str) -> tuple[TextSpan, ...]:
        """Return all emoji occurrences in ``text`` in left-to-right order.

        Overlapping sequences are not possible in well-formed Unicode text;
        each code point appears in at most one span.

        Args:
            text: Source string to scan.

        Returns:
            A tuple of ``TextSpan`` instances, each describing one match.
            Returns an empty tuple when no emoji are found.
        """

    @abc.abstractmethod
    def extract_unique(self, text: str) -> frozenset[Emoji]:
        """Return the set of distinct emoji present in ``text``.

        Skin-tone variants are treated as distinct from their base emoji.

        Args:
            text: Source string to scan.

        Returns:
            A ``frozenset`` of unique ``Emoji`` instances.
        """

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def count_occurrences(self, text: str) -> int:
        """Return the total number of emoji occurrences in ``text``.

        The same emoji appearing twice is counted twice.

        Args:
            text: Source string to scan.

        Returns:
            Non-negative integer occurrence count.
        """

    @abc.abstractmethod
    def count_unique(self, text: str) -> int:
        """Return the number of *distinct* emoji present in ``text``.

        Equivalent to ``len(extract_unique(text))``.

        Args:
            text: Source string to scan.

        Returns:
            Non-negative integer distinct-emoji count.
        """

    # ------------------------------------------------------------------
    # Category checks
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def filter_by_category(
        self,
        text: str,
        category: EmojiCategory,
    ) -> tuple[TextSpan, ...]:
        """Return only the spans whose emoji belong to ``category``.

        Args:
            text:     Source string to scan.
            category: The ``EmojiCategory`` to keep.

        Returns:
            A filtered subset of what ``find_all`` would return.
        """


# ---------------------------------------------------------------------------
# Abstract: EmojiTransformer
# ---------------------------------------------------------------------------

class EmojiTransformer(abc.ABC):
    """Transforms strings that contain emoji or emoji shortcodes.

    All methods return a *new* string and never mutate the input.
    Methods that accept shortcodes require a ``ShortcodeMap`` to be
    registered (see ``ShortcodeMap`` below).
    """

    @property
    @abc.abstractmethod
    def registry(self) -> EmojiRegistry:
        """The ``EmojiRegistry`` used for resolving metadata."""

    # ------------------------------------------------------------------
    # Removal & stripping
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def strip_emoji(self, text: str) -> str:
        """Remove all emoji from ``text`` and return the result.

        Whitespace that surrounded removed emoji is *not* collapsed.
        Use ``strip_emoji_and_collapse_whitespace`` when that is needed.

        Args:
            text: Source string.

        Returns:
            String with all emoji removed.
        """

    @abc.abstractmethod
    def strip_emoji_and_collapse_whitespace(self, text: str) -> str:
        """Remove all emoji from ``text`` and collapse runs of internal
        whitespace (spaces, tabs) that result from removal to a single
        space.  Leading and trailing whitespace is stripped.

        Args:
            text: Source string.

        Returns:
            Normalised string without emoji and with collapsed whitespace.
        """

    # ------------------------------------------------------------------
    # Replacement
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def replace_emoji(self, text: str, replacement: str) -> str:
        """Replace every emoji in ``text`` with ``replacement``.

        Args:
            text:        Source string.
            replacement: The string to substitute for each emoji.
                         May itself contain emoji.

        Returns:
            String with each emoji occurrence replaced.
        """

    @abc.abstractmethod
    def replace_emoji_with_cldr_names(self, text: str) -> str:
        """Replace each emoji with its CLDR short name in square brackets.

        Example: ``"I ❤️ Python"`` → ``"I [red heart] Python"``.

        Useful for plain-text fallbacks and basic accessibility.

        Args:
            text: Source string.

        Returns:
            String with emoji replaced by bracketed CLDR names.
        """

    # ------------------------------------------------------------------
    # Skin-tone operations
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def apply_skin_tone(self, text: str, tone: SkinTone) -> str:
        """Apply ``tone`` to every skin-tone-capable emoji in ``text``.

        Emoji that do not support Fitzpatrick modifiers are left unchanged.

        Args:
            text: Source string.
            tone: The ``SkinTone`` to apply.

        Returns:
            String with tone modifiers applied to eligible emoji.
        """

    @abc.abstractmethod
    def strip_skin_tones(self, text: str) -> str:
        """Remove all Fitzpatrick skin-tone modifiers from ``text``,
        returning each modified emoji to its base (yellow) form.

        Args:
            text: Source string.

        Returns:
            String with all tone modifiers removed.
        """

    # ------------------------------------------------------------------
    # Shortcode conversion
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def shortcodes_to_emoji(
        self,
        text: str,
        shortcode_map: "ShortcodeMap",
    ) -> str:
        """Replace shortcode tokens (e.g. ``:thumbs_up:``) with emoji.

        Only tokens present in ``shortcode_map`` are replaced.  Unknown
        tokens are left as-is so callers can apply multiple maps
        sequentially without data loss.

        Args:
            text:          Source string containing zero or more shortcodes.
            shortcode_map: The mapping to use for resolution.

        Returns:
            String with recognised shortcodes replaced by emoji characters.
        """

    @abc.abstractmethod
    def emoji_to_shortcodes(
        self,
        text: str,
        shortcode_map: "ShortcodeMap",
    ) -> str:
        """Replace emoji characters with their shortcode representations.

        When an emoji has multiple shortcodes registered in
        ``shortcode_map``, the canonical (first-registered) shortcode is
        used.  Emoji absent from the map are left unchanged.

        Args:
            text:          Source string.
            shortcode_map: The mapping to use for resolution.

        Returns:
            String with emoji replaced by their shortcode tokens.
        """


# ---------------------------------------------------------------------------
# Abstract: EmojiRenderer
# ---------------------------------------------------------------------------

class EmojiRenderer(abc.ABC):
    """Converts ``Emoji`` objects into various output representations.

    Renderers do not mutate the ``Emoji`` descriptor; they produce new
    output strings or URLs.  Output formats that require external assets
    (images) may return ``None`` when assets are unavailable, rather than
    raising, unless the ``strict`` flag is set to ``True`` at construction.
    """

    @property
    @abc.abstractmethod
    def strict(self) -> bool:
        """When ``True``, missing assets raise ``RenderingFormatError``
        instead of returning ``None``."""

    # ------------------------------------------------------------------
    # Text / HTML formats
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def to_html_entity(self, emoji: Emoji) -> str:
        """Return an HTML numeric character reference for ``emoji``.

        For multi-code-point sequences each code point is rendered as its
        own ``&#xNNNN;`` entity.

        Example: 👍 → ``"&#x1F44D;&#xFE0F;"``

        Args:
            emoji: The emoji to encode.

        Returns:
            HTML entity string, safe for use inside HTML text content.
        """

    @abc.abstractmethod
    def to_alt_text(self, emoji: Emoji) -> str:
        """Return a concise, human-readable description of ``emoji``
        suitable for use as image ``alt`` text or an ``aria-label``.

        The description is derived from the CLDR short name and
        skin-tone modifier when applicable.

        Example: 👍🏽 → ``"thumbs up: medium skin tone"``

        Args:
            emoji: The emoji to describe.

        Returns:
            Plain-text description string (English).
        """

    @abc.abstractmethod
    def to_unicode_escape(self, emoji: Emoji) -> str:
        """Return Python-style Unicode escape notation for ``emoji``.

        Example: 👍 → ``"\\U0001F44D\\uFE0F"``

        Args:
            emoji: The emoji to encode.

        Returns:
            String of ``\\UNNNNNNNN`` or ``\\uNNNN`` escape sequences.
        """

    # ------------------------------------------------------------------
    # Image rendering
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def to_image_url(
        self,
        emoji: Emoji,
        *,
        size_px: int = 64,
        vendor: str = "twemoji",
    ) -> Optional[str]:
        """Return a URL to a rasterised image of ``emoji``.

        The URL points to a public CDN asset for the specified vendor.
        Returns ``None`` (or raises ``RenderingFormatError`` when
        ``self.strict`` is ``True``) if no image is available for the
        requested combination of emoji, size, and vendor.

        Args:
            emoji:    The emoji to render.
            size_px:  Requested image dimension in pixels.  Supported
                      sizes are vendor-dependent; callers should not rely
                      on the image being exactly ``size_px`` pixels.
                      Allowed range: 8–512.
            vendor:   Image set to use.  Supported values depend on the
                      concrete implementation; ``"twemoji"`` is the
                      universal default.

        Returns:
            HTTPS URL string, or ``None`` when unavailable (non-strict mode).

        Raises:
            RenderingFormatError: In strict mode when no image is available.
            ValueError:           If ``size_px`` is outside [8, 512].
        """

    @abc.abstractmethod
    def to_html_image_tag(
        self,
        emoji: Emoji,
        *,
        size_px: int = 64,
        vendor: str = "twemoji",
        css_class: Optional[str] = None,
    ) -> Optional[str]:
        """Return a self-contained HTML ``<img>`` tag for ``emoji``.

        The tag includes an ``alt`` attribute derived from ``to_alt_text``
        and a ``role="img"`` for accessibility.

        Args:
            emoji:     The emoji to render.
            size_px:   Image dimension hint (see ``to_image_url``).
            vendor:    Image set to use (see ``to_image_url``).
            css_class: Optional value for the ``class`` attribute.

        Returns:
            HTML string, or ``None`` when the image URL is unavailable
            (non-strict mode).

        Raises:
            RenderingFormatError: In strict mode when no image is available.
        """


# ---------------------------------------------------------------------------
# Abstract: ShortcodeMap
# ---------------------------------------------------------------------------

class ShortcodeMap(abc.ABC):
    """Bidirectional mapping between emoji shortcode tokens and ``Emoji``
    objects.

    A *shortcode* is a named token delimited by colons, e.g. ``:heart:``.
    Multiple shortcodes may map to the same emoji; the first one registered
    is the *canonical* shortcode for the reverse mapping.

    ShortcodeMap implementations are immutable after construction.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """A short identifier for this shortcode set (e.g. ``"slack"``).

        Used in diagnostics and error messages.
        """

    @property
    @abc.abstractmethod
    def shortcode_count(self) -> int:
        """Total number of shortcode tokens registered in this map."""

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def lookup_emoji(self, shortcode: str) -> Emoji:
        """Return the ``Emoji`` for a shortcode token.

        The lookup is case-insensitive.  The surrounding colons are
        optional — both ``:heart:`` and ``heart`` are accepted.

        Args:
            shortcode: The shortcode token to look up.

        Returns:
            The mapped ``Emoji``.

        Raises:
            ShortcodeNotFoundError: If the shortcode is not registered.
        """

    @abc.abstractmethod
    def lookup_canonical_shortcode(self, emoji: Emoji) -> str:
        """Return the canonical shortcode token for ``emoji``.

        The canonical shortcode is the first one registered for the emoji.
        The returned string always includes surrounding colons.

        Args:
            emoji: The ``Emoji`` whose shortcode is requested.

        Returns:
            Shortcode string including colons, e.g. ``:thumbs_up:``.

        Raises:
            ShortcodeNotFoundError: If the emoji has no registered shortcode
                                    in this map.
        """

    @abc.abstractmethod
    def lookup_all_shortcodes(self, emoji: Emoji) -> tuple[str, ...]:
        """Return *all* shortcode tokens registered for ``emoji``.

        The first entry in the tuple is the canonical shortcode.

        Args:
            emoji: The ``Emoji`` to query.

        Returns:
            Non-empty tuple of shortcode strings (with colons).
            Returns an empty tuple — not an error — when the emoji has
            no registered shortcodes in this map.
        """

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def iterate_shortcodes(self) -> Iterator[tuple[str, Emoji]]:
        """Iterate over every ``(shortcode, emoji)`` pair in registration
        order.

        When multiple shortcodes map to the same emoji, each pair is
        yielded separately.

        Yields:
            Tuples of ``(shortcode_with_colons, emoji)``.
        """