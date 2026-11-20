import tempfile, unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"app"))
import project_workspace

class WorkspaceTests(unittest.TestCase):
    def test_rejects_traversal(self):
        with self.assertRaises(ValueError):
            project_workspace.write_project_file("valid","../escape.txt","x")

    def test_creates_project_inside_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            original=project_workspace.ROOT
            project_workspace.ROOT=Path(temp)
            try:
                path=project_workspace.create_project("demo")
                self.assertTrue((path/"README.md").exists())
            finally:
                project_workspace.ROOT=original

if __name__=="__main__":
    unittest.main()
