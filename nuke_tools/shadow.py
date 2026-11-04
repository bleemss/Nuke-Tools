"""Build an editable alpha-projected shadow using native Nuke nodes."""

import nuke

from .contact import CONTACT_ALPHA, CONTACT_MASK, find_contact
from .softness import CAST_DISTANCE, UNDER_DISTANCE, distance_mask


def hold_ground(group):
    """Freeze the floor at its current evaluated height, with undo support."""
    knob = group["contact_y"]
    value = knob.value()
    if knob.isAnimated() or knob.hasExpression():
        if not nuke.ask("Remove Ground contact Y animation and hold the floor at %g?\n"
                        "This affects both the broad shadow and contact shadow. You can Undo." % value):
            return
    with nuke.Undo("Hold shadow ground height"):
        knob.clearAnimated()
        knob.setValue(value)


def _expand_shadow(node, name):
    # Positive Dilate size expands alpha in the target Nuke host.
    expand = nuke.nodes.Dilate(name=name, inputs=[node], channels="alpha")
    expand["size"].setExpression("max(parent.shadow_expand,0)")
    return expand


def _distance_softness(node, near_blur, name, distance, near_x, near_y):
    far = nuke.nodes.Blur(name=name + "FarBlur", inputs=[node], channels="alpha")
    far["size"].setExpression("(%s)+max(parent.far_softness,0)" % near_x, 0)
    far["size"].setExpression("(%s)+max(parent.far_softness,0)" % near_y, 1)
    mask = nuke.nodes.Expression(name=name + "DistanceMask", inputs=[far])
    mask["expr3"].setValue(distance_mask(distance))
    blend = nuke.nodes.Keymix(name=name + "SoftnessBlend", channels="alpha")
    blend.setInput(0, near_blur)  # B: near softness
    blend.setInput(1, far)  # A: far softness
    blend.setInput(2, mask)
    return blend


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
        mode = nuke.Enumeration_Knob("shadow_mode", "Shadow mode", ["Cast Shadow", "Under Character"])
        group.addKnob(mode)
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
        hold = nuke.PyScript_Knob("hold_ground", "Hold Ground at Current Value")
        hold.setCommand("from nuke_tools.shadow import hold_ground\nhold_ground(nuke.thisNode())")
        hold.setTooltip("For a level floor in a locked shot: freeze the current ground height instead of following raised feet. Replaces contact-height animation after confirmation.")
        group.addKnob(hold)
        for name, label, default, low, high in (
            ("reach", "Horizontal reach (pixels)", 250, -2000, 2000),
            ("length", "Ground projection", 0.35, -2, 2),
            ("softness", "Softness (pixels)", 15, 0, 200),
            ("density", "Density", 0.5, 0, 1),
            ("falloff", "Falloff", 0, 0, 1),
            ("falloff_distance", "Falloff distance (pixels)", 500, 1, 4000),
            ("shadow_expand", "Expand shadow (pixels)", 0, 0, 100),
            ("distance_softness", "Distance softness", 0, 0, 1),
            ("far_softness", "Extra far softness (pixels)", 40, 0, 300),
        ):
            knob = nuke.Double_Knob(name, label)
            knob.setRange(low, high)
            group.addKnob(knob)
            knob.setValue(default)
        group["falloff"].setTooltip("0 keeps uniform density. 1 fades fully to transparent at the falloff distance.")
        group["falloff_distance"].setTooltip("Distance along the projected ground shadow where the fade reaches its maximum. Measured from the contact line in output pixels.")
        group["shadow_expand"].setTooltip("Expand the broad shadow's alpha before blurring, in either mode. The independent contact shadow is unchanged.")
        group["distance_softness"].setTooltip("0 keeps uniform softness. 1 blends fully to the far blur at Falloff distance. Opacity Falloff is independent.")
        group["far_softness"].setTooltip("Additional blur at Falloff distance, added to the active mode's base softness. This is an artistic blend between two blurs.")
        tint = nuke.Color_Knob("tint", "Shadow color")
        group.addKnob(tint)
        tint.setValue([0, 0, 0])
        group.addKnob(nuke.Tab_Knob("under_controls", "Under Character"))
        for name, label, default, low, high in (
            ("under_depth", "Depth (vertical scale)", 0.04, 0.001, 0.25),
            ("under_width", "Width spread (pixels)", 20, 0, 300),
            ("under_softness", "Softness (pixels)", 12, 0, 200),
            ("under_density", "Density", 0.35, 0, 1),
        ):
            knob = nuke.Double_Knob(name, label)
            knob.setRange(low, high)
            group.addKnob(knob)
            knob.setValue(default)
        offset = nuke.XY_Knob("under_offset", "Offset (pixels)")
        group.addKnob(offset)
        offset.setValue([0, -8])
        group["under_depth"].setTooltip("Compress the full silhouette around Ground contact Y. 0.04 makes a 600-pixel character about 24 pixels deep before blur.")
        group["under_width"].setTooltip("Extra horizontal blur widens and blends the footprint while following the input's horizontal position.")
        group["under_offset"].setTooltip("Move only the broad shadow patch. Negative Y moves it downward. The contact shadow stays at the feet.")
        group.addKnob(nuke.Tab_Knob("contact_controls", "Contact Shadow"))
        enabled = nuke.Boolean_Knob("contact_enabled", "Enable contact shadow")
        group.addKnob(enabled)
        enabled.setValue(True)
        for name, label, default, low, high in (
            ("contact_band", "Contact tolerance (pixels)", 5, 1, 100),
            ("contact_depth", "Patch depth (pixels)", 5, 1, 100),
            ("contact_width", "Width spread (pixels)", 10, 0, 100),
            ("contact_softness", "Softness (pixels)", 4, 0, 100),
            ("contact_density", "Density", 0.65, 0, 1),
            ("contact_strength", "Strength (animatable)", 1, 0, 1),
        ):
            knob = nuke.Double_Knob(name, label)
            knob.setRange(low, high)
            group.addKnob(knob)
            knob.setValue(default)
        group["contact_band"].setTooltip("Alpha touching the floor is strongest and fades to zero at this height above Ground contact Y. Start at 5 pixels. Keep the ground line fixed for a level floor; tracking raised feet defeats the contact test.")
        group["contact_width"].setTooltip("Extra horizontal blur spreads each footprint without moving it sideways.")
        group["contact_strength"].setTooltip("Animate down for jumps or incorrect contact. This affects the whole contact layer, not individual feet.")
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
            expanded = _expand_shadow(projection, "ExpandCastShadow")
            blur = nuke.nodes.Blur(name="ShadowSoftness", inputs=[expanded], channels="alpha")
            blur["size"].setExpression("parent.softness")
            distance_blur = _distance_softness(expanded, blur, "Cast", CAST_DISTANCE,
                                               "max(parent.softness,0)", "max(parent.softness,0)")
            color = nuke.nodes.Expression(name="ShadowColorAndDensity", inputs=[distance_blur])
            for knob, channel in (("expr0", "r"), ("expr1", "g"), ("expr2", "b")):
                color[knob].setValue("parent.tint.%s*clamp(a*parent.density,0,1)" % channel)
            color["expr3"].setValue("clamp(a*parent.density,0,1)")
            # Overhead-style branch uses the whole silhouette, independent of
            # cast direction/falloff. X stays unchanged to follow lateral motion.
            under = nuke.nodes.Transform(name="UnderCharacterProjection", inputs=[silhouette])
            under["center"].setValue(0, 0)
            under["center"].setExpression("parent.contact_y", 1)
            under["scale"].setValue(1, 0)
            under["scale"].setExpression("max(parent.under_depth,0.001)", 1)
            under["translate"].setExpression("parent.under_offset.x", 0)
            under["translate"].setExpression("parent.under_offset.y", 1)
            under_expanded = _expand_shadow(under, "ExpandUnderShadow")
            under_blur = nuke.nodes.Blur(name="UnderCharacterSoftness", inputs=[under_expanded], channels="alpha")
            under_blur["size"].setExpression("max(parent.under_width,0)+max(parent.under_softness,0)", 0)
            under_blur["size"].setExpression("max(parent.under_softness,0)", 1)
            under_distance_blur = _distance_softness(
                under_expanded, under_blur, "Under", UNDER_DISTANCE,
                "max(parent.under_width,0)+max(parent.under_softness,0)",
                "max(parent.under_softness,0)")
            under_color = nuke.nodes.Expression(name="UnderCharacterColor", inputs=[under_distance_blur])
            for knob, channel in (("expr0", "r"), ("expr1", "g"), ("expr2", "b")):
                under_color[knob].setValue("parent.tint.%s*clamp(a*parent.under_density,0,1)" % channel)
            under_color["expr3"].setValue("clamp(a*parent.under_density,0,1)")
            base_shadow = nuke.nodes.Switch(name="ShadowMode")
            base_shadow.setInput(0, color)
            base_shadow.setInput(1, under_color)
            base_shadow["which"].setExpression("parent.shadow_mode")
            # Separate branch: isolate the feet before compressing vertically.
            # X is unchanged so footprints follow the moving input silhouette.
            foot_band = nuke.nodes.Expression(name="ContactFootBand", inputs=[silhouette])
            foot_band["expr3"].setValue(CONTACT_MASK)
            flatten = nuke.nodes.Transform(name="FlattenContact", inputs=[foot_band])
            flatten["center"].setValue(0, 0)
            flatten["center"].setExpression("parent.contact_y", 1)
            flatten["scale"].setValue(1, 0)
            flatten["scale"].setExpression("max(parent.contact_depth,1)/max(parent.contact_band,1)", 1)
            contact_blur = nuke.nodes.Blur(name="ContactSoftness", inputs=[flatten], channels="alpha")
            contact_blur["size"].setExpression("max(parent.contact_width,0)+max(parent.contact_softness,0)", 0)
            contact_blur["size"].setExpression("max(parent.contact_softness,0)", 1)
            contact_color = nuke.nodes.Expression(name="ContactColorAndDensity", inputs=[contact_blur])
            for knob, channel in (("expr0", "r"), ("expr1", "g"), ("expr2", "b")):
                contact_color[knob].setValue("parent.tint.%s*(%s)" % (channel, CONTACT_ALPHA))
            contact_color["expr3"].setValue(CONTACT_ALPHA)
            combined = nuke.nodes.Merge2(name="ContactOverCast", operation="over")
            combined.setInput(0, base_shadow)  # B: selected broad shadow
            combined.setInput(1, contact_color)  # A: contact shadow
            output_switch = nuke.nodes.Switch(name="ContactEnabled")
            output_switch.setInput(0, base_shadow)
            output_switch.setInput(1, combined)
            output_switch["which"].setExpression("parent.contact_enabled")
            nuke.nodes.Output(inputs=[output_switch])
        finally:
            group.end()
        if source is not None:
            group.setXYpos(source.xpos() + 150, source.ypos() + 100)
        group["contact_y"].setTooltip("Set this to the floor in image pixels. For a sideways walk on a level floor, hold it fixed so raised feet leave the contact tolerance. Follow Feet estimates silhouette bottom, not physical ground.")
        group.showControlPanel()
    return group


def install_menu():
    menu = nuke.menu("Nuke")
    if menu.findItem("Nuke Tools/Character Shadow") is None:
        menu.addCommand("Nuke Tools/Character Shadow", create_shadow)
