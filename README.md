# Nuke Tools — Read Node Auditor

## Character Shadow (2D alpha)

### Widen farther from the feet

**Distance widening (pixels)** adds horizontal dilation gradually with distance
from the ground line. Try `30` with Falloff distance `300` for a cast shadow.
The extra width is zero at contact, reaches the chosen value at Falloff distance,
and holds that value beyond it. **Expand shadow** remains the uniform base
expansion. Blur and opacity falloff are independent; the contact layer is untouched.

This works in both modes using the same distance definitions as Distance softness.
For the small Under Character patch, try a shorter Falloff distance such as `40`.
Widening changes horizontal thickness, not length or vertical placement. It uses
four interpolated dilation levels before blur, so it is an artistic approximation
and may show blended edges on hard, unblurred mattes. Zero bypasses the extra
processing and preserves the previous result. It does not simulate a 3D light.

In Nuke, test a narrow rectangle: contact width should stay fixed while farther
rows widen. Check positive/negative projection, both modes, a moving matte,
zero widening, and combinations with blur and expansion. Host checks are pending.

### Expand and soften with distance

The **Shadow** tab now includes **Expand shadow**, **Distance softness**, and
**Extra far softness**. Expansion grows the broad shadow's alpha before blur,
without changing the independent contact layer. These controls work in both modes.

For a cast shadow, try base Softness `5`, Distance softness `1`, Extra far softness
`40`, and Falloff distance `300`. At ground contact the base blur is used; farther
along the cast direction it blends toward base plus extra blur, reaching the far
blur at Falloff distance. **Falloff** still controls opacity independently: set it
to `0` to keep density while varying softness. Expand shadow `5–15` is a starting
point for thickening the silhouette before softening it.

In Under Character mode, distance is measured vertically from the offset ground
line in either direction; a shorter Falloff distance such as `30–60` generally
fits the compact patch better. Base softness and width spread come from the
Under Character tab. The patch is not radially blurred around individual feet.

This is an artistic blend of two fixed blurs, not a physically based penumbra
simulation. Near-horizontal cast projections are poorly conditioned; use Under
Character mode for overhead-style patches. Settings default to zero expansion
and zero distance softness to preserve the previous look. Host checks pending:
verify positive expansion grows alpha, distance softness zero matches base blur,
far edges soften with distance, and tinted output stays premultiplied. Update the
whole `nuke_tools` folder and create a new group to get the new controls.

### Soft shadow directly under the character

On the **Shadow** tab choose **Shadow mode → Under Character**. This replaces
the long cast layer with a compressed whole-silhouette patch; the independent
contact layer is still available. On the **Under Character** tab start with:

- **Depth:** `0.04` (a 600-pixel-tall silhouette becomes about 24 pixels deep).
- **Width spread:** `20` pixels of extra horizontal blur to blend the shape.
- **Softness:** `12` pixels; increase for a softer overhead-light look.
- **Density:** `0.35`; increase if the patch is too faint after blur.
- **Offset:** X `0`, Y `-8`; adjust Y to position the patch beneath the shoes.

The patch follows the incoming character's horizontal position and compresses
around animated **Ground contact Y**. Width spread expands via blur rather than
scaling around the frame center, so it does not shift a moving character's patch
sideways. It can soften and widen the source shape, but cannot make it narrower
than the source without upstream matte adjustments. Depth is a scale, not a fixed
pixel height; poses with different silhouette heights may vary in patch depth.

Main Shadow color applies to both modes. Cast reach, ground projection, falloff,
cast softness and cast density only affect Cast Shadow mode. Contact controls
remain independent of either mode and of the broad patch's offset.

Nuke validation still required: switch modes on a moving matte, check ground-line
tracking and offsets, confirm width changes do not displace the patch, compare
with the contact layer disabled, and check premultiplied tinted output. Existing
groups do not gain these controls automatically; create a new group after update.

### Contact shadows

#### Default straight ground line

New groups include a straight line without needing a Roto node. On **Contact
Shadow**, leave Ground reference at **Built-in straight line**, enable **Preview
ground guide**, and adjust **Ground contact Y** on the Shadow tab until the white
line meets the planted soles. View the Group output or its composite while
positioning the line. Turn preview off to restore shadows before rendering.
The line uses the selected character format at group creation (or the root format
if nothing was selected); recreate the group if that format changes. It follows
Ground contact Y animation. Use Hold Ground for a fixed floor. This is a procedural
line, not an editable Roto spline; use an external guide for slopes or curves.

#### Uneven ground: draw an open guide

New groups have an optional second input, **GroundGuide**. The **Contact Shadow**
tab includes **Ground reference** and **How to draw a ground guide…**; the button
opens these instructions inside Nuke.

1. Create a separate **Roto** on transparent black in the same image format and
   coordinates as your positioned character. Leave its background disconnected.
2. Draw an **open stroked spline** following the walking surface across the full
   path. Use a thin, approximately 1–2 pixel stroke, opacity 1, rendered in alpha.
   No closed shape is needed. The line must actually render: an unstroked open
   path is not enough. An open **RotoPaint brush stroke** is also suitable.
3. View the guide's **alpha**. Only the ground line should be white; the rest must
   be transparent. Do not connect a background with an opaque alpha.
4. Connect the character to the first Group input and the guide to the second.
5. Choose **Contact Shadow → Ground reference → External ground guide (input 2)**.
6. Enable contact; try Density `0.8`, Strength `1`, Contact tolerance `3–5`,
   Patch depth `3–5`, Width spread `3–5`, and Softness `2–4`.

The guide is widened vertically by Contact tolerance, then intersected with the
character alpha. Only that overlap creates a patch. A lifted foot outside the
band contributes nothing. The guide stroke thickness adds to the effective
tolerance, so keep it thin. Patch depth adds vertical dilation around the overlap
in guide mode; it does not flatten the patch to Ground Y. Width and softness are
applied afterward and can spread a valid patch beyond the guide line.

For a locked camera and static ground, draw once. Animate only if the surface
moves in image coordinates. Ground Y/Follow Feet still position the **broad**
shadow; the guide controls the **contact layer only**. This does not make the
long cast shadow conform to a 3D surface. It cannot distinguish a hand or prop
touching the line from a foot, or resolve multiple depth layers at one location.

Built-in straight line is the default and requires no second input. Ground Y (legacy) retains the original contact-band behavior. Guide mode requires
a connected, rendered alpha stroke; a missing input may produce a Nuke input
error, and an empty guide gives no contact. Switch back to Ground Y to bypass it.
Create a new group after updating; existing groups do not gain a second input.

Nuke checks pending: use a thin diagonal/open curved stroke and a moving two-foot
matte. Confirm contact follows the slope, disappears for a raised foot, stays
absent outside the stroke's covered area, and responds to tolerance. Also check
Ground Y with the guide disconnected, empty guide, both broad modes, contact
disable, and save/reopen. Roto stroke rendering and the Nuke graph need host testing.

New groups have a **Contact Shadow** tab with a separate contact layer combined
over the long cast shadow. It shares the main shadow color and Ground contact Y,
including analyzed animation, but has independent density and softness.

- **Enable contact shadow** bypasses this layer when unchecked.
- **Contact tolerance** selects a narrow strip above the ground line (default
  5 pixels). Alpha is strongest at the line and fades to zero at the top of the
  tolerance. A foot fully above this strip contributes no contact patch.
- **Patch depth** compresses that strip vertically (default 5 pixels).
- **Width spread** adds horizontal blur without shifting the foot positions.
- **Softness** blurs the patch in both directions. Blurring can reduce peak density.
- **Density** sets opacity; **Strength** is a separate animatable multiplier.
  Set strength to zero during a jump or reduce it when contact looks wrong.

The patch follows horizontal motion in the incoming alpha and vertical motion
through Ground contact Y. For a sideways walk on a level floor in a locked shot,
set Ground contact Y at the planted sole and keep it fixed. If it already has
Follow Feet keys, choose a frame with a planted foot and click **Hold Ground at
Current Value**. It asks before removing animation and can be undone. It also
changes the broad shadow's shared ground line. You can rerun analysis afterward.

Do not follow a lifted foot with the ground line: that would keep it inside the
contact tolerance and produce a floating patch. For movement into depth, animate
the actual floor height as needed. The detector does not identify anatomical
feet; any alpha inside the strip contributes. Soft blur may spread a valid patch
below the ground line in the image; the restriction applies before blur. Contact
strength still affects both feet together and can be corrected manually.

Install the updated `nuke_tools` folder, restart Nuke and create a new group;
existing groups are unchanged. In Nuke, check a two-foot matte moving horizontally
and vertically: the patches should follow it. Check that alpha above the source
band contributes nothing, a lifted foot loses its patch while a planted foot
retains one, and holding ground clears only Ground contact Y animation with Undo.
Disabling the layer or setting strength to zero should
restore the cast-only result. Check colored shadows over a checkerboard, animation,
Undo and save/reopen. Host rendering checks are pending.

### Follow a moving character

Connect the character **after** any transforms that position it in the scene.
Click **Analyze Alpha / Follow Feet**, enter a first/last frame, and let analysis
finish. The tool samples bottom-up alpha row averages and writes Ground contact Y
keys at the lowest occupied row on each frame. Horizontal movement already comes
from the moving input silhouette. This is a one-time analysis, not a live tracker:
reanalyze after changing the matte, timing, format or upstream transforms.

Start with the default **Alpha row threshold** of `0.001`. Raise it to ignore
faint noise; lower it if thin or faint feet disappear. It measures the average
over the full image width, not an individual pixel's alpha. Scanning large frames
or long clips can be slow. Cancel leaves existing contact keys unchanged.
Existing contact animation requires confirmation before full replacement;
the replacement is one Undo operation. Other shadow controls are preserved.

Empty frames hold the previous detected height; leading empty frames use the
first detected height. Entirely empty clips leave the control unchanged. Only
pixels inside the input image format are inspected. The matte must contain only
the intended character. This detects the bottom of the silhouette, not physical
ground: jumps, cropped feet, props or edge noise require manual key corrections.
It does not estimate background lighting, and it does not stabilize bouncing feet.

Host smoke check: animate a rectangle vertically with a known bottom coordinate,
analyze, and compare the contact keys. Also check an empty frame, cancellation,
Undo, a missing alpha channel and save/reopen. These Nuke API checks are pending.

Creates a native, editable Nuke Group that projects an input alpha into a ground
shadow. Intended for Nuke 17.0v4 on Windows; host validation is still pending.
Add this to your `menu.py` after the plugin path setup below:

```python
from nuke_tools.shadow import install_menu as install_shadow_menu
install_shadow_menu()
```

1. Select one character Read or other node with a clean alpha.
2. Choose **Nuke Tools → Character Shadow**.
3. Set **Ground contact Y** to the feet's vertical image coordinate (Nuke's
   origin is bottom-left). The contact line stays fixed during projection.
4. Adjust **Horizontal reach** and **Ground projection** to match scene lighting.
   Reach is the horizontal displacement over one full image height. Positive
   projection casts downward from the feet; negative casts upward. Avoid zero
   projection, which collapses the silhouette to a line.
5. Adjust softness, density and shadow color. Output RGB is premultiplied.
6. Merge the shadow **over the background**, then the character **over that**.

**Falloff** fades density with distance from the feet. At `0` the shadow stays
uniform; at `1` it fades fully to transparent at **Falloff distance (pixels)**.
Try Falloff `1` and distance `500`, then increase the distance for a longer fade.
The distance follows the projected shadow direction, including horizontal reach.
Softness is applied after the fade, so a blurred edge can extend past that distance.

To update: replace your installed `nuke_tools` folder with the latest folder,
restart Nuke, and create a new Character Shadow node. Existing groups keep their
original controls and behavior; keep them until you have copied their settings
and checked the replacement.

This is an artist-directed planar projection, not automatic light estimation or
a physically accurate 3D shadow. It uses uniform softness, assumes a horizontal
contact line, and cannot reconstruct hidden body geometry, uneven surfaces or
multiple lights. Source alpha below the contact line also projects; clean or
crop unwanted source matte first. No source media or files are modified.

Inside Nuke, validate with a simple opaque rectangle on transparent background:
confirm the contact line is fixed, reach moves the shadow left/right, projection
changes its length, density zero makes it transparent, and color composites
without fringes. Then test a character matte, Undo creation, and save/reopen the
script. These host checks cannot run in the current cloud machine.
Also check Falloff `0` against the original uniform shadow, Falloff `1` at
several distances, both projection signs and left/right reach. Contact density
should stay strongest and the far end should fade; tinted output should remain
premultiplied when merged.

A dependency-free Python panel intended for Foundry Nuke 17.0v4 on Windows.
Scan Read nodes for missing files and sequence gaps, then preview and apply
folder-prefix replacements in a single undo operation.

## Install on Windows

1. Keep this repository in a permanent folder, for example `C:/tools/Nuke-Tools`.
2. Add these lines to your existing `%USERPROFILE%/.nuke/menu.py` (create it if
   absent; preserve any existing configuration):

   ```python
   import nuke
   nuke.pluginAddPath("C:/tools/Nuke-Tools")
   from nuke_tools.auditor import install_menu
   install_menu()
   ```

3. Restart Nuke and open **Nuke Tools → Read Node Auditor**.

Scan all Read nodes, including groups, or enable selected-only mode for the
current group. Scanning checks each Read node's inclusive first/last frame range
using Nuke's filename resolver and restores the current frame afterward. Movie
and still-image filenames are checked once. Missing files are listed up to 20
per node; the count includes all missing files. Cancellation gives partial results.

For relinking, enter old and new folder prefixes, such as `D:/show/plates` and
`E:/archive/plates`. Review the proposed changes before confirming. Animated and
expression paths are skipped. Relinking does not copy files or save the script.
Use Nuke Undo to revert. A scan follows each relink.

## Development and validation

No packages, services or credentials are required for the filesystem logic:

```sh
python3 -m unittest discover -s tests -v
```

The panel requires Nuke's bundled `nuke` and `nukescripts` modules; installing a
PyPI package named `nuke` does not provide the host application. Nuke itself and
an appropriate license are not included. The panel has not been run in Nuke here.

Before production use, test in Nuke 17.0v4 with a disposable script: a complete
sequence, a sequence with one missing frame, a still, a movie, a grouped Read,
and a relink followed by Undo. Confirm the current frame is restored. Scanning
checks file existence, not decoding, movie frame counts, or media corruption;
it does not audit DeepRead nodes. Relative paths use the host's working-directory
resolution. Large network sequences may take time to inspect.
