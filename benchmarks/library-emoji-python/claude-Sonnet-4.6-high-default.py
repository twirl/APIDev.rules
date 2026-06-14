"""
emojikit — A Python library for working with emoji.

This module defines the abstract interface for the library. No implementation
is provided here; concrete classes should subclass the ABCs and fill in the
annotated methods.

Design goals
------------
* Unicode-first: every emoji is treated as a Unicode code-point sequence, so
  the library works correctly with ZWJ sequences, skin-tone modifiers,
  flag sequences, and keycap sequences.
* Composable: every subsystem (lookup, rendering, analysis, …) is an
  independent ABC that can be mixed in or replaced.
* Framework-agnostic: the library makes no assumption about the runtime
  (web, CLI, mobile). Rendering is pluggable.
* Typed: public APIs carry full PEP 484 annotations so IDEs and type-checkers
  can catch mistakes before runtime.

Modules (one ABC per file in a real package)
--------------------------------------------
  emoji_lib.core        — Emoji value object and Catalog
  emoji_lib.search      — Text-based search and fuzzy matching
  emoji_lib.transform   — Modifier, variant, and ZWJ composition
  emoji_lib.analysis    — Sentiment, density, and frequency tools
  emoji_lib.convert     — Cross-format serialisation (shortcodes, HTML, …)
  emoji_lib.render      — Pluggable image / text rendering

Use-case overview
-----------------
1. Lookup & discovery
     catalog.by_name("sparkles")
     catalog.search("face smiling")
     catalog.by_category(EmojiCategory.TRAVEL)

2. Text processing
     detector.find_all("I love 🐍 and 🦄")      → [Emoji, Emoji]
     detector.strip("Clean ✨ text ✨")           → "Clean  text "
     detector.replace_with_text("Hi 👋")         → "Hi :wave:"

3. Transformation / composition
     transformer.apply_skin_tone("👍", SkinTone.MEDIUM_DARK)  → "👍🏾"
     transformer.zwj_sequence("👨", "👩", "👧")               → "👨‍👩‍👧"
     transformer.text_variation("☀")                          → "☀️"

4. Sentiment & analysis
     analyzer.sentiment("Best day ever 🎉🥳🎊")   → SentimentResult(score=0.92)
     analyzer.density("Hi 👋, I'm fine 😊.")      → 0.4          # 2 emoji / 5 tokens
     analyzer.frequency(corpus)                    → Counter({...})

5. Serialisation / conversion
     converter.to_shortcode("🎸")          → ":guitar:"
     converter.from_shortcode(":guitar:")  → "🎸"
     converter.to_html_entity("©")         → "&#169;"
     converter.to_image_url("😀")          → "https://cdn.example/1f600.svg"

6. Rendering
     renderer.to_png("🌍", size=64)        → bytes
     renderer.to_svg("🌍")                 → str   (SVG markup)
     renderer.to_ascii("🔥")              → "[fire]"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator, Optional, Sequence


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EmojiCategory(Enum):
    """Top-level Unicode CLDR emoji categories."""

    SMILEYS_AND_EMOTION = auto()
    PEOPLE_AND_BODY = auto()
    ANIMALS_AND_NATURE = auto()
    FOOD_AND_DRINK = auto()
    TRAVEL_AND_PLACES = auto()
    ACTIVITIES = auto()
    OBJECTS = auto()
    SYMBOLS = auto()
    FLAGS = auto()
    COMPONENT = auto()
    UNKNOWN = auto()


class SkinTone(Enum):
    """Fitzpatrick skin-tone modifier code points (Unicode 8.0+)."""

    LIGHT = "\U0001F3FB"            # 🏻
    MEDIUM_LIGHT = "\U0001F3FC"     # 🏼
    MEDIUM = "\U0001F3FD"           # 🏽
    MEDIUM_DARK = "\U0001F3FE"      # 🏾
    DARK = "\U0001F3FF"             # 🏿


class HairStyle(Enum):
    """Hair-component code points used in ZWJ sequences."""

    RED = "\U0001F9B0"
    CURLY = "\U0001F9B1"
    BALD = "\U0001F9B2"
    WHITE = "\U0001F9B3"


# ---------------------------------------------------------------------------
# Core value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Emoji:
    """
    Immutable value object representing a single logical emoji.

    An *emoji* in this model is a Unicode grapheme cluster — it may consist
    of multiple code points (e.g. ZWJ sequences, skin-tone + base, flag
    sequences) but is perceived by a user as a single glyph.

    Attributes
    ----------
    sequence:
        The raw Unicode string (one or more code points) that represents
        this emoji.  Must be a non-empty string.
    name:
        The official Unicode CLDR English name, e.g. ``"grinning face"``.
    cldr_short_name:
        Short CLDR annotation name used in search, e.g. ``"grin"``.
    category:
        Top-level CLDR category.
    subcategory:
        CLDR subcategory string, e.g. ``"face-smiling"``.
    unicode_version:
        The Unicode standard version that introduced this emoji,
        e.g. ``"6.0"``.
    keywords:
        CLDR keyword annotations, e.g. ``["face", "grin", "smile"]``.
    is_fully_qualified:
        ``True`` when the sequence ends with the VS-16 variation selector
        (U+FE0F) making it explicitly emoji-style.
    """

    sequence: str
    name: str
    cldr_short_name: str
    category: EmojiCategory
    subcategory: str
    unicode_version: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    is_fully_qualified: bool = True

    # ------------------------------------------------------------------
    # Convenience properties

    @property
    def codepoints(self) -> list[str]:
        """Return each code point as a ``U+XXXX`` hex string."""
        return [f"U+{ord(cp):04X}" for cp in self.sequence]

    @property
    def is_modifier_base(self) -> bool:
        """Return ``True`` if this emoji accepts a Fitzpatrick modifier."""
        ...

    @property
    def supports_zwj(self) -> bool:
        """Return ``True`` if this emoji can participate in ZWJ sequences."""
        ...


@dataclass
class SentimentResult:
    """
    Output of :meth:`EmojiAnalyzer.sentiment`.

    Attributes
    ----------
    score:
        Normalised polarity score in ``[-1.0, +1.0]``.
        Positive values indicate positive sentiment.
    label:
        Human-readable label: ``"positive"``, ``"neutral"``, or
        ``"negative"``.
    contributing_emoji:
        The emoji instances that drove the result, paired with their
        individual scores.
    confidence:
        Model confidence in ``[0.0, 1.0]``.  May be ``None`` when the
        underlying method does not produce a confidence estimate.
    """

    score: float
    label: str
    contributing_emoji: list[tuple[Emoji, float]] = field(default_factory=list)
    confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# ABC 1 — EmojiCatalog
# ---------------------------------------------------------------------------


class EmojiCatalog(ABC):
    """
    Read-only registry of all known emoji.

    The catalog is the authoritative source of :class:`Emoji` instances.
    Concrete implementations may load data from the bundled Unicode CLDR
    JSON files, a SQLite database, a remote API, or a hand-crafted dict.

    Thread-safety
    ~~~~~~~~~~~~~
    Implementations must be safe to call from multiple threads after
    construction (i.e. the catalog must be effectively immutable once built).

    Example
    -------
    ::

        catalog = JsonEmojiCatalog.from_package_data()

        sparkles = catalog.by_sequence("✨")
        print(sparkles.name)              # "sparkles"

        results = catalog.search("smiling face")
        for e in results:
            print(e.sequence, e.name)
    """

    @abstractmethod
    def by_sequence(self, sequence: str) -> Optional[Emoji]:
        """
        Look up an emoji by its exact Unicode sequence.

        Parameters
        ----------
        sequence:
            A Unicode string of one or more code points, e.g. ``"👋🏽"``.

        Returns
        -------
        :class:`Emoji` if found, ``None`` otherwise.  Implementations
        should handle both fully-qualified and minimally-qualified
        sequences (i.e. with or without U+FE0F).
        """

    @abstractmethod
    def by_name(self, name: str, *, exact: bool = False) -> list[Emoji]:
        """
        Find emoji whose CLDR name matches *name*.

        Parameters
        ----------
        name:
            Search string, e.g. ``"sparkles"`` or ``"smiling face"``.
        exact:
            When ``True``, only return emoji whose :attr:`Emoji.name` or
            :attr:`Emoji.cldr_short_name` matches *name* exactly
            (case-insensitive). When ``False`` (default), return all emoji
            whose name *contains* the search string.

        Returns
        -------
        A list of matching :class:`Emoji` objects, possibly empty.
        """

    @abstractmethod
    def by_category(self, category: EmojiCategory) -> list[Emoji]:
        """
        Return every emoji in *category*, in Unicode code-point order.

        Parameters
        ----------
        category:
            A :class:`EmojiCategory` member.
        """

    @abstractmethod
    def by_keyword(self, keyword: str) -> list[Emoji]:
        """
        Return emoji annotated with *keyword* in the CLDR keyword list.

        Parameters
        ----------
        keyword:
            A single annotation word, e.g. ``"fire"`` or ``"celebration"``.
        """

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        fuzzy: bool = True,
    ) -> list[Emoji]:
        """
        Full-text search across names, short-names, and keywords.

        Parameters
        ----------
        query:
            Free-form search string, e.g. ``"laughing cry"`` or
            ``"red heart"``.
        limit:
            Maximum number of results to return (default 20).
        fuzzy:
            When ``True``, tolerate minor spelling variations using an
            edit-distance heuristic. When ``False``, require all query
            tokens to appear verbatim in the emoji metadata.

        Returns
        -------
        A ranked list of :class:`Emoji` objects (best match first).
        """

    @abstractmethod
    def all(self) -> Iterator[Emoji]:
        """
        Iterate over every emoji in the catalog.

        The iteration order is not guaranteed; callers should sort if
        a deterministic order is required.
        """

    @abstractmethod
    def __len__(self) -> int:
        """Return the total number of emoji in the catalog."""


# ---------------------------------------------------------------------------
# ABC 2 — EmojiDetector
# ---------------------------------------------------------------------------


class EmojiDetector(ABC):
    """
    Scan plain-text strings for emoji occurrences.

    The detector operates on *grapheme clusters*, not individual code points,
    so a family ZWJ sequence like 👨‍👩‍👧 is reported as a single match.

    Example
    -------
    ::

        text = "I love 🐍 and building 🚀 things 🎉"
        detector = UnicodeEmojiDetector(catalog)

        found = detector.find_all(text)
        # [Emoji("🐍"), Emoji("🚀"), Emoji("🎉")]

        clean = detector.strip(text)
        # "I love  and building  things "

        shortcodes = detector.replace(text, lambda e: f":{e.cldr_short_name}:")
        # "I love :snake: and building :rocket: things :party_popper:"
    """

    @abstractmethod
    def contains(self, text: str) -> bool:
        """
        Return ``True`` if *text* contains at least one emoji.

        Parameters
        ----------
        text:
            Any Unicode string.
        """

    @abstractmethod
    def find_all(self, text: str) -> list[tuple[int, int, Emoji]]:
        """
        Locate every emoji in *text*.

        Parameters
        ----------
        text:
            The string to scan.

        Returns
        -------
        A list of ``(start, end, emoji)`` tuples where *start* and *end*
        are character indices into *text* (``text[start:end] == emoji.sequence``).
        Results are returned in left-to-right order.
        """

    @abstractmethod
    def strip(self, text: str, *, replacement: str = "") -> str:
        """
        Remove all emoji from *text*.

        Parameters
        ----------
        text:
            The source string.
        replacement:
            String to insert in place of each emoji.  Defaults to an empty
            string (simple removal). Use ``" "`` to preserve word spacing.
        """

    @abstractmethod
    def replace(
        self,
        text: str,
        replacer,   # Callable[[Emoji], str]
    ) -> str:
        """
        Replace each emoji in *text* with the string returned by *replacer*.

        Parameters
        ----------
        text:
            The source string.
        replacer:
            A callable ``(Emoji) -> str`` invoked for every match.  The
            return value is inserted in place of the original emoji sequence.

        Example
        -------
        ::

            detector.replace("Hi 👋", lambda e: e.name.upper())
            # "Hi WAVING HAND"
        """

    @abstractmethod
    def split(self, text: str) -> list[str]:
        """
        Split *text* into alternating non-emoji and emoji segments.

        Returns
        -------
        A list where odd-indexed items are emoji sequences and even-indexed
        items are plain-text runs (which may be empty strings). Useful for
        rendering pipelines that need to handle each segment differently.

        Example
        -------
        ``"Hi 👋!"``  →  ``["Hi ", "👋", "!"]``
        """


# ---------------------------------------------------------------------------
# ABC 3 — EmojiTransformer
# ---------------------------------------------------------------------------


class EmojiTransformer(ABC):
    """
    Produce new emoji sequences from existing ones.

    Transformations cover Fitzpatrick skin-tone modifiers, Unicode variation
    selectors (text vs. emoji presentation), hair-component ZWJ sequences,
    and arbitrary ZWJ composition.

    All methods accept and return raw Unicode strings (not :class:`Emoji`
    objects) so they can be composed in pipelines without repeated catalog
    lookups.

    Example
    -------
    ::

        t = UnicodeEmojiTransformer()

        t.apply_skin_tone("👍", SkinTone.DARK)           → "👍🏿"
        t.remove_skin_tone("👍🏿")                        → "👍"
        t.apply_hair_style("🧑", HairStyle.CURLY)        → "🧑‍🦱"
        t.to_emoji_presentation("☀")                     → "☀️"
        t.to_text_presentation("☀️")                     → "☀︎"
        t.zwj_sequence("👨", "🍳")                       → "👨‍🍳"
    """

    @abstractmethod
    def apply_skin_tone(self, sequence: str, tone: SkinTone) -> str:
        """
        Insert a Fitzpatrick modifier into *sequence*.

        Parameters
        ----------
        sequence:
            A modifier-base emoji (e.g. ``"👋"``).
        tone:
            The desired :class:`SkinTone`.

        Returns
        -------
        The modified sequence, or *sequence* unchanged if it is not a valid
        modifier base.

        Raises
        ------
        ValueError
            If *sequence* is not a recognised modifier base.
        """

    @abstractmethod
    def remove_skin_tone(self, sequence: str) -> str:
        """
        Strip any Fitzpatrick modifier from *sequence*.

        Returns
        -------
        The base emoji without a modifier, or *sequence* unchanged if it
        carries no modifier.
        """

    @abstractmethod
    def apply_hair_style(self, sequence: str, style: HairStyle) -> str:
        """
        Build a hair-component ZWJ sequence from *sequence*.

        Parameters
        ----------
        sequence:
            A person emoji that supports hair components (e.g. ``"🧑"``).
        style:
            The desired :class:`HairStyle` component.

        Raises
        ------
        ValueError
            If *sequence* does not support hair ZWJ sequences.
        """

    @abstractmethod
    def to_emoji_presentation(self, sequence: str) -> str:
        """
        Force *sequence* into emoji (coloured) presentation.

        Appends U+FE0F (VS-16) if the sequence is not already
        fully-qualified and supports emoji presentation.
        """

    @abstractmethod
    def to_text_presentation(self, sequence: str) -> str:
        """
        Force *sequence* into text (monochrome) presentation.

        Appends U+FE0E (VS-15) and strips any existing VS-16.
        """

    @abstractmethod
    def zwj_sequence(self, *sequences: str) -> str:
        """
        Join two or more emoji sequences with U+200D (ZWJ).

        Parameters
        ----------
        *sequences:
            Two or more emoji Unicode strings. Order is significant.

        Returns
        -------
        A single string with each sequence joined by ZWJ.

        Raises
        ------
        ValueError
            If fewer than two sequences are provided.
        """

    @abstractmethod
    def gender_variant(self, sequence: str, *, gender: str) -> str:
        """
        Return a gender-explicit ZWJ variant of *sequence*.

        Parameters
        ----------
        sequence:
            A gender-neutral person emoji (e.g. ``"🧑‍💻"``).
        gender:
            Either ``"man"`` (♂, U+2642) or ``"woman"`` (♀, U+2640).

        Returns
        -------
        The gender-explicit sequence, or *sequence* unchanged if no variant
        exists.
        """


# ---------------------------------------------------------------------------
# ABC 4 — EmojiAnalyzer
# ---------------------------------------------------------------------------


class EmojiAnalyzer(ABC):
    """
    Measure and interpret emoji usage in text.

    Use this component for sentiment scoring, readability metrics, corpus
    frequency analysis, and per-emoji statistics.

    Example
    -------
    ::

        analyzer = RuleBasedEmojiAnalyzer(catalog)

        result = analyzer.sentiment("So excited 🎉🥳🎊")
        print(result.score)          # 0.85
        print(result.label)          # "positive"

        print(analyzer.density("Hi 👋, nice to meet you 😊."))   # 0.28
    """

    @abstractmethod
    def sentiment(self, text: str) -> SentimentResult:
        """
        Estimate the sentiment polarity of the emoji content in *text*.

        The score reflects only the contribution of emoji; implementations
        that want to combine with lexical sentiment should do so at a higher
        level.

        Parameters
        ----------
        text:
            Any Unicode string that may or may not contain emoji.

        Returns
        -------
        A :class:`SentimentResult`. When *text* contains no emoji the score
        is ``0.0`` and the label is ``"neutral"``.
        """

    @abstractmethod
    def density(self, text: str) -> float:
        """
        Compute the ratio of emoji tokens to total word tokens in *text*.

        The denominator counts Unicode word boundaries, not raw characters.

        Returns
        -------
        A float in ``[0.0, 1.0]``.  Returns ``0.0`` for empty strings.
        """

    @abstractmethod
    def frequency(self, texts: Sequence[str]) -> Counter[str]:
        """
        Count how often each emoji sequence appears across *texts*.

        Parameters
        ----------
        texts:
            An iterable of Unicode strings (e.g. a list of social-media posts).

        Returns
        -------
        A :class:`collections.Counter` keyed by raw emoji sequence strings,
        sorted by count descending.
        """

    @abstractmethod
    def top_n(
        self,
        texts: Sequence[str],
        n: int = 10,
    ) -> list[tuple[Emoji, int]]:
        """
        Return the *n* most frequently used emoji across *texts*.

        Parameters
        ----------
        texts:
            Corpus to analyse.
        n:
            How many results to return (default 10).

        Returns
        -------
        A list of ``(Emoji, count)`` pairs, ranked by count descending.
        Emoji with no entry in the catalog are skipped.
        """

    @abstractmethod
    def co_occurrence(
        self,
        texts: Sequence[str],
        *,
        window: int = 1,
    ) -> dict[tuple[str, str], int]:
        """
        Build a symmetric co-occurrence matrix for emoji pairs in *texts*.

        Parameters
        ----------
        texts:
            Corpus to analyse.
        window:
            Maximum distance (in emoji positions within the same message)
            for two emoji to be counted as co-occurring. Default is ``1``
            (adjacent emoji only).

        Returns
        -------
        A dict mapping ``(seq_a, seq_b)`` pairs (with ``seq_a < seq_b``
        lexicographically) to co-occurrence counts.
        """


# ---------------------------------------------------------------------------
# ABC 5 — EmojiConverter
# ---------------------------------------------------------------------------


class EmojiConverter(ABC):
    """
    Serialise and deserialise emoji across representation formats.

    Supported formats
    -----------------
    * **Shortcodes** — ``:shortcode:`` syntax as used by GitHub, Slack,
      Discord, etc. Implementations may support multiple platform dialects.
    * **HTML entities** — numeric character references (``&#x1F600;``).
    * **Unicode escapes** — Python-style ``\\U0001F600`` or JS-style
      ``\\uD83D\\uDE00`` (surrogate-pair encoding).
    * **Image URLs** — CDN URLs for Twemoji, Noto Emoji, or OpenMoji.

    Example
    -------
    ::

        c = MultiDialectEmojiConverter(catalog)

        c.to_shortcode("🎸")                    → ":guitar:"
        c.from_shortcode(":guitar:")            → "🎸"
        c.to_html_entity("©")                   → "&#169;"
        c.to_unicode_escape("😀")               → "\\U0001F600"
        c.to_image_url("😀", dialect="twemoji") → "https://..."
    """

    @abstractmethod
    def to_shortcode(
        self,
        sequence: str,
        *,
        dialect: str = "github",
    ) -> Optional[str]:
        """
        Convert a Unicode emoji sequence to a shortcode string.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        dialect:
            Shortcode dialect to use. Built-in options should include at
            least ``"github"`` and ``"slack"``. Implementations may extend
            this list.

        Returns
        -------
        The shortcode (including surrounding colons), or ``None`` if no
        shortcode exists for *sequence* in the given dialect.
        """

    @abstractmethod
    def from_shortcode(
        self,
        shortcode: str,
        *,
        dialect: str = "github",
    ) -> Optional[str]:
        """
        Convert a shortcode string to a Unicode emoji sequence.

        Parameters
        ----------
        shortcode:
            A shortcode with or without surrounding colons,
            e.g. ``":guitar:"`` or ``"guitar"``.
        dialect:
            Shortcode dialect to use (see :meth:`to_shortcode`).

        Returns
        -------
        The Unicode sequence, or ``None`` if the shortcode is unknown.
        """

    @abstractmethod
    def replace_shortcodes(self, text: str, *, dialect: str = "github") -> str:
        """
        Replace all shortcodes in *text* with their emoji equivalents.

        Parameters
        ----------
        text:
            A string that may contain ``:shortcode:`` tokens mixed with
            plain text.
        dialect:
            Shortcode dialect to use (see :meth:`to_shortcode`).

        Returns
        -------
        *text* with every recognised shortcode replaced by its Unicode
        sequence. Unrecognised shortcodes are left as-is.
        """

    @abstractmethod
    def to_html_entity(self, sequence: str) -> str:
        """
        Encode *sequence* as numeric HTML character references.

        Each code point is encoded as ``&#xXXXX;``.  Useful when embedding
        emoji in HTML contexts that don't support raw Unicode reliably.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        """

    @abstractmethod
    def to_unicode_escape(self, sequence: str, *, style: str = "python") -> str:
        """
        Render *sequence* as Unicode escape sequences.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        style:
            Escape style: ``"python"`` (``\\U0001F600``),
            ``"js"`` (surrogate pairs, ``\\uD83D\\uDE00``), or
            ``"u+"`` (``U+1F600``). Default ``"python"``.
        """

    @abstractmethod
    def to_image_url(
        self,
        sequence: str,
        *,
        dialect: str = "twemoji",
        size: int = 72,
    ) -> Optional[str]:
        """
        Return a CDN URL for the image asset representing *sequence*.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        dialect:
            Image set to target. Built-in options should include at least
            ``"twemoji"``, ``"noto"``, and ``"openmoji"``.
        size:
            Nominal pixel size hint (not all CDNs honour this).

        Returns
        -------
        A URL string, or ``None`` if no asset is available for *sequence*
        in the given dialect.
        """


# ---------------------------------------------------------------------------
# ABC 6 — EmojiRenderer
# ---------------------------------------------------------------------------


class EmojiRenderer(ABC):
    """
    Render emoji as raster images, SVG, or ASCII fallback text.

    Implementations wrap an underlying font or image-asset library
    (e.g. Pillow + NotoColorEmoji, or a bundled SVG sprite set).

    All methods raise :class:`RenderError` when rendering cannot be
    completed (e.g. unsupported emoji, missing font).

    Example
    -------
    ::

        renderer = NotoEmojiRenderer(font_path="/usr/share/fonts/noto/")

        png_bytes = renderer.to_png("🌍", size=128)
        with open("earth.png", "wb") as f:
            f.write(png_bytes)

        svg_markup = renderer.to_svg("🌍")
        fallback   = renderer.to_ascii("🔥")    # "[fire]"
    """

    @abstractmethod
    def to_png(self, sequence: str, *, size: int = 72) -> bytes:
        """
        Render *sequence* as a PNG image.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        size:
            Output image size in pixels (width == height).  Default 72.

        Returns
        -------
        Raw PNG bytes.

        Raises
        ------
        RenderError
            If the emoji cannot be rendered with the current renderer.
        """

    @abstractmethod
    def to_svg(self, sequence: str) -> str:
        """
        Render *sequence* as an SVG string.

        Returns
        -------
        A self-contained SVG document as a string.

        Raises
        ------
        RenderError
            If no SVG asset is available for *sequence*.
        """

    @abstractmethod
    def to_ascii(self, sequence: str) -> str:
        """
        Return an ASCII / plain-text fallback representation of *sequence*.

        The format is ``[<cldr_short_name>]``, e.g. ``"[fire]"`` for 🔥.
        This is used when rendering to a terminal or environment that
        does not support Unicode emoji.

        Parameters
        ----------
        sequence:
            A single emoji Unicode string.
        """

    @abstractmethod
    def to_sprite_sheet(
        self,
        sequences: Sequence[str],
        *,
        size: int = 72,
        columns: int = 10,
    ) -> bytes:
        """
        Composite multiple emoji into a single PNG sprite sheet.

        Parameters
        ----------
        sequences:
            Ordered list of emoji Unicode strings to render.
        size:
            Individual cell size in pixels.
        columns:
            Number of emoji per row in the output image.

        Returns
        -------
        Raw PNG bytes of the sprite sheet.
        """


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EmojiKitError(Exception):
    """Base exception for all emojikit errors."""


class UnknownEmojiError(EmojiKitError):
    """Raised when an emoji sequence is not found in the catalog."""

    def __init__(self, sequence: str) -> None:
        self.sequence = sequence
        super().__init__(f"No emoji found for sequence: {sequence!r}")


class RenderError(EmojiKitError):
    """Raised when an :class:`EmojiRenderer` cannot render a sequence."""

    def __init__(self, sequence: str, reason: str = "") -> None:
        self.sequence = sequence
        msg = f"Cannot render {sequence!r}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class UnsupportedTransformError(EmojiKitError):
    """
    Raised by :class:`EmojiTransformer` when a requested transformation is
    not valid for the given emoji (e.g. applying a skin tone to an object).
    """

    def __init__(self, sequence: str, transform: str) -> None:
        self.sequence = sequence
        self.transform = transform
        super().__init__(
            f"Transform {transform!r} is not supported for sequence {sequence!r}"
        )