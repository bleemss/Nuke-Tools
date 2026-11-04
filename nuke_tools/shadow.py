"""Build an editable alpha-projected shadow using native Nuke nodes."""

import nuke


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
        for name, label, default, low, high in (
            ("reach", "Horizontal reach (pixels)", 250, -2000, 2000),
            ("length", "Ground projection", 0.35, -2, 2),
            ("softness", "Softness (pixels)", 15, 0, 200),
            ("density", "Density", 0.5, 0, 1),
        ):
            knob = nuke.Double_Knob(name, label)
            knob.setRange(low, high)
            group.addKnob(knob)
            knob.setValue(default)
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
            projection = nuke.nodes.CornerPin2D(name="GroundProjection", inputs=[silhouette])
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
