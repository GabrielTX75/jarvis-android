import unittest

from core import CommandRouter, ModuleRegistry, ModuleStatus


class CoreTests(unittest.TestCase):
    def test_registry_tracks_capabilities_only_when_available(self):
        registry = ModuleRegistry()
        registry.register(ModuleStatus("maps", "Maps", ("routes", "places"), True))
        registry.register(ModuleStatus("calendar", "Calendar", ("events",), False, "not configured"))
        self.assertEqual([m.module_id for m in registry.providers_for("routes")], ["maps"])
        self.assertEqual(registry.providers_for("events"), ())

    def test_duplicate_module_is_rejected(self):
        registry = ModuleRegistry()
        registry.register(ModuleStatus("voice", "Voice", ("speech",), True))
        with self.assertRaises(ValueError):
            registry.register(ModuleStatus("VOICE", "Voice duplicate", ("speech",), True))

    def test_router_runs_by_priority_and_stops_when_handled(self):
        calls = []
        router = CommandRouter()
        router.register("later", lambda _text: calls.append("later") or True, priority=20)
        router.register("first", lambda _text: calls.append("first") or True, priority=10)
        self.assertTrue(router.dispatch("hello"))
        self.assertEqual(calls, ["first"])

    def test_router_falls_through_when_not_handled(self):
        router = CommandRouter()
        router.register("no", lambda _text: False)
        self.assertFalse(router.dispatch("hello"))


if __name__ == "__main__":
    unittest.main()
