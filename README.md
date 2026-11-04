# Nuke Tools — Read Node Auditor

## Character Shadow (2D alpha)

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
