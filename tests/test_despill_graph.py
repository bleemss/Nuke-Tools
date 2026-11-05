"""Check expression routing without claiming to render a Nuke graph."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class ExpressionRoutingTests(unittest.TestCase):
    def test_explicit_rgba_routing_and_identity(self):
        knobs = {name + str(i): Mock() for name in ('channel', 'expr') for i in range(4)}
        node = Mock()
        node.__getitem__ = Mock(side_effect=knobs.__getitem__)
        factory = Mock(return_value=node)
        fake_nuke = SimpleNamespace(nodes=SimpleNamespace(Expression=factory))
        path = Path(__file__).resolve().parents[1] / 'nuke_tools' / 'despill.py'
        spec = importlib.util.spec_from_file_location('nuke_tools._despill_routing_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'nuke': fake_nuke}):
            spec.loader.exec_module(module)
        self.assertIs(module._expression(name='Test'), node)
        factory.assert_called_once_with(name='Test')
        for i, (channel, identity) in enumerate(zip(
                ('rgba.red', 'rgba.green', 'rgba.blue', 'rgba.alpha'), 'rgba')):
            knobs['channel%d' % i].setValue.assert_called_once_with(channel)
            knobs['expr%d' % i].setValue.assert_called_once_with(identity)
