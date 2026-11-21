import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "addon" / "installTasks.py"


class InstallTasksTests(unittest.TestCase):
	def test_legacy_addon_is_scheduled_for_removal(self):
		legacyAddon = SimpleNamespace(
			manifest={"name": "terminalVirtualView"},
			isPendingRemove=False,
			requestRemove=lambda: setattr(legacyAddon, "removed", True),
			removed=False,
		)
		currentAddon = SimpleNamespace(
			manifest={"name": "AccessibleTerminalViewer"},
			isPendingRemove=False,
			requestRemove=lambda: setattr(currentAddon, "removed", True),
			removed=False,
		)
		addonHandler = SimpleNamespace(
			getAvailableAddons=lambda: [legacyAddon, currentAddon],
		)
		logHandler = SimpleNamespace(
			log=SimpleNamespace(error=lambda *args, **kwargs: None),
		)

		with patch.dict(
			"sys.modules",
			{"addonHandler": addonHandler, "logHandler": logHandler},
		):
			spec = importlib.util.spec_from_file_location("installTasks", MODULE_PATH)
			module = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(module)
			module.onInstall()

		self.assertTrue(legacyAddon.removed)
		self.assertFalse(currentAddon.removed)


if __name__ == "__main__":
	unittest.main()
