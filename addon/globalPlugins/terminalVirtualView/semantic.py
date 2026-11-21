# Copyright (C) 2026 Ibrahim Badawy
# This file is covered by the GNU General Public License, version 2 or later.

from html import escape
import re
import unicodedata


_ANSI_SEQUENCE = re.compile(
	r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))",
)
_PROMPT = re.compile(
	r"^(?:"
	r"PS\s+.+?>"
	r"|(?:[A-Za-z]:|\\\\)[^>]*>"
	r"|(?:\([^)]+\)\s*)?[\w.-]+@[\w.-]+:[^$#]*[$#]"
	r")(?:\s.*)?$",
	re.IGNORECASE,
)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$")
_NUMBERED_LIST_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_SEPARATOR_CELL = re.compile(r"^\s*:?[=\-─—]{2,}:?\s*$")
_COLUMN_RUN = re.compile(r"[=\-─—]{2,}")
_BOX_BORDER = re.compile(r"^[\s┌┬┐├┼┤└┴┘╔╦╗╠╬╣╚╩╝═─━+\-=]+$")
_BRAILLE_BLANK = "\u2800"


def _normalize(text):
	text = _ANSI_SEQUENCE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
	return text.replace("\0", " ")


def _normalizeLine(line):
	normalized = []
	for character in line.expandtabs(4):
		category = unicodedata.category(character)
		if character == _BRAILLE_BLANK or category.startswith("Z"):
			normalized.append(" ")
		elif category in {"Cc", "Cf"}:
			continue
		else:
			normalized.append(character)
	return "".join(normalized).rstrip()


def _isPrompt(line):
	return bool(_PROMPT.match(line.strip()))


def _splitPipeRow(line):
	normalized = re.sub(r"[│┃║]", "|", line).strip()
	if normalized.startswith("|"):
		normalized = normalized[1:]
	if normalized.endswith("|"):
		normalized = normalized[:-1]
	return [cell.strip() for cell in normalized.split("|")]


def _looksLikePipeRow(line):
	normalized = re.sub(r"[│┃║]", "|", line)
	return normalized.count("|") >= 2 and not _BOX_BORDER.match(normalized)


def _isSeparatorRow(cells):
	return bool(cells) and all(_SEPARATOR_CELL.match(cell) for cell in cells)


def _renderTable(rows, header=True):
	if not rows:
		return ""
	columnCount = max(len(row) for row in rows)
	normalizedRows = [row + [""] * (columnCount - len(row)) for row in rows]
	parts = ["<table>"]
	start = 0
	if header:
		parts.append("<thead><tr>")
		parts.extend(f"<th scope=\"col\">{escape(cell)}</th>" for cell in normalizedRows[0])
		parts.append("</tr></thead>")
		start = 1
	if start < len(normalizedRows):
		parts.append("<tbody>")
		for row in normalizedRows[start:]:
			parts.append("<tr>")
			parts.extend(f"<td>{escape(cell)}</td>" for cell in row)
			parts.append("</tr>")
		parts.append("</tbody>")
	parts.append("</table>")
	return "".join(parts)


def _parsePipeTable(lines, start):
	rows = []
	index = start
	while index < len(lines) and _looksLikePipeRow(lines[index]):
		rows.append(_splitPipeRow(lines[index]))
		index += 1
	if len(rows) < 2:
		return None

	width = len(rows[0])
	if width < 2 or any(len(row) != width for row in rows):
		return None
	if len(rows) > 1 and _isSeparatorRow(rows[1]):
		del rows[1]
	return _renderTable(rows), index


def _splitFixedWidthRow(line, runs):
	boundaries = [
		(left.end() + right.start()) // 2
		for left, right in zip(runs, runs[1:])
	]
	cells = []
	columnStart = 0
	for columnEnd in [*boundaries, None]:
		cells.append(line[columnStart:columnEnd].strip())
		columnStart = columnEnd
	return cells


def _parseFixedWidthTable(lines, start):
	if start + 1 >= len(lines):
		return None
	runs = list(_COLUMN_RUN.finditer(lines[start + 1]))
	if len(runs) < 2:
		return None

	rows = [_splitFixedWidthRow(lines[start], runs)]
	index = start + 2
	while index < len(lines):
		line = lines[index]
		if not line.strip() or _isPrompt(line):
			break
		if _COLUMN_RUN.fullmatch(line.strip()):
			index += 1
			continue
		row = _splitFixedWidthRow(line, runs)
		if sum(bool(cell) for cell in row) < 1:
			break
		rows.append(row)
		index += 1
	if len(rows) < 2:
		return None
	return _renderTable(rows), index


def _renderPreformatted(lines):
	return f"<pre>{escape(chr(10).join(lines))}</pre>"


def buildDocument(text, title):
	lines = [
		normalizedLine
		for line in _normalize(text).split("\n")
		if (normalizedLine := _normalizeLine(line)).strip()
	]
	parts = [
		"<!DOCTYPE html><html><head><meta charset=\"utf-8\">",
		"<style>h1,h2,pre,table,ul,ol{margin-top:0;margin-bottom:0}</style>",
		"<title>",
		escape(title),
		"</title></head><body><main>",
		f"<h1>{escape(title)}</h1>",
	]
	index = 0
	plainLines = []

	def flushPlainLines():
		if plainLines:
			parts.append(_renderPreformatted(plainLines))
			plainLines.clear()

	while index < len(lines):
		line = lines[index]
		if _isPrompt(line):
			flushPlainLines()
			parts.append(f"<h2>{escape(line.strip())}</h2>")
			index += 1
			continue

		pipeTable = _parsePipeTable(lines, index)
		if pipeTable:
			flushPlainLines()
			table, index = pipeTable
			parts.append(table)
			continue

		fixedTable = _parseFixedWidthTable(lines, index)
		if fixedTable:
			flushPlainLines()
			table, index = fixedTable
			parts.append(table)
			continue

		listMatch = _LIST_ITEM.match(line)
		if listMatch:
			flushPlainLines()
			ordered = bool(_NUMBERED_LIST_ITEM.match(line))
			tag = "ol" if ordered else "ul"
			items = []
			while index < len(lines):
				match = (_NUMBERED_LIST_ITEM if ordered else _LIST_ITEM).match(lines[index])
				if not match:
					break
				if not ordered and _NUMBERED_LIST_ITEM.match(lines[index]):
					break
				items.append(match.group(1))
				index += 1
			parts.append(f"<{tag}>")
			parts.extend(f"<li>{escape(item)}</li>" for item in items)
			parts.append(f"</{tag}>")
			continue

		plainLines.append(line)
		index += 1

	flushPlainLines()
	parts.append("</main></body></html>")
	return "".join(parts)
