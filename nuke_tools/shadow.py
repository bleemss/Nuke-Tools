"""Build an editable alpha-projected shadow using native Nuke nodes."""

import nuke

from .contact import find_contact


def track_contact(group):
    """Analyze first, then write keys atomically in a single undo operation."""
    source = group.input(0)
    if source is None:
        nuke.message("Connect the character with alpha to the shadow input first.")
        return
    panel = nuke.Panel("Follow feet from alpha")
    panel.addSingleLineInput("First frame", str(int(nuke.root()["first_frame"].value())))
    panel.addSingleLineInput("Last frame", str(int(nuke.root()["last_frame"].value())))
    if not panel.show():
        return
    try:
        first, last = int(panel.value("First frame")), int(panel.value("Last frame"))
        if last < first:
            raise ValueError
    except ValueError:
        nuke.message("Enter whole frame numbers, with last frame at least first frame.")
        return
    contact = group["contact_y"]
    if contact.isAnimated() or contact.hasExpression():
        if not nuke.ask("Replace ALL existing Ground contact Y animation or expressions?\n"
                        "Other controls are preserved. You can Undo the replacement."):
            return
    threshold = float(group["alpha_threshold"].value())
    if not 0 < threshold < 1:
        nuke.message("Alpha row threshold must be between 0 and 1.")
        return
    original_frame = nuke.frame()
    values = []
    empty = []
    task = nuke.ProgressTask("Follow feet from alpha")
    try:
        for frame in range(first, last + 1):
            if task.isCancelled():
                raise InterruptedError
            nuke.frame(frame)
            if "rgba.alpha" not in source.channels():
                raise ValueError("The connected character has no rgba.alpha channel.")
            width, height = source.width(), source.height()
            task.setMessage("Frame %d" % frame)
            task.setProgress(int(100 * (frame - first) / (last - first + 1)))

            def sample_row(row):
                if task.isCancelled():
                    raise InterruptedError
                return nuke.sample(source, "rgba.alpha", width / 2.0, row + 0.5, width, 1)

            value = find_contact(height, sample_row, threshold)
            if value is None:
                empty.append(frame)
            values.append((frame, value))
    except InterruptedError:
        nuke.message("Analysis cancelled. Ground contact was not changed.")
        return
    except Exception as error:
        nuke.message("Analysis failed; ground contact was not changed.\n%s" % error)
        return
    finally:
        nuke.frame(original_frame)
        del task
    detected = [value for frame, value in values if value is not None]
    if not detected:
        nuke.message("No alpha above the threshold was found. Ground contact was not changed.")
        return
    # Hold the previous contact through empty frames; backfill leading empties
    # from the first detected frame rather than inventing a ground coordinate.
    previous = detected[0]
    with nuke.Undo("Follow feet from alpha"):
        contact.clearAnimated()
        contact.setAnimated()
        for frame, value in values:
            if value is not None:
                previous = value
            contact.setValueAt(previous, frame)
    nuke.message("Contact keys created for %d frames.\n"
                 "%d frames had no detectable alpha and use held contact.\n"
                 "Review lifted feet, cropped mattes and noisy edges." % (len(values), len(empty)))


def create_shadow():
    selected = nuke.selectedNodes()
    source = selected[0] if len(selected) == 1 else None
    with nuke.Undo("Create Character Shadow"):
        group = nuke.nodes.Group(name="CharacterShadow", label="2D ground shadow")
        if source is not None:
            group.setInput(0, source)
        group.addKnob(nuke.Tab_Knob("shadow_controls", "Shadow"))
        contact = nuke.Double_Knob("contact_y", "Ground contact Y (pixels)")
        group.addKnob(contact)
        contact.setRange(0, 2160)
        contact.setValue(0)
        threshold = nuke.Double_Knob("alpha_threshold", "Alpha row threshold")
        threshold.setRange(0.00001, 0.05)
        threshold.setValue(0.001)
        threshold.setTooltip("Minimum mean alpha across a full image row. Raise to reject faint noise; lower for narrow or faint feet.")
        group.addKnob(threshold)
        follow = nuke.PyScript_Knob("follow_feet", "Analyze Alpha / Follow Feet")
        follow.setCommand("from nuke_tools.shadow import track_contact\ntrack_contact(nuke.thisNode())")
        group.addKnob(follow)
        for name, label, default, low, high in (
            ("reach", "Horizontal reach (pixels)", 250, -2000, 2000),
            ("length", "Ground projection", 0.35, -2, 2),
            ("softness", "Softness (pixels)", 15, 0, 200),
            ("density", "Density", 0.5, 0, 1),
            ("falloff", "Falloff", 0, 0, 1),
            ("falloff_distance", "Falloff distance (pixels)", 500, 1, 4000),
        ):
            knob = nuke.Double_Knob(name, label)
            knob.setRange(low, high)
            group.addKnob(knob)
            knob.setValue(default)
        group["falloff"].setTooltip("0 keeps uniform density. 1 fades fully to transparent at the falloff distance.")
        group["falloff_distance"].setTooltip("Distance along the projected ground shadow where the fade reaches its maximum. Measured from the contact line in output pixels.")
        tint = nuke.Color_Knob("tint", "Shadow color")
        group.addKnob(tint)
        tint.setValue([0, 0, 0])
        note = nuke.Text_Knob("help", "", "Place Ground contact at the feet. Reach moves the tip left/right.\n"
                              "Positive Ground projection casts downward; negative casts upward.\n"
                              "Merge this shadow OVER the scene, UNDER the character.")
        group.addKnob(note)
        group.begin()
        try:
            input_node = nuke.nodes.Input(name="CharacterAlpha")
            silhouette = nuke.nodes.Expression(name="ShadowMatte", inputs=[input_node])
            for channel in ("expr0", "expr1", "expr2"):
                silhouette[channel].setValue("0")
            silhouette["expr3"].setValue("clamp(a,0,1)")
            fade = nuke.nodes.Expression(name="DistanceFalloff", inputs=[silhouette])
            # A source pixel's displacement from the fixed contact line becomes
            # (reach * dy / height, -length * dy) after ground projection.
            # Fade before resampling/blur so the soft edge keeps the same fade.
            fade["expr3"].setValue(
                "a*(1-clamp(parent.falloff,0,1)*clamp("
                "abs(y-parent.contact_y)*sqrt("
                "pow(parent.reach/max(height,1),2)+pow(parent.length,2))"
                "/max(parent.falloff_distance,1),0,1))")
            projection = nuke.nodes.CornerPin2D(name="GroundProjection", inputs=[fade])
            # Affine map: x'=x+reach*(y-contact.y)/height,
            # y'=contact.y-length*(y-contact.y). The contact line stays fixed.
            corners = (("0", "0"), ("width", "0"), ("width", "height"), ("0", "height"))
            for index, (x, y) in enumerate(corners, 1):
                projection["from%d" % index].setExpression(x, 0)
                projection["from%d" % index].setExpression(y, 1)
                projection["to%d" % index].setExpression(
                    "(%s)+parent.reach*((%s)-parent.contact_y)/max(height,1)" % (x, y), 0)
                projection["to%d" % index].setExpression(
                    "parent.contact_y-parent.length*((%s)-parent.contact_y)" % y, 1)
            blur = nuke.nodes.Blur(name="ShadowSoftness", inputs=[projection], channels="alpha")
            blur["size"].setExpression("parent.softness")
            color = nuke.nodes.Expression(name="ShadowColorAndDensity", inputs=[blur])
            for knob, channel in (("expr0", "r"), ("expr1", "g"), ("expr2", "b")):
                color[knob].setValue("parent.tint.%s*clamp(a*parent.density,0,1)" % channel)
            color["expr3"].setValue("clamp(a*parent.density,0,1)")
            nuke.nodes.Output(inputs=[color])
        finally:
            group.end()
        if source is not None:
            group.setXYpos(source.xpos() + 150, source.ypos() + 100)
        group["contact_y"].setTooltip("Set this to the feet/ground line in image pixels. The projection fixes this horizontal line.")
        group.showControlPanel()
    return group


def install_menu():
    menu = nuke.menu("Nuke")
    if menu.findItem("Nuke Tools/Character Shadow") is None:
        menu.addCommand("Nuke Tools/Character Shadow", create_shadow)
