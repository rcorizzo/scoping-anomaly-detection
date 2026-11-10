"""Offline regression checks for archive curation; no toolkit execution."""

import io
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from import_archives import clean_workbook, safe_name, NS


class ArchiveToolsTests(unittest.TestCase):
    def test_safe_paths(self):
        for name in ["../escape", "/absolute", "folder/../../escape", "folder\\escape"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)
        self.assertEqual(str(safe_name("core/search.py")), "core/search.py")

    def workbook(self, sheet, strings=None):
        data = io.BytesIO()
        with ZipFile(data, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", sheet)
            if strings:
                z.writestr("xl/sharedStrings.xml", strings)
        return data.getvalue()

    def test_no_transformation_preserves_original_bytes(self):
        data = self.workbook('<worksheet xmlns="' + NS["s"] + '"><sheetData/></worksheet>')
        public, cleared, replacements = clean_workbook(data)
        self.assertEqual(data, public)
        self.assertEqual((cleared, replacements), (0, 0))

    def test_inline_contact_column_cleared_and_other_email_redacted(self):
        data = self.workbook('''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
        <row r="1"><c r="A1" t="inlineStr"><is><t>emails</t></is></c><c r="B1" t="inlineStr"><is><t>title</t></is></c></row>
        <row r="2"><c r="A2" t="inlineStr"><is><t>nonstandard contact text</t></is></c><c r="B2" t="inlineStr"><is><t>Research contact: example@example.org</t></is></c><c r="C2"><v>11079</v></c></row>
        </sheetData></worksheet>''')
        public, cleared, replacements = clean_workbook(data)
        self.assertEqual((cleared, replacements), (1, 1))
        with ZipFile(io.BytesIO(public)) as z:
            root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            cells = {c.get("r"): c for c in root.findall(".//s:c", NS)}
            self.assertEqual(len(cells["A2"]), 0)
            self.assertEqual("".join(cells["B2"].itertext()), "Research contact: [email redacted]")
            self.assertEqual(cells["C2"].find("s:v", NS).text, "11079")

    def test_shared_string_contact_header_and_formula_removed(self):
        data = self.workbook('''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
        <row r="1"><c r="A1" t="s"><v>0</v></c></row>
        <row r="2"><c r="A2"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>''',
        '<sst xmlns="' + NS["s"] + '"><si><t>emails</t></si></sst>')
        public, cleared, replacements = clean_workbook(data)
        self.assertEqual((cleared, replacements), (1, 0))
        with ZipFile(io.BytesIO(public)) as z:
            self.assertNotIn(b"<ns0:f>", z.read("xl/worksheets/sheet1.xml"))


if __name__ == "__main__":
    unittest.main()
