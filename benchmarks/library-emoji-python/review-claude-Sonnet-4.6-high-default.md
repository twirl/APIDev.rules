## EmojiKit API Review

Overall, this is a well-structured, thoughtful design. The Unicode-first philosophy is sound and the ABC-based architecture makes the library genuinely composable. Here's a detailed breakdown.

---

### Strengths

**Architecture**
- Six focused ABCs with clear single responsibilities — easy to implement partially or swap out.
- Accepting/returning raw `str` in `EmojiTransformer` rather than `Emoji` objects is a good pipeline-friendly choice.
- The `frozen=True` dataclass for `Emoji` is correct; value objects should be immutable.
- Custom exception hierarchy (`EmojiKitError → UnknownEmojiError`, `RenderError`, etc.) is clean.

**Correctness of domain modeling**
- Grapheme-cluster awareness in `EmojiDetector` (handling ZWJ sequences as single matches) is the right call — most libraries get this wrong.
- `is_fully_qualified` on `Emoji` and handling both qualified/unqualified forms in `by_sequence` shows real Unicode awareness.
- `SkinTone` as an enum with actual code point values (not just names) is practical.

---

### Issues & Suggestions

**`Emoji.codepoints` returns `list[str]`, not `list[int]`**
The property produces `U+XXXX` strings (display format), which is fine for debugging but makes programmatic use awkward. Consider splitting:
```python
@property
def codepoints(self) -> list[int]:
    """Raw ordinal values."""
    return [ord(cp) for cp in self.sequence]

@property
def codepoints_str(self) -> list[str]:
    """Human-readable U+XXXX strings."""
    return [f"U+{ord(cp):04X}" for cp in self.sequence]
```

**`is_modifier_base` and `supports_zwj` have `...` bodies**
These are properties on a `dataclass`, not an ABC — they need real implementations (or at least `raise NotImplementedError`). As-is they silently return `None`, which will cause subtle bugs.

**`EmojiDetector.find_all` return type is inconsistent with the docstring**
The docstring example shows `[Emoji, Emoji]` but the signature returns `list[tuple[int, int, Emoji]]`. The tuple form is more useful, but the module docstring (use-case section) needs updating to match.

**`EmojiAnalyzer.density` denominator is underspecified**
"Unicode word boundaries" is ambiguous — does punctuation count? Does it use `\b` regex, `unicodedata`, or `regex` with `\w+`? This will cause inconsistent implementations. Define it explicitly (e.g. "tokens are sequences matched by `\w+` in Unicode mode").

**`EmojiConverter.to_html_entity` uses `&#xXXXX;` in the docstring but `&#NNN;` in the class docstring**
The class-level example shows `&#169;` (decimal) while the method doc says hex (`&#xXXXX;`). Pick one and be consistent — hex is the better choice for emoji since the code points are large.

**`EmojiTransformer.gender_variant` accepts `gender: str` instead of an enum**
This is the only place a free string is used where an enum would prevent bugs:
```python
class Gender(Enum):
    MAN = "\u2642"
    WOMAN = "\u2640"
```
`"man"` vs `"male"` vs `"Man"` are all plausible inputs and will all silently fail differently.

**`EmojiCatalog.all()` has no guaranteed order**
This is documented, but it means two calls to `all()` on the same catalog could yield different orders, making testing and reproducibility harder. Consider guaranteeing Unicode code-point order as the default.

**`EmojiRenderer` is missing a `supports(sequence)` method**
Without it, callers can't check capability before invoking — they can only try and catch `RenderError`. A `supports(self, sequence: str) -> bool` method would enable graceful fallback chains.

**`keywords` field type annotation**
```python
keywords: tuple[str, ...] = field(default_factory=tuple)
```
`default_factory=tuple` produces an empty `tuple()`, which is correct, but the annotation `tuple[str, ...]` requires Python 3.9+. Worth noting in the module requirements, or use `Tuple[str, ...]` from `typing` for broader compatibility (though `from __future__ import annotations` already defers evaluation, so this is low-priority).

---

### Minor Nits

- `EmojiDetector.split` says "odd-indexed items are emoji" — this should be even-indexed if the string starts with text (as in the `"Hi 👋!"` example, index 0 is `"Hi "`, index 1 is `"👋"`). The description and the example contradict each other; clarify which convention is canonical.
- `EmojiConverter.to_unicode_escape` with `style="u+"` should probably be `style="U+"` (uppercase) since `U+1F600` is the standard Unicode notation.
- No `__version__` or versioning strategy mentioned — worth adding for a public library.
- The `EmojiCatalog` thread-safety guarantee ("effectively immutable once built") should be enforced or at least tested; it's easy to accidentally break in subclasses.

---

### Summary Table

| Area | Rating | Notes |
|---|---|---|
| Architecture | ✅ Strong | Clean ABCs, good separation |
| Unicode correctness | ✅ Strong | ZWJ, qualifiers, modifiers all addressed |
| Type annotations | ⚠️ Mostly good | `codepoints` type, `gender: str` need fixes |
| Docstring consistency | ⚠️ Some gaps | `find_all`, `to_html_entity` have contradictions |
| Completeness | ⚠️ Minor gaps | `supports()` on renderer, `Gender` enum missing |
| Error handling | ✅ Good | Hierarchy is well-designed |

This is a solid foundation. The biggest actionable fixes are the `Gender` enum, the `codepoints` type split, and the `EmojiDetector.split` index contradiction.