# Copyright (C) 2026 Ibrahim Badawy
# This file is covered by the GNU General Public License, version 2 or later.

import json
import os
import tempfile
import threading
from urllib.request import Request, urlopen

import addonHandler
import core
import gui
from logHandler import log
import ui
import wx


_ADDON_NAME = "AccessibleTerminalViewer"
_LATEST_RELEASE_URL = (
	"https://api.github.com/repos/ibrasonic/AccessibleTerminalViewer/releases/latest"
)
_REQUEST_HEADERS = {
	"Accept": "application/vnd.github+json",
	"User-Agent": "AccessibleTerminalViewer-NVDA-Addon",
	"X-GitHub-Api-Version": "2022-11-28",
}


def parseVersion(version):
	numericParts = []
	for part in version.lstrip("vV").split("."):
		digits = "".join(character for character in part if character.isdigit())
		if not digits:
			break
		numericParts.append(int(digits))
	return tuple(numericParts)


def isNewerVersion(candidate, current):
	return parseVersion(candidate) > parseVersion(current)


def _getCurrentVersion():
	return addonHandler.getCodeAddon().manifest["version"]


def _getLatestRelease():
	request = Request(_LATEST_RELEASE_URL, headers=_REQUEST_HEADERS)
	with urlopen(request, timeout=15) as response:
		data = json.load(response)
	version = data["tag_name"].lstrip("vV")
	asset = next(
		(
			item
			for item in data.get("assets", [])
			if item["name"].lower().endswith(".nvda-addon")
		),
		None,
	)
	if asset is None:
		raise RuntimeError("The latest GitHub release has no NVDA add-on package")
	return {
		"version": version,
		"downloadUrl": asset["browser_download_url"],
		"releaseUrl": data["html_url"],
	}


class UpdateManager:
	def __init__(self):
		self._checking = False
		self._updateOffered = False

	def check(self, automatic=False):
		if self._checking:
			if not automatic:
				ui.message(_("An update check is already in progress."))
			return
		self._checking = True
		threading.Thread(
			target=self._checkWorker,
			args=(automatic,),
			name="AccessibleTerminalViewerUpdateCheck",
			daemon=True,
		).start()

	def _checkWorker(self, automatic):
		try:
			release = _getLatestRelease()
			updateAvailable = isNewerVersion(release["version"], _getCurrentVersion())
		except Exception:
			log.error("Unable to check for AccessibleTerminalViewer updates", exc_info=True)
			wx.CallAfter(self._checkFinished, automatic, None, None)
			return
		wx.CallAfter(self._checkFinished, automatic, updateAvailable, release)

	def _checkFinished(self, automatic, updateAvailable, release):
		self._checking = False
		if updateAvailable:
			if not self._updateOffered:
				self._updateOffered = True
				self._offerUpdate(release)
			return
		if updateAvailable is False and not automatic:
			ui.message(_("AccessibleTerminalViewer is up to date."))
		elif updateAvailable is None and not automatic:
			ui.message(_("Unable to check for updates. Check your internet connection and try again."))

	def _offerUpdate(self, release):
		result = gui.messageBox(
			_(
				"AccessibleTerminalViewer version {version} is available. "
				"Do you want to download and install it now?"
			).format(version=release["version"]),
			_("AccessibleTerminalViewer update"),
			wx.YES_NO | wx.ICON_INFORMATION,
		)
		if result != wx.YES:
			return
		ui.message(_("Downloading AccessibleTerminalViewer update."))
		threading.Thread(
			target=self._downloadWorker,
			args=(release,),
			name="AccessibleTerminalViewerUpdateDownload",
			daemon=True,
		).start()

	def _downloadWorker(self, release):
		path = None
		try:
			request = Request(release["downloadUrl"], headers=_REQUEST_HEADERS)
			with urlopen(request, timeout=30) as response:
				with tempfile.NamedTemporaryFile(
					prefix="AccessibleTerminalViewer-",
					suffix=".nvda-addon",
					delete=False,
				) as package:
					path = package.name
					while chunk := response.read(64 * 1024):
						package.write(chunk)
			bundle = addonHandler.AddonBundle(path)
			if bundle.manifest["name"] != _ADDON_NAME:
				raise RuntimeError("Downloaded package has an unexpected add-on name")
			if bundle.manifest["version"] != release["version"]:
				raise RuntimeError("Downloaded package version does not match the GitHub release")
		except Exception:
			log.error("Unable to download AccessibleTerminalViewer update", exc_info=True)
			if path and os.path.exists(path):
				os.remove(path)
			wx.CallAfter(
				ui.message,
				_("The AccessibleTerminalViewer update could not be downloaded or verified."),
			)
			return
		wx.CallAfter(self._installUpdate, bundle, path)

	def _installUpdate(self, bundle, path):
		try:
			currentAddon = next(
				(
					addon
					for addon in addonHandler.getAvailableAddons()
					if not addon.isPendingRemove and addon.manifest["name"] == _ADDON_NAME
				),
				None,
			)
			if currentAddon:
				currentAddon.requestRemove()
			addonHandler.installAddonBundle(bundle)
		except Exception:
			log.error("Unable to install AccessibleTerminalViewer update", exc_info=True)
			gui.messageBox(
				_("The update could not be installed."),
				_("AccessibleTerminalViewer update"),
				wx.OK | wx.ICON_ERROR,
			)
			return
		finally:
			try:
				os.remove(path)
			except OSError:
				log.debugWarning("Unable to remove downloaded update package", exc_info=True)

		result = gui.messageBox(
			_("The update was installed. Restart NVDA now to finish updating?"),
			_("AccessibleTerminalViewer update"),
			wx.YES_NO | wx.ICON_INFORMATION,
		)
		if result == wx.YES:
			core.restart()
