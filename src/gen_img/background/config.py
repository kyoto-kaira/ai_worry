import os

from gen_img.paths import BACKGROUND_DIR

MODEL = os.environ.get("IMAGE_MODEL", "gemini-3-pro-image")

# 線の太さ・描き込みの密度の参考としてだけモデルに渡す
STYLE_REFERENCES = [BACKGROUND_DIR / "1.png", BACKGROUND_DIR / "2.png"]

REFERENCE_NOTE = (
    "Create a completely new illustration. The attached images are ONLY a style reference for line "
    "weight, density and drawing style; do not copy their layout, objects or creatures."
)

STYLE = (
    "Black and white line art only, like a coloring book page. Clean uniform black outlines of medium "
    "thickness on a pure white background, no shading, no gray fills, no hatching, no color, no text, "
    "no letters, no signature. An extremely dense, detailed 'Where's Wally' style seek-and-find scene that "
    "fills the whole canvas edge to edge with many small objects and quirky cartoon creatures. "
    "Do NOT draw any brain-shaped creature, and no creature with a net or mesh of tentacles."
)

THEMES = {
    3: "A crowded underwater laboratory: coral, bubbles, glass tanks, cables, valves, diving helmets, "
    "odd fish and one-eyed sea critters hiding among machines.",
    4: "A cluttered mushroom forest village: giant mushrooms with doors and windows, roots, ladders, "
    "lanterns, stairs, bridges, snails, bugs and goofy forest spirits with big round eyes.",
    5: "A busy retro space station interior: control panels, pipes, hatches, robots, floating gadgets, "
    "planets through round windows, and many small alien creatures with antennae and big eyes.",
}
