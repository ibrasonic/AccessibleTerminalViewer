import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
	Path(__file__).parents[1]
	/ "addon"
	/ "globalPlugins"
	/ "terminalVirtualView"
	/ "semantic.py"
)
SPEC = importlib.util.spec_from_file_location("semantic", MODULE_PATH)
semantic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(semantic)


class BuildDocumentTests(unittest.TestCase):
	def test_prompts_become_headings_and_content_is_escaped(self):
		document = semantic.buildDocument(
			"C:\\Users\\Ada> echo <ready>\n<ready>\nPS C:\\Users\\Ada> Get-Date",
			"Command Prompt & PowerShell",
		)

		self.assertIn("<h1>Command Prompt &amp; PowerShell</h1>", document)
		self.assertIn("<h2>C:\\Users\\Ada&gt; echo &lt;ready&gt;</h2>", document)
		self.assertIn("<h2>PS C:\\Users\\Ada&gt; Get-Date</h2>", document)
		self.assertIn("&lt;ready&gt;", document)
		self.assertNotIn("<ready>", document)

	def test_powershell_fixed_width_output_becomes_table(self):
		document = semantic.buildDocument(
			"PS C:\\> Get-Process\n"
			"Name          Id  CPU\n"
			"----          --  ---\n"
			"nvda        1200  4.2\n"
			"pwsh        1300  1.1",
			"PowerShell",
		)

		self.assertIn("<table>", document)
		self.assertIn('<th scope="col">Name</th>', document)
		self.assertIn("<td>nvda</td>", document)
		self.assertIn("<td>1200</td>", document)

	def test_pipe_output_becomes_table(self):
		document = semantic.buildDocument(
			"| Name | Status |\n| --- | --- |\n| API | Running |",
			"Terminal",
		)

		self.assertEqual(document.count("<table>"), 1)
		self.assertIn('<th scope="col">Status</th>', document)
		self.assertIn("<td>Running</td>", document)
		self.assertNotIn("<td>---</td>", document)

	def test_lists_become_semantic_lists(self):
		document = semantic.buildDocument(
			"- first\n- second\n\n1. one\n2. two",
			"Terminal",
		)

		self.assertIn("<ul><li>first</li><li>second</li></ul>", document)
		self.assertIn("<ol><li>one</li><li>two</li></ol>", document)

	def test_ansi_sequences_are_removed(self):
		document = semantic.buildDocument("\x1b[31mError\x1b[0m", "Terminal")

		self.assertIn("<pre>Error</pre>", document)
		self.assertNotIn("\x1b", document)

	def test_blank_lines_are_removed(self):
		document = semantic.buildDocument(
			"\n\nC:\\> echo ready\n\n\nready\n   \n\n",
			"Command Prompt",
		)

		self.assertIn("<h2>C:\\&gt; echo ready</h2>", document)
		self.assertIn("<pre>ready</pre>", document)
		self.assertNotIn("<pre>\n", document)
		self.assertNotIn("\n\n", document)


if __name__ == "__main__":
	unittest.main()
