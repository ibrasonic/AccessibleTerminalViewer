# Copyright (C) 2026 Ibrahim Badawy
# This file is covered by the GNU General Public License, version 2 or later.

from collections import deque
import threading

import addonHandler
import api
import core
import globalPluginHandler
import globalVars
from logHandler import log
import scriptHandler
import textInfos
import ui
import wx

from .semantic import buildDocument
from .updater import UpdateManager

addonHandler.initTranslation()

try:
	from globalCommands import SCRCAT_TEXTREVIEW
except ImportError:
	SCRCAT_TEXTREVIEW = None


_TERMINAL_APP_NAMES = {
	"cmd",
	"conhost",
	"openconsole",
	"powershell",
	"pwsh",
	"windowsterminal",
}
_TERMINAL_WINDOW_CLASSES = {
	"consolewindowclass",
	"termcontrol",
	"cascadiahostingwindow",
}
_MAX_OBJECTS_TO_SEARCH = 100
_TERMINAL_TEXT_WINDOW_CLASSES = {
	"consolewindowclass",
	"termcontrol",
}


def _objectIdentity(obj):
	appModule = getattr(obj, "appModule", None)
	appName = (getattr(appModule, "appName", "") or "").lower()
	windowClassName = (getattr(obj, "windowClassName", "") or "").lower()
	return appName, windowClassName


def _isTerminalObject(obj):
	appName, windowClassName = _objectIdentity(obj)
	return appName in _TERMINAL_APP_NAMES or windowClassName in _TERMINAL_WINDOW_CLASSES


def _iterDescendants(root):
	queue = deque([root])
	seen = set()
	while queue and len(seen) < _MAX_OBJECTS_TO_SEARCH:
		obj = queue.popleft()
		identity = id(obj)
		if identity in seen:
			continue
		seen.add(identity)
		yield obj
		child = getattr(obj, "simpleFirstChild", None)
		while child:
			queue.append(child)
			child = getattr(child, "simpleNext", None)


def _getText(obj):
	try:
		info = obj.makeTextInfo(textInfos.POSITION_FIRST)
		info.expand(textInfos.UNIT_STORY)
		text = getattr(info, "clipboardText", None)
		if text is None:
			text = info.text
	except (AttributeError, NotImplementedError, RuntimeError):
		log.debugWarning("Terminal object does not expose readable text", exc_info=True)
		return ""
	except Exception:
		log.error("Failed to retrieve text from a terminal object", exc_info=True)
		return ""
	return (text or "").replace("\0", " ").rstrip()


def _captureTerminal():
	focus = api.getFocusObject()
	foreground = api.getForegroundObject()
	ancestors = list(api.getFocusAncestors())
	context = [focus, *reversed(ancestors), foreground]
	if not any(_isTerminalObject(obj) for obj in context):
		return None, None

	seen = set()
	candidates = []
	for obj in context:
		_, windowClassName = _objectIdentity(obj)
		if windowClassName in _TERMINAL_TEXT_WINDOW_CLASSES and id(obj) not in seen:
			seen.add(id(obj))
			candidates.append(obj)
	if not candidates:
		for obj in _iterDescendants(foreground):
			_, windowClassName = _objectIdentity(obj)
			if windowClassName in _TERMINAL_TEXT_WINDOW_CLASSES and id(obj) not in seen:
				seen.add(id(obj))
				candidates.append(obj)
				break
	if not candidates:
		for obj in context:
			if _isTerminalObject(obj) and id(obj) not in seen:
				seen.add(id(obj))
				candidates.append(obj)

	for obj in candidates:
		text = _getText(obj)
		if text:
			title = getattr(foreground, "name", None) or _("Terminal")
			return text, title

	title = getattr(foreground, "name", None) or _("Terminal")
	return "", title


def _trustedHtml(html):
	return html


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = SCRCAT_TEXTREVIEW

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._updateManager = UpdateManager()
		self._buildingView = False
		self._updateTimer = core.callLater(
			10000,
			self._updateManager.check,
			automatic=True,
		)

	@scriptHandler.script(
		# Translators: Description of the command that opens terminal content in browse mode.
		description=_("Open terminal content as a structured virtual document"),
		gesture="kb:nvda+shift+v",
	)
	def script_openTerminalVirtualView(self, gesture):
		text, title = _captureTerminal()
		if text is None:
			ui.message(
				_("AccessibleTerminalViewer is available only in Command Prompt, PowerShell, and Windows Terminal."),
			)
			return
		if not text:
			ui.message(_("No terminal text is available."))
			return

		if self._buildingView:
			ui.message(_("The terminal virtual document is still being prepared."))
			return
		self._buildingView = True
		ui.message(_("Preparing the complete terminal virtual document."))
		threading.Thread(
			target=self._buildDocument,
			args=(text, title),
			name="AccessibleTerminalViewerDocumentBuilder",
			daemon=True,
		).start()

	def _buildDocument(self, text, title):
		try:
			document = buildDocument(text, title)
		except Exception:
			log.error("Unable to build the terminal virtual document", exc_info=True)
			wx.CallAfter(self._documentBuildFailed)
			return
		wx.CallAfter(self._showDocument, document, title)

	def _documentBuildFailed(self):
		self._buildingView = False
		ui.message(_("The terminal virtual document could not be created."))

	def _showDocument(self, document, title):
		self._buildingView = False
		ui.browseableMessage(
			message=document,
			title=_("AccessibleTerminalViewer: {title}").format(title=title),
			isHtml=True,
			closeButton=True,
			copyButton=True,
			sanitizeHtmlFunc=_trustedHtml,
		)

	@scriptHandler.script(
		# Translators: Description of the command that checks GitHub for add-on updates.
		description=_("Check AccessibleTerminalViewer for updates"),
	)
	def script_checkForUpdates(self, gesture):
		self._updateManager.check()


if globalVars.appArgs.secure:
	GlobalPlugin = globalPluginHandler.GlobalPlugin
