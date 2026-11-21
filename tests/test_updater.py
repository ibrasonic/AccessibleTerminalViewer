import ast
from pathlib import Path
import unittest


MODULE_PATH = (
	Path(__file__).parents[1]
	/ "addon"
	/ "globalPlugins"
	/ "terminalVirtualView"
	/ "updater.py"
)


def _loadVersionFunctions():
	module = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
	functions = [
		node
		for node in module.body
		if isinstance(node, ast.FunctionDef)
		and node.name in {"parseVersion", "isNewerVersion"}
	]
	namespace = {}
	exec(compile(ast.Module(body=functions, type_ignores=[]), str(MODULE_PATH), "exec"), namespace)
	return namespace["parseVersion"], namespace["isNewerVersion"]


parseVersion, isNewerVersion = _loadVersionFunctions()


class UpdateVersionTests(unittest.TestCase):
	def test_parses_release_tags(self):
		self.assertEqual(parseVersion("v1.2.3"), (1, 2, 3))

	def test_detects_newer_version(self):
		self.assertTrue(isNewerVersion("1.0.1", "1.0.0"))
		self.assertFalse(isNewerVersion("1.0.0", "1.0.0"))
		self.assertFalse(isNewerVersion("0.9.9", "1.0.0"))


if __name__ == "__main__":
	unittest.main()
