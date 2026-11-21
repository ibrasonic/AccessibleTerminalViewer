# Copyright (C) 2026 Ibrahim Badawy
# This file is covered by the GNU General Public License, version 2 or later.

import addonHandler
from logHandler import log


_LEGACY_ADDON_NAME = "terminalVirtualView"


def onInstall():
	for addon in addonHandler.getAvailableAddons():
		if (
			addon.manifest.get("name") == _LEGACY_ADDON_NAME
			and not addon.isPendingRemove
		):
			try:
				addon.requestRemove()
			except Exception:
				log.error(
					"Unable to schedule the legacy Terminal Virtual View add-on for removal",
					exc_info=True,
				)
