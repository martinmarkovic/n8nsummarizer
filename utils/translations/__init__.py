"""
Translation catalog package.

Each submodule owns the UI strings for one feature/view and exposes a
``STRINGS`` dict of ``{key: {lang: text}}``. This module merges them all into a
single ``CATALOG`` that utils.i18n consumes.

Splitting the catalog per feature keeps it maintainable and lets different
tabs be localized independently without editing one giant file.

To add a new feature's strings: create a new submodule with a ``STRINGS`` dict
and add it to ``_MODULES`` below.
"""

from utils.translations import (
    common,
    summarizer,
    transcriber,
    bulk_summarizer,
    bulk_transcriber,
    translation,
    downloader,
    video_subtitler,
    picture_to_text,
    context_menu,
    fullscreen,
)

# Order matters only for duplicate-key warnings (last one wins); keys are
# namespaced per module so collisions are not expected.
_MODULES = (
    common,
    summarizer,
    transcriber,
    bulk_summarizer,
    bulk_transcriber,
    translation,
    downloader,
    video_subtitler,
    picture_to_text,
    context_menu,
    fullscreen,
)

CATALOG = {}
for _module in _MODULES:
    _strings = getattr(_module, "STRINGS", {})
    for _key, _value in _strings.items():
        if _key in CATALOG:
            # Duplicate key across modules — keep the first, but surface it.
            import warnings
            warnings.warn(
                f"[i18n] Duplicate translation key '{_key}' in "
                f"{_module.__name__}; keeping the earlier definition."
            )
            continue
        CATALOG[_key] = _value
