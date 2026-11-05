"""Editable native-node green despill and edge extension."""

import nuke

from .despill_math import EDGE_OPACITY_FACTOR, green_expression



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


def _native_extend(source):
    """Use the EdgeExtend interface reported by the user's Nuke 17 host."""
    node = nuke.nodes.EdgeExtend(name='NativeEdgeExtend', inputs=[source])
    node['channels'].setValue('rgba')
    node['matte'].setValue('Matte Alpha')
    # Despill runs on straight RGB; premultiplication happens once at output.
    node['sourceIsPremultiplied'].setValue(False)
    node['premultiply'].setValue(False)
    node['erode'].setExpression('max(parent.extend_erode,0)')
    node['detailAmount'].setExpression('max(parent.extend_detail,0)')
    node['disable'].setExpression('!parent.extend_enabled')
    return node


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
            ('extend_width', 'Replacement edge thickness (pixels)', 10, 200, 'Inward band where extended RGB replaces the despilled image. The eroded core is protected; RGB outside alpha can also be filled.'),
            ('extend_erode', 'Source erode (native)', 2.5, 200, 'Drives the native EdgeExtend Erode control, independently of the replacement band.'),
            ('extend_detail', 'Detail amount (native)', 2, 10, 'Drives the native EdgeExtend Detail Amount control; this is no longer a blend between two blur sizes.'),
            ('extend_mix', 'Extension amount', 1, 1, 'Blend original despilled edge colors with the extension.'),
            ('extend_opacity', 'Edge opacity', 1, 1, 'Opacity multiplier in the extension edge band: 1 preserves alpha; 0 removes the edge. Independent of Extension amount. The eroded core stays opaque where it was opaque.'),
        ):
            _slider(group, *args)
        output_premult = nuke.Boolean_Knob('output_premult', 'Premult output')
        output_premult.setValue(True)
        output_premult.setTooltip('On: multiply RGB by output alpha for compositing. Off: expose straight RGB, including extended colors outside alpha. The replacement mask protects the eroded core; Nuke EdgeExtend generates the surrounding fill. This toggle does not change alpha or Edge opacity.')
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
            fill = _native_extend(despilled)
            band = _expression(name='ExtensionBand', inputs=[inset])
            band['expr3'].setValue('(1-clamp(a,0,1))*clamp(parent.extend_mix,0,1)')
            extended = _mix(despilled, fill, band, 'ExtendEdgeColors')
            switch = nuke.nodes.Switch(name='ExtensionEnabled')
            switch.setInput(0, despilled)
            switch.setInput(1, extended)
            switch['which'].setExpression('parent.extend_enabled')
            restored = _copy_alpha(switch, incoming, 'RestoreOriginalAlpha')
            opacity_factor = _expression(name='EdgeOpacityFactor', inputs=[inset])
            opacity_factor['expr3'].setValue(EDGE_OPACITY_FACTOR)
            opacity_alpha = nuke.nodes.Merge2(name='EdgeOpacityAlpha', operation='multiply', channels='alpha')
            opacity_alpha.setInput(0, incoming)
            opacity_alpha.setInput(1, opacity_factor)
            adjusted = _copy_alpha(restored, opacity_alpha, 'ApplyEdgeOpacity')
            adjusted['disable'].setExpression('!parent.extend_enabled')
            result = nuke.nodes.Premult(name='OutputPremult', inputs=[adjusted], channels='rgb')
            result['disable'].setExpression('!parent.output_premult')
            view = nuke.nodes.Switch(name='Preview')
            view.setInput(0, result)
            for index, mask in ((1, core_mask), (2, band)):
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
