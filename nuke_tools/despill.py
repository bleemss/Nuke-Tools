"""Editable native-node green despill and edge extension."""

import nuke

from .despill_math import EDGE_OPACITY_FACTOR, NORMALIZE, green_expression



def _expression(**kwargs):
    """Route each expression explicitly; do not depend on host defaults."""
    node = nuke.nodes.Expression(**kwargs)
    for index, (channel, identity) in enumerate(zip(
            ('rgba.red', 'rgba.green', 'rgba.blue', 'rgba.alpha'), 'rgba')):
        node['channel%d' % index].setValue(channel)
        node['expr%d' % index].setValue(identity)
    return node

def _slider(group, name, label, value, maximum, tooltip):
    knob = nuke.Double_Knob(name, label)
    knob.setRange(0, maximum)
    knob.setValue(value)
    knob.setTooltip(tooltip)
    group.addKnob(knob)


def _copy_alpha(rgb, alpha, name):
    node = nuke.nodes.Copy(name=name)
    node.setInput(0, rgb)
    node.setInput(1, alpha)
    node['from0'].setValue('rgba.alpha')
    node['to0'].setValue('rgba.alpha')
    return node


def _mix(base, changed, mask, name):
    node = nuke.nodes.Keymix(name=name, channels='rgb')
    node.setInput(0, base)
    node.setInput(1, changed)
    node.setInput(2, mask)
    return node


def _erode(source, name, width):
    node = nuke.nodes.Dilate(name=name, inputs=[source], channels='alpha')
    node['size'].setExpression('-max(parent.%s,0)' % width)
    return node


def _fill(source, name, radius):
    blur = nuke.nodes.Blur(name=name + 'WeightedBlur', inputs=[source], channels='rgba')
    blur['size'].setExpression(radius)
    normalized = _expression(name=name + 'Normalize', inputs=[blur])
    for index, channel in enumerate('rgb'):
        normalized['expr%d' % index].setValue(NORMALIZE.format(channel=channel))
    return normalized


def create_despill():
    """Create a connected group; the input must already have a foreground alpha."""
    selected = nuke.selectedNodes()
    source = selected[0] if len(selected) == 1 else None
    with nuke.Undo('Create Despill and Edge Extend'):
        group = nuke.nodes.Group(name='DespillEdgeExtend')
        if source is not None:
            group.setInput(0, source)
        group.addKnob(nuke.Tab_Knob('despill_tab', '1. Despill'))
        group.addKnob(nuke.Text_Knob('usage', '', 'Input: keyed foreground with alpha. Green objects also trigger detection.'))
        premult = nuke.Boolean_Knob('input_premult', 'Input is premultiplied')
        premult.setValue(True)
        group.addKnob(premult)
        enabled = nuke.Boolean_Knob('despill_enabled', 'Enable despill')
        enabled.setValue(True)
        group.addKnob(enabled)
        for args in (
            ('edge_width', 'Edge thickness (pixels)', 5, 100, 'Inward alpha erosion defines the core. Larger values assign more pixels to edge correction.'),
            ('core_strength', 'Core despill', 0.5, 1, 'Amount of detected excess green removed in the core.'),
            ('edge_strength', 'Edge despill', 1, 1, 'Amount of detected excess green removed in the edge band.'),
            ('balance', 'Red / blue reference', 0.5, 1, '0 uses red; 1 uses blue. Green above this reference is detected automatically.'),
            ('threshold', 'Green tolerance', 0, 1, 'Excess green below this scene-linear amount is preserved.'),
        ):
            _slider(group, *args)
        group.addKnob(nuke.Tab_Knob('extend_tab', '2. Edge Extend'))
        enabled = nuke.Boolean_Knob('extend_enabled', 'Enable edge extend')
        enabled.setValue(False)
        group.addKnob(enabled)
        for args in (
            ('extend_width', 'Edge thickness (pixels)', 10, 200, 'Inset used both to exclude contaminated source colors and define the replacement band.'),
            ('extend_reach', 'Color reach (pixels)', 30, 400, 'Blur size used to spread inset foreground colors. Increase if the fill cannot reach the edge.'),
            ('extend_detail', 'Replicate local detail', 0.75, 1, '0 uses a broad smooth fill; 1 uses a smaller local fill where available. Does not synthesize hidden texture.'),
            ('extend_mix', 'Extension amount', 1, 1, 'Blend original despilled edge colors with the extension.'),
            ('extend_opacity', 'Edge opacity', 1, 1, 'Opacity multiplier in the extension edge band: 1 preserves alpha; 0 removes the edge. Independent of Extension amount. The eroded core stays opaque where it was opaque.'),
        ):
            _slider(group, *args)
        output_premult = nuke.Boolean_Knob('output_premult', 'Premult output')
        output_premult.setValue(True)
        output_premult.setTooltip('On: multiply RGB by output alpha for compositing. Off: expose straight RGB, including extended colors outside alpha. The extension preserves the eroded core and fills only within Color reach. This toggle does not change alpha or Edge opacity.')
        group.addKnob(output_premult)
        group.addKnob(nuke.Enumeration_Knob('preview', 'View', ['Result', 'Despill edge mask', 'Extension mask']))
        group.begin()
        try:
            incoming = nuke.nodes.Input(name='KeyedForeground')
            unpremult = nuke.nodes.Unpremult(name='InputUnpremult', inputs=[incoming], channels='rgb')
            unpremult['disable'].setExpression('!parent.input_premult')
            core_mask = _erode(incoming, 'CoreMask', 'edge_width')
            core = _expression(name='CoreDespill', inputs=[unpremult])
            core['expr1'].setValue(green_expression('core_strength'))
            edge = _expression(name='EdgeDespill', inputs=[unpremult])
            edge['expr1'].setValue(green_expression('edge_strength'))
            corrected = _mix(edge, core, core_mask, 'SeparateCoreAndEdge')
            despilled = nuke.nodes.Switch(name='DespillEnabled')
            despilled.setInput(0, unpremult)
            despilled.setInput(1, corrected)
            despilled['which'].setExpression('parent.despill_enabled')
            inset = _erode(incoming, 'CleanColorSourceMask', 'extend_width')
            weighted = _copy_alpha(despilled, inset, 'InsetAlpha')
            weighted = nuke.nodes.Premult(name='WeightCleanColors', inputs=[weighted], channels='rgb')
            broad = _fill(weighted, 'BroadFill', 'max(parent.extend_reach,0)')
            local = _fill(weighted, 'LocalFill', 'max(parent.extend_reach,0)/3')
            # A local fill with no support falls back to the broad fill.
            detail_mask = _expression(name='DetailSupport', inputs=[local])
            detail_mask['expr3'].setValue('a>0.000001 ? clamp(parent.extend_detail,0,1) : 0')
            fill = _mix(broad, local, detail_mask, 'DetailBlend')
            # Carry broad support so empty/fully-eroded mattes retain their RGB.
            fill = _copy_alpha(fill, broad, 'FillSupport')
            band = _expression(name='ExtensionBand', inputs=[inset])
            band['expr3'].setValue('(1-clamp(a,0,1))*clamp(parent.extend_mix,0,1)')
            support = _expression(name='ValidFill', inputs=[fill])
            support['expr3'].setValue('a>0.000001 ? 1 : 0')
            valid_band = nuke.nodes.Merge2(name='SupportedExtensionBand', operation='multiply', channels='alpha')
            valid_band.setInput(0, band)
            valid_band.setInput(1, support)
            extended = _mix(despilled, fill, valid_band, 'ExtendEdgeColors')
            switch = nuke.nodes.Switch(name='ExtensionEnabled')
            switch.setInput(0, despilled)
            switch.setInput(1, extended)
            switch['which'].setExpression('parent.extend_enabled && parent.extend_width>0 && parent.extend_reach>0')
            restored = _copy_alpha(switch, incoming, 'RestoreOriginalAlpha')
            opacity_factor = _expression(name='EdgeOpacityFactor', inputs=[inset])
            opacity_factor['expr3'].setValue(EDGE_OPACITY_FACTOR)
            opacity_alpha = nuke.nodes.Merge2(name='EdgeOpacityAlpha', operation='multiply', channels='alpha')
            opacity_alpha.setInput(0, incoming)
            opacity_alpha.setInput(1, opacity_factor)
            adjusted = _copy_alpha(restored, opacity_alpha, 'ApplyEdgeOpacity')
            adjusted['disable'].setExpression('!parent.extend_enabled || parent.extend_width<=0 || parent.extend_reach<=0')
            result = nuke.nodes.Premult(name='OutputPremult', inputs=[adjusted], channels='rgb')
            result['disable'].setExpression('!parent.output_premult')
            view = nuke.nodes.Switch(name='Preview')
            view.setInput(0, result)
            for index, mask in ((1, core_mask), (2, valid_band)):
                display = _expression(name='MaskPreview%d' % index, inputs=[mask])
                for channel in range(3):
                    display['expr%d' % channel].setValue('1-clamp(a,0,1)' if index == 1 else 'clamp(a,0,1)')
                display['expr3'].setValue('1')
                view.setInput(index, display)
            view['which'].setExpression('parent.preview')
            nuke.nodes.Output(inputs=[view])
        finally:
            group.end()
        if source is not None:
            group.setXYpos(source.xpos(), source.ypos() + 100)
        group.showControlPanel()
    return group


def install_menu():
    menu = nuke.menu('Nuke')
    if menu.findItem('Nuke Tools/Despill and Edge Extend') is None:
        menu.addCommand('Nuke Tools/Despill and Edge Extend', create_despill)
