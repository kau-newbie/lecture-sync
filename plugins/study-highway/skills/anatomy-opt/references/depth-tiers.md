# Depth tiers

Added in the local anatomy-opt version. It replaces the Epic size. A large subject (a vehicle, a building, a plant) is drawn as one Hero: a few parts in full detail and the rest as a flat, blurred setting, the way a game draws distant scenery as a flat background image or blurs it with depth of field. Level of detail with two or three levels is the usual game practice; more levels only add work.

## 1. The three tiers

Put every part in one tier when you write the parts list (workflow step 4). Ask the user which mechanism is the focus when it is not obvious.

| Tier | What goes in it | How it is drawn | Checks |
|---|---|---|---|
| Focus | The subject and its mechanism: the parts that carry the idea | Every rule in `SKILL.md`: full detail, four-tone shading, true depth order | Full audit, line check, 4× close-ups |
| Context | Parts that touch the focus: base, stand, neighbours, cables into the focus | Bevels, main shading, only the screws and labels that sit on the focus side; no knurls, ticks or textures | The line check and one 2× view |
| Backdrop | Everything else that gives scale and setting | Flat silhouettes in `lo` or `faint`, one or two tones, no textures, no lines that must end on something | A 1× view only |

Part budget: a Figure is 40–80 parts in total, mostly focus. A Hero is 80–150 parts in total with at most 60 focus parts, 40 context parts and 50 backdrop silhouettes. If the subject needs more focus parts than that, say so and propose a smaller focus.

## 2. Backdrop layer (impostor and depth of field)

- Draw all backdrop shapes inside one group, `<g class="iso-backdrop">`, and paint it first, behind everything else.
- Blur the group once with CSS: `.iso-backdrop { filter: blur(2px); opacity: 0.85 }`. The kit already uses `filter: blur()` for the halo under the base (`.iso-halo` in `kit/iso.css`). Tune the blur radius by eye at 1× and at phone width.
- Never animate, move or toggle a blurred group. SVG blur is a slow path in browsers, and it stays cheap only when the blurred result does not change.
- Never put the figure's subject, readout or a moving part in the backdrop.
- Keep backdrop shapes out of the `A.recorder` list so the audit does not treat them as parts. This is untested in this version: if `--audit` reports a backdrop shape, record only focus and context parts and report the failure to the user.
- Build the backdrop with `slabOf` or `extrude` flat tones, or with plain paths. A few large silhouettes are better than many small ones.

## 3. Culling: do not author what cannot be seen

- Do not write parts that are fully hidden from the chosen camera, or that are inside a closed housing, unless the figure is a cutaway or an exploded view.
- Cull before you write code, in the parts list. A culled part costs no code, no audit time and no check.

## 4. Effects

- WebGL layers apply to the focus tier only (at most the limit in `SKILL.md`, workflow step 1).
- An effect in the backdrop (smoke, glow, steam behind the machine) is a static blurred shape with a soft gradient. Do not write a shader for it.

## 5. Parallax instead of the 3D mode

Use this when the idea does not need a part that truly turns. This is a new technique in this version and is untested.

- Split the figure into two or three groups: backdrop, context, focus.
- On pointer move, shift each group by a small offset in the same direction, scaled by depth: 0 for focus, a few pixels for context, more for backdrop. Do not blur a group that is moving; draw the backdrop sharp while it moves and blur it when still, or skip the blur.
- Honour reduced motion: no shift.
- Use the 3D mode (`references/3d.md`) only when a part turning in depth is the idea itself, and then for one subject.

## 6. What does not save Claude's tokens

These techniques make the finished page smaller or faster in the browser, but they do not reduce what Claude writes or reads, so they are not part of this skill:

- Reusing shapes with `<use>` or `<symbol>`: the kit builds strings in loops already, so the code is the same size.
- Merging paths of the same tone to reduce draw calls.
- Baking an assembly to an image.

## 7. Whole vehicle, building or plant

There is no larger size than Hero. For a subject this large:

1. Choose one mechanism as the focus and say which one.
2. Put its touching parts in context and the rest of the object in the backdrop.
3. Offer a second figure for another mechanism if the user wants it. Each is its own Hero or Figure.
