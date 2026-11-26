"""Structural regression tests for the JARVIS EXE desktop interface."""
import ast
import unittest
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"


class DashboardInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DASHBOARD.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.methods = {
            node.name: node for node in ast.walk(cls.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_dashboard_source_compiles(self):
        compile(self.source, str(DASHBOARD), "exec")

    def test_build_keeps_all_core_interaction_widgets(self):
        build = self.methods["_build"]
        assigned = {
            target.attr
            for node in ast.walk(build)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        }
        expected = {
            "status_label", "clock", "date_label", "hero", "chat",
            "agent_picker", "entry", "voice_button", "voice_state",
            "ai_state", "net_state", "security_state", "cpu_state",
            "mem_state", "disk_state", "battery_state", "location", "footer",
        }
        self.assertTrue(expected.issubset(assigned), expected - assigned)

    def test_interface_retains_navigation_and_chat_actions(self):
        build_source = ast.get_source_segment(self.source, self.methods["_build"])
        for required in (
            "self.focus_chat", "self.new_project", "self.tools",
            "self.open_security_lab", "self.settings", "self.listen",
            "self.send", "self.agent_var", "self.manage_memory",
        ):
            with self.subTest(required=required):
                self.assertIn(required, build_source)

    def test_hero_animation_adapts_to_available_space(self):
        hero_source = ast.get_source_segment(self.source, self.methods["draw_core"])
        self.assertIn("canvas.winfo_width()", hero_source)
        self.assertIn("canvas.winfo_height()", hero_source)
        self.assertIn("self.root.after(100, self.draw_core)", hero_source)

    def test_accessible_scrollbar_is_attached_to_conversation(self):
        build_source = ast.get_source_segment(self.source, self.methods["_build"])
        self.assertIn("command=self.chat.yview", build_source)
        self.assertIn("yscrollcommand=scroll.set", build_source)


if __name__ == "__main__":
    unittest.main()
