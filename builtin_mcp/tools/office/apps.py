from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .errors import OfficeUnavailable


def _app_progids() -> dict[str, tuple[str, ...]]:
    return {
        "word": ("Word.Application",),
        "excel": ("Excel.Application",),
        "powerpoint": ("PowerPoint.Application",),
        "wps_word": tuple(item.strip() for item in os.getenv("COPY_MYSELF_WPS_WORD_PROGID", "KWps.Application,KWps.Application.12,et.Application").split(",") if item.strip()),
        "wps_excel": tuple(item.strip() for item in os.getenv("COPY_MYSELF_WPS_EXCEL_PROGID", "Ket.Application,KET.Application,et.Application").split(",") if item.strip()),
        "wps_powerpoint": tuple(item.strip() for item in os.getenv("COPY_MYSELF_WPS_POWERPOINT_PROGID", "KWPP.Application,KWPP.Application.12").split(",") if item.strip()),
    }


def _matrix(value: Any) -> list[list[Any]]:
    if value is None:
        return []
    if not isinstance(value, tuple):
        return [[value]]
    if not value:
        return []
    if isinstance(value[0], tuple):
        return [list(row) for row in value]
    return [list(value)]


class ComOfficeAdapter:
    def __init__(self) -> None:
        self._available = None

    @property
    def available(self) -> bool:
        if self._available is None:
            self._available = self._probe()
        return self._available

    def _probe(self) -> bool:
        if os.name != "nt":
            return False
        try:
            __import__("pythoncom")
            __import__("win32com.client")
        except Exception:
            return False
        return True

    @contextmanager
    def _application(self, app: str, visible: bool) -> Iterator[Any]:
        if not self.available:
            raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")
        pythoncom = __import__("pythoncom")
        client = __import__("win32com.client", fromlist=["DispatchEx"])
        office = None
        pythoncom.CoInitialize()
        try:
            for progid in _app_progids().get(app, ()):
                try:
                    office = client.DispatchEx(progid)
                    break
                except Exception:
                    continue
            if office is None:
                raise OfficeUnavailable(f"OfficeUnavailable: no enabled app for {app}")
            office.Visible = visible
            yield office
        finally:
            try:
                if office is not None:
                    office.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    @contextmanager
    def _session(self, progid: str) -> Iterator[tuple[Any, Any]]:
        if not self.available:
            raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")
        pythoncom = __import__("pythoncom")
        client = __import__("win32com.client", fromlist=["DispatchEx"])
        pythoncom.CoInitialize()
        try:
            app = client.DispatchEx(progid)
            yield pythoncom, app
        finally:
            try:
                app.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    def _dispatch(self, app: str) -> tuple[str, str]:
        for progid in APP_PROGIDS.get(app, ()):
            with self._session(progid) as (_, office):
                return progid, office.ProgId if hasattr(office, "ProgId") else progid
        raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")

    def list_apps(self) -> list[str]:
        if not self.available:
            raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")
        found: list[str] = []
        for app, progids in _app_progids().items():
            for progid in progids:
                try:
                    with self._session(progid):
                        found.append(app)
                        break
                except Exception:
                    continue
        return found

    def open(self, app: str, path: Path, visible: bool) -> dict[str, Any]:
        if not path.is_file():
            raise ValueError(f"InvalidArguments: not a file {path}")
        with self._application(app, visible):
            return {"action": "open", "app": app, "path": str(path), "visible": visible}

    def close(self, app: str, path: Path) -> dict[str, Any]:
        return {"action": "close", "app": app, "path": str(path)}

    def create_word(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        return self._create_document(app, destination, visible)

    def create_excel(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        return self._create_workbook(app, destination, visible)

    def create_powerpoint(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        return self._create_presentation(app, destination, visible)

    def save_as(self, app: str, path: Path, destination: Path, visible: bool) -> dict[str, Any]:
        if app in {"word", "wps_word"}:
            return self._save_word(app, path, destination, visible)
        if app in {"excel", "wps_excel"}:
            return self._save_excel(app, path, destination, visible)
        if app in {"powerpoint", "wps_powerpoint"}:
            return self._save_powerpoint(app, path, destination, visible)
        raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")

    def export_pdf(self, app: str, path: Path, destination: Path, visible: bool) -> dict[str, Any]:
        if app in {"word", "wps_word"}:
            with self._application(app, visible) as office:
                document = office.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
                try:
                    document.ExportAsFixedFormat(str(destination), 17)
                finally:
                    document.Close(SaveChanges=False)
        elif app in {"excel", "wps_excel"}:
            with self._application(app, visible) as office:
                workbook = office.Workbooks.Open(str(path), ReadOnly=True, AddToMru=False)
                try:
                    workbook.ExportAsFixedFormat(0, str(destination))
                finally:
                    workbook.Close(SaveChanges=False)
        elif app in {"powerpoint", "wps_powerpoint"}:
            with self._application(app, visible) as office:
                presentation = office.Presentations.Open(str(path), WithWindow=visible)
                try:
                    presentation.ExportAsFixedFormat(str(destination), 2)
                finally:
                    presentation.Close()
        else:
            raise OfficeUnavailable("OfficeUnavailable: install copy-myself[office] on Windows")
        return {"action": "export_pdf", "app": app, "path": str(path), "destination": str(destination), "visible": visible}

    def word_read_text(self, path: Path, visible: bool) -> dict[str, Any]:
        return self._word_read_text(path, visible)

    def word_replace_text(self, path: Path, text: str, replacement: str, visible: bool) -> dict[str, Any]:
        return self._word_replace_text(path, text, replacement, visible)

    def excel_list_sheets(self, path: Path, visible: bool) -> dict[str, Any]:
        return self._excel_list_sheets(path, visible)

    def excel_read_range(self, path: Path, sheet: str, range_name: str, visible: bool) -> dict[str, Any]:
        return self._excel_read_range(path, sheet, range_name, visible)

    def excel_write_range(self, path: Path, sheet: str, range_name: str, values: list[list[Any]], visible: bool) -> dict[str, Any]:
        return self._excel_write_range(path, sheet, range_name, values, visible)

    def powerpoint_list_slides(self, path: Path, visible: bool) -> dict[str, Any]:
        return self._powerpoint_list_slides(path, visible)

    def powerpoint_read_text(self, path: Path, visible: bool) -> dict[str, Any]:
        return self._powerpoint_read_text(path, visible)

    def _create_document(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            document = office.Documents.Add()
            try:
                if hasattr(document, "SaveAs2"):
                    document.SaveAs2(str(destination))
                else:
                    document.SaveAs(str(destination))
            finally:
                document.Close(SaveChanges=False)
        return {"action": "create_word", "app": app, "path": str(destination), "visible": visible}

    def _create_workbook(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            workbook = office.Workbooks.Add()
            workbook.SaveAs(str(destination))
            workbook.Close(SaveChanges=False)
        return {"action": "create_excel", "app": app, "path": str(destination), "visible": visible}

    def _create_presentation(self, app: str, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            presentation = office.Presentations.Add()
            presentation.SaveAs(str(destination))
            presentation.Close()
        return {"action": "create_powerpoint", "app": app, "path": str(destination), "visible": visible}

    def _save_word(self, app: str, path: Path, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            document = office.Documents.Open(str(path), ReadOnly=False, AddToRecentFiles=False)
            try:
                if hasattr(document, "SaveAs2"):
                    document.SaveAs2(str(destination))
                else:
                    document.SaveAs(str(destination))
            finally:
                document.Close(SaveChanges=False)
        return {"action": "save_as", "app": app, "path": str(path), "destination": str(destination), "visible": visible}

    def _save_excel(self, app: str, path: Path, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            workbook = office.Workbooks.Open(str(path), ReadOnly=False, AddToMru=False)
            workbook.SaveAs(str(destination))
            workbook.Close(SaveChanges=False)
        return {"action": "save_as", "app": app, "path": str(path), "destination": str(destination), "visible": visible}

    def _save_powerpoint(self, app: str, path: Path, destination: Path, visible: bool) -> dict[str, Any]:
        with self._application(app, visible) as office:
            presentation = office.Presentations.Open(str(path), WithWindow=visible)
            presentation.SaveAs(str(destination))
            presentation.Close()
        return {"action": "save_as", "app": app, "path": str(path), "destination": str(destination), "visible": visible}

    def _word_read_text(self, path: Path, visible: bool) -> dict[str, Any]:
        with self._application("word", visible) as office:
            document = office.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
            try:
                text = document.Content.Text
            finally:
                document.Close(SaveChanges=False)
        return {"action": "word_read_text", "path": str(path), "visible": visible, "text": text}

    def _word_replace_text(self, path: Path, text: str, replacement: str, visible: bool) -> dict[str, Any]:
        with self._application("word", visible) as office:
            document = office.Documents.Open(str(path), ReadOnly=False, AddToRecentFiles=False)
            try:
                original = document.Content.Text
                replacements = original.count(text)
                find = document.Content.Find
                find.ClearFormatting()
                find.Replacement.ClearFormatting()
                find.Execute(FindText=text, ReplaceWith=replacement, Replace=2)
                document.Save()
            finally:
                document.Close(SaveChanges=False)
        return {"action": "word_replace_text", "path": str(path), "visible": visible, "text": text, "replacement": replacement, "replacements": replacements}

    def _excel_list_sheets(self, path: Path, visible: bool) -> dict[str, Any]:
        with self._application("excel", visible) as office:
            workbook = office.Workbooks.Open(str(path), ReadOnly=True, AddToMru=False)
            try:
                sheets = [workbook.Worksheets(index).Name for index in range(1, workbook.Worksheets.Count + 1)]
            finally:
                workbook.Close(SaveChanges=False)
        return {"action": "excel_list_sheets", "path": str(path), "visible": visible, "sheets": sheets}

    def _excel_read_range(self, path: Path, sheet: str, range_name: str, visible: bool) -> dict[str, Any]:
        with self._application("excel", visible) as office:
            workbook = office.Workbooks.Open(str(path), ReadOnly=True, AddToMru=False)
            try:
                values = _matrix(workbook.Worksheets(sheet).Range(range_name).Value)
            finally:
                workbook.Close(SaveChanges=False)
        return {"action": "excel_read_range", "path": str(path), "visible": visible, "sheet": sheet, "range": range_name, "values": values}

    def _excel_write_range(self, path: Path, sheet: str, range_name: str, values: list[list[Any]], visible: bool) -> dict[str, Any]:
        with self._application("excel", visible) as office:
            workbook = office.Workbooks.Open(str(path), ReadOnly=False, AddToMru=False)
            try:
                workbook.Worksheets(sheet).Range(range_name).Value = tuple(tuple(row) for row in values)
                workbook.Save()
            finally:
                workbook.Close(SaveChanges=False)
        return {"action": "excel_write_range", "path": str(path), "visible": visible, "sheet": sheet, "range": range_name, "values": values}

    def _powerpoint_list_slides(self, path: Path, visible: bool) -> dict[str, Any]:
        with self._application("powerpoint", visible) as office:
            presentation = office.Presentations.Open(str(path), WithWindow=visible)
            try:
                slides = [{"index": index} for index in range(1, presentation.Slides.Count + 1)]
            finally:
                presentation.Close()
        return {"action": "powerpoint_list_slides", "path": str(path), "visible": visible, "slides": slides}

    def _powerpoint_read_text(self, path: Path, visible: bool) -> dict[str, Any]:
        with self._application("powerpoint", visible) as office:
            presentation = office.Presentations.Open(str(path), WithWindow=visible)
            try:
                slides: list[dict[str, Any]] = []
                for index in range(1, presentation.Slides.Count + 1):
                    slide = presentation.Slides(index)
                    texts: list[str] = []
                    for shape_index in range(1, slide.Shapes.Count + 1):
                        shape = slide.Shapes(shape_index)
                        if getattr(shape, "HasTextFrame", False):
                            texts.append(str(shape.TextFrame.TextRange.Text))
                    slides.append({"index": index, "text": texts})
            finally:
                presentation.Close()
        return {"action": "powerpoint_read_text", "path": str(path), "visible": visible, "text": slides}
