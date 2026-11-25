import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from agents import names, system_instruction

class AgentTests(unittest.TestCase):
    def test_all_specialists_have_instructions(self):
        expected = {"Geral", "Pesquisa", "Programação", "Flutter/Dart", "Estudos", "Escrita", "Planejamento", "Análise", "Visão"}
        self.assertEqual(set(names()), expected)
        for name in expected:
            self.assertIn("AGENTE ATIVO", system_instruction(name))

    def test_unknown_agent_falls_back_to_general(self):
        self.assertEqual(system_instruction("não existe"), system_instruction("Geral"))

if __name__ == "__main__":
    unittest.main()
