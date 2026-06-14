# API Review: emojikit

## Confirmed Defects

**1. `EmojiDetector.find_all` return type contradicts the module docstring's promised return value.**
The class docstring example shows `find_all` returning `[Emoji, Emoji]` (a flat list of `Emoji`), but the method signature returns `list[tuple[int, int, Emoji]]`. This is a real ambiguity for implementers and a trap for consumers reading the top-level docstring vs. the method docstring. Fix: update the module-level docstring's example to match the `(start, end, emoji)` tuple form, since the tuple form is more useful and should be the canonical contract.

**2. `EmojiTransformer` methods silently no-op on invalid input in some places and raise in others, with no consistent rule.**
- `apply_skin_tone`: docstring says it both raises `ValueError` *and* "returns sequence unchanged if not a valid modifier base" — these are contradictory outcomes for the same condition.
- `remove_skin_tone`: returns unchanged silently (no error path).
- `apply_hair_style`: raises `ValueError`.
- `to_emoji_presentation`/`to_text_presentation`: silently no-op for unsupported sequences.
- `gender_variant`: returns unchanged silently.

A consumer cannot predict whether an invalid/no-op transform raises or passes through. Per dos-and-donts, "validation errors are machine-readable and identify violated... constraints" — silent no-ops here hide a real failure (the consumer thinks the transform succeeded). Fix: pick one rule, e.g. all transform methods raise `UnsupportedTransformError` (already defined but unused) for invalid input, and document "unchanged" only for genuinely no-op cases (e.g. `remove_skin_tone` on a sequence with no modifier — which is a legitimate no-op, not an error). Resolve the `apply_skin_tone` self-contradiction explicitly.

**3. `UnsupportedTransformError` is defined but never referenced by any `EmojiTransformer` method's `Raises` section.**
Every transformer method that can fail names `ValueError` or nothing, while a dedicated, more informative exception type exists unused. This is dead/confusing API surface — consumers see the exception class and reasonably assume it's raised by the transform methods. Fix: either wire `UnsupportedTransformError` into the transform methods that currently raise generic `ValueError` (preferred — it carries `sequence` and `transform` for diagnostics, satisfying "validation errors are machine-readable"), or remove it.

**4. `EmojiConverter.to_shortcode`/`to_image_url` return `Optional[str]` (None on miss) while `from_shortcode` also returns `Optional[str]`, but `EmojiCatalog.by_sequence` returns `Optional[Emoji]` — three different "not found" representations across the library with no shared convention, and no `UnknownEmojiError` usage anywhere despite it being defined.**
`UnknownEmojiError` is defined in the exceptions section but never appears in any method's `Raises:` docs. Consumers must guess: does `by_sequence("🤷")` for a near-miss return `None`, or could it raise? Fix: state the convention once — e.g. "lookup methods return `None` for not-found; `UnknownEmojiError` is reserved for methods where absence is a caller error, not a valid query result" — and either apply `UnknownEmojiError` somewhere or remove it to avoid implying unsupported behavior.

**5. `EmojiTransformer.zwj_sequence` raising `ValueError` for "fewer than two sequences" makes the varargs signature partially load-bearing in a way that's easy to misuse, and conflicts with naming guidance against signatures that hide minimum-arity requirements.**
A call like `transformer.zwj_sequence("👨")` type-checks fine but raises at runtime. This is a minor ergonomics issue but worth flagging since ZWJ-joining a single sequence is a meaningless no-op that could just as easily return the input unchanged (consistent with the "no-op vs raise" inconsistency in finding 2). Fix: either accept `seq_a: str, seq_b: str, *rest: str` to make the two-argument minimum visible in the signature, or document why returning the input unchanged for a single argument is wrong here specifically.

## Contract Shape / Problem Fit Observations

**6. `EmojiAnalyzer.co_occurrence`'s "window" parameter is ambiguous: "distance... for two emoji to be counted as co-occurring" combined with "adjacent emoji only" as the default for `window=1` is internally consistent, but the units of "distance" are unclear** — is it distance in emoji-positions (as stated) or could an implementer reasonably interpret it as character/token distance given the broader text-processing context? Given `density()` already distinguishes "emoji tokens" from "word tokens," this method should explicitly restate that `window` counts only emoji positions, ignoring intervening text/words, to prevent two correct-looking but incompatible implementations.

**7. `EmojiConverter.to_shortcode`/`from_shortcode`/`to_image_url` use an open `dialect: str` parameter rather than an enum, unlike `EmojiCategory`/`SkinTone`/`HairStyle` which are all enums.** This is the only place in the library where a closed, library-relevant set of options ("github", "slack", "twemoji", "noto", "openmoji") is typed as a free string. Inconsistent with the library's own typed-API design goal stated in the module docstring ("Typed: public APIs carry full PEP 484 annotations so IDEs and type-checkers can catch mistakes before runtime") — a typo like `dialect="github"` is currently a silent `None`/wrong-result, not a type error. Fix: define `ShortcodeDialect` and `ImageDialect` enums (or a `Literal[...]` type) while still allowing extension if the library supports plugin dialects.

**8. `EmojiRenderer.to_sprite_sheet` has no documented behavior for `len(sequences) == 0` or for `sequences` containing entries that individually raise `RenderError`.** Per dos-and-donts, bulk operations need defined partial-success/error semantics. Does one unrenderable emoji abort the whole sprite sheet, get skipped, or get replaced with a placeholder? This should be specified — at minimum, state whether `to_sprite_sheet` is all-or-nothing or best-effort.

## Open Questions / Assumptions

- **`Emoji.is_modifier_base` and `Emoji.supports_zwj`** are declared with `...` bodies and no docstring detail on how they're derived (static CLDR data vs. computed from `sequence`). Since `EmojiTransformer.apply_skin_tone`/`apply_hair_style` need exactly this information to decide raise-vs-no-op, these properties should be the documented source of truth the transformer methods are specified against — currently the two ABCs don't reference each other at all, despite an obvious dependency.
- **Thread-safety is specified only for `EmojiCatalog`** ("must be safe to call from multiple threads after construction"). No equivalent statement exists for `EmojiRenderer` (which likely wraps font/image state) or `EmojiAnalyzer` (which may cache frequency tables). If these are meant to be used as long-lived singletons (as the `Example` blocks imply), thread-safety should be stated or explicitly disclaimed for each ABC.
- **`EmojiAnalyzer.frequency` doc says "sorted by count descending"** but `Counter` is not inherently ordered in a way Python's type system or `==` comparisons preserve meaningfully — `Counter` equality ignores order. If ordering is a contract guarantee, consider returning `list[tuple[str, int]]` (as `top_n` already does) for consistency, or clarify that "sorted" only applies to iteration via `.most_common()`.

## Summary

No blocking architectural issues — the ABC decomposition is sound and abstraction levels are well-separated (catalog/detection/transform/analysis/conversion/rendering map cleanly to consumer workflows). The main risks are inconsistent error-vs-no-op conventions across `EmojiTransformer` (finding 2) and an unused exception type (`UnsupportedTransformError`, finding 3) that currently misleads implementers and consumers about the error contract. These should be resolved before implementation begins, since fixing them later is a breaking change to every concrete `EmojiTransformer`.