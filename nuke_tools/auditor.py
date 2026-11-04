"""Nuke-native panel; no third-party Python packages required."""

import nuke
import nukescripts

from .media import audit_frames, replace_prefix


class ReadAuditor(nukescripts.PythonPanel):
    def __init__(self):
        super().__init__("Read Node Auditor", "com.nuketools.ReadAuditor")
        self.selected = nuke.Boolean_Knob("selected_only", "Selected Read nodes only")
        self.scan = nuke.PyScript_Knob("scan", "Scan media")
        self.report = nuke.Multiline_Eval_String_Knob("report", "Results")
        self.report.setEnabled(False)
        self.old = nuke.String_Knob("old_prefix", "Old folder prefix")
        self.new = nuke.String_Knob("new_prefix", "New folder prefix")
        self.relink = nuke.PyScript_Knob("relink", "Preview relink…")
        for knob in (self.selected, self.scan, self.report, self.old, self.new, self.relink):
            self.addKnob(knob)

    def nodes(self):
        if self.selected.value():
            return [node for node in nuke.selectedNodes() if node.Class() == "Read"]
        return nuke.allNodes("Read", recurseGroups=True)

    def knobChanged(self, knob):
        if knob is self.scan:
            self.scan_media()
        elif knob is self.relink:
            self.relink_media()

    def scan_media(self):
        lines = []
        task = nuke.ProgressTask("Audit Read media")
        nodes = self.nodes()
        original_frame = nuke.frame()
        try:
            for index, node in enumerate(nodes):
                if task.isCancelled():
                    lines.append("Scan cancelled; results are partial.")
                    break
                task.setMessage(node.fullName())
                task.setProgress(int(100 * index / max(1, len(nodes))))
                try:
                    def resolve(frame):
                        if task.isCancelled():
                            raise InterruptedError("Scan cancelled")
                        nuke.frame(frame)
                        # Nuke resolves padding, expressions and frame-dependent knobs.
                        path = nuke.filename(node, nuke.REPLACE)
                        if not path:
                            raise ValueError("Empty or unresolved file path")
                        return path

                    result = audit_frames(resolve, int(node["first"].value()), int(node["last"].value()))
                    lines.append("{}: {} — {} unique files checked, {} missing".format(
                        node.fullName(), "MISSING" if result.missing else "OK",
                        result.checked, len(result.missing)))
                    lines.extend("  " + path for path in result.missing[:20])
                    if len(result.missing) > 20:
                        lines.append("  … {} more missing files".format(len(result.missing) - 20))
                except InterruptedError:
                    lines.append("Scan cancelled; results are partial.")
                    break
                except Exception as error:
                    lines.append("{}: ERROR — {}".format(node.fullName(), error))
        finally:
            nuke.frame(original_frame)
            del task
        self.report.setValue("\n".join(lines) or "No matching Read nodes.")

    def relink_media(self):
        changes = []
        try:
            for node in self.nodes():
                knob = node["file"]
                if knob.isAnimated() or knob.hasExpression():
                    continue
                old_path = knob.value()
                new_path = replace_prefix(old_path, self.old.value(), self.new.value())
                if new_path != old_path.replace("\\", "/"):
                    changes.append((node, old_path, new_path))
        except ValueError as error:
            nuke.message(str(error))
            return
        if not changes:
            nuke.message("No matching static paths. Animated and expression paths are skipped.")
            return
        preview = "\n\n".join("{}\n{}\n→ {}".format(node.fullName(), old, new)
                                for node, old, new in changes)
        if not nuke.ask("Relink {} Read nodes?\nAnimated and expression paths are skipped.\n\n{}".format(len(changes), preview)):
            return
        with nuke.Undo("Relink Read media"):
            for node, old, new in changes:
                node["file"].setValue(new)
        self.scan_media()


def show():
    ReadAuditor().showModalDialog()


def install_menu():
    menu = nuke.menu("Nuke")
    if menu.findItem("Nuke Tools/Read Node Auditor") is None:
        menu.addCommand("Nuke Tools/Read Node Auditor", show)
