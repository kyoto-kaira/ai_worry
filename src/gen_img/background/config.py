# gen_img/background/config.py

import os
from gen_img.paths import BACKGROUND_DIR

MODEL = os.environ.get("IMAGE_MODEL", "gemini-3-pro-image")

# 線の太さ・描き込みの密度の参考としてだけモデルに渡す
STYLE_REFERENCES = [BACKGROUND_DIR / "1.png", BACKGROUND_DIR / "2.png"]

REFERENCE_NOTE = (
    "Create a completely new illustration. The attached images are ONLY a style reference for line "
    "weight, density and drawing style; do not copy their layout, objects or creatures."
)

# 構図・視点・地面の割合・クリーチャーの抑制を定義した全テーマ共通スタイル
STYLE = (
    "Black and white line art only, like a coloring book page. Clean uniform black outlines of medium "
    "thickness on a pure white background, no shading, no gray fills, no hatching, no color, no text, "
    "no letters, no signature. An extremely detailed 'Where's Wally' style seek-and-find scene edge to edge. "
    "COMPOSITION & PERSPECTIVE: High-angle isometric or slightly top-down perspective with a prominent, "
    "broad ground/floor plane occupying the majority of the image. Alternatively, if side-view, fill the background "
    "depth with dense multi-tiered structures, platforms, scaffolding, shelves, pipes, grids, and architectural lines "
    "so anything positioned higher up naturally rests on or inside a structure. "
    "CREATURE DENSITY: Keep the background creature count LOW (include only a few sparse, small background creatures, "
    "never zero, but do NOT crowd the screen with creatures). Focus heavily on inanimate objects, architecture, "
    "machinery, furniture, and environmental details, leaving clean floor/surface spaces for character placement. "
    "Do NOT draw any brain-shaped creature, and no creature with a net or mesh of tentacles."
)

THEMES = {
    1: (
        "A cluttered high-tech robot laboratory viewed from a high angle: sprawling floor grid covered with "
        "control panels, workbench tables, complex machinery, pipes, monitors, tools, and cables. "
        "Only a few small idle robots sparse throughout the lab."
    ),
    2: (
        "A fantasy medieval marketplace viewed from an upper perspective: wide cobblestone ground with many "
        "wooden stalls, potion displays, barrels, crates, ropes, and hanging signs. Only 2 or 3 merchant creatures."
    ),
    3: (
        "A multi-tiered underwater laboratory: layered ocean floor with coral, submerged platforms, glass tanks, "
        "dense networks of pipes, valves, and diving gear filling the background depth. A few tiny sea critters."
    ),
    4: (
        "A mushroom forest village with rich ground coverage and wooden bridges: giant mushroom houses with doors, "
        "root systems, ladders, stairs, and lanterns filling the vertical space. A few small forest spirits."
    ),
    5: (
        "A busy retro space station interior viewed from above: multi-level catwalks, metal floor panels, control desks, "
        "hatches, and background wall piping. A few small alien creatures sparsely placed."
    ),
    6: (
        "Kyoto University Clock Tower Centennial Hall plaza from a high-angle bird's-eye view: broad paved plaza "
        "ground filling the view, iconic brick clock tower, sprawling camphor tree branches, rows of parked bicycles, "
        "benches, and lamp posts. Only a few scattered student figures."
    ),
    7: (
        "A stepped university lecture hall viewed from above: tiered rows of desks and stairs going down, massive "
        "blackboards with formulas, desks packed with textbooks, laptops, stationary, and backpacks. A few student creatures."
    ),
    8: (
        "A grand university library with deep perspective: wooden floor, towering bookshelves, rolling ladders, "
        "spiral staircases, reading carrels, stacks of manuscripts, and scrolls. A couple of studious little creatures."
    ),
    9: (
        "Kyoto Shinto shrine with thousands of Torii gates (Fushimi Inari style) viewed from an elevated angle: "
        "stone pathways climbing up, dense tunnel maze of Torii gates, stone lanterns (ishidoro), fox statues, "
        "and cedar trees filling the depth. A few spirit figures."
    ),
    10: (
        "Kyoto historic temple with Zen rock garden viewed from a high veranda: broad raked gravel sand patterns, "
        "engawa wooden floorboards, mossy boulders, temple roofs, five-story pagoda in background, and bonsai pines. "
        "A few monk figures."
    ),
    11: (
        "Kyoto Station building grand atrium viewed from an upper escalator: vast floor space, crisscrossing "
        "catwalks, steel trusses, lattice glass roof, platforms, and train tracks in the background. A few commuter figures."
    ),
    12: (
        "Kyoto Kamogawa Delta riverside park from a high angle: wide grassy banks, flowing river with turtle-shaped "
        "stepping stones, stepping paths, weeping willow trees, bicycles on pathways. A few picnicking figures."
    ),
    13: (
        "Kyoto Kiyomizu-dera Temple viewed from an elevated angle: famous massive wooden stage supported by complex "
        "interlocking timber scaffolding beams, broad wooden floorboards, surrounding maple trees, stone lanterns, "
        "Otowa Waterfall below, and pagodas in the background depth. A few tourist creatures."
    ),
    14: (
        "Kyoto Kinkaku-ji (Golden Pavilion) viewed from a high lakefront perspective: the iconic three-story pavilion "
        "with ornate roof and phoenix ornament, broad Kyoko-chi (Mirror Pond) with decorative rock islands occupying the "
        "lower foreground, garden walking paths, pine trees, and stone lanterns. A few sightseeing creatures."
    ),
    15: (
        "A bustling university sports ground/athletic field viewed from high stadium bleachers: wide dirt and grass field "
        "marked with running track lines, soccer goals, baseball dugouts, tennis nets, sports equipment carts, cones, "
        "and bench seating. A few athletic student creatures practicing sports."
    ),
    16: (
        "A crowded university cafeteria and student dining hall viewed from a top-down angle: broad floor space "
        "filled with long rows of dining tables, chairs, food service counters, tray return racks, vending machines, "
        "menu boards, and water dispensers. A few dining student creatures eating."
    ),
}