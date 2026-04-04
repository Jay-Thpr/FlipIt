from __future__ import annotations


CLEAN_PHOTO_EDIT_PROMPT = (
    "Keep the item identical and centered. Remove the background and replace it with a pure white studio background. "
    "Do not change the product shape, color, branding, material, or visible wear. "
    "Return a clean resale-ready product image only."
)


def build_clean_photo_prompt(*, category_hint: str | None = None) -> str:
    if not category_hint:
        return CLEAN_PHOTO_EDIT_PROMPT
    return f"{CLEAN_PHOTO_EDIT_PROMPT} Item category hint: {category_hint}."
