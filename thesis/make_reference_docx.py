#!/usr/bin/env python3
"""Generate build/hec_reference.docx for the HEC report format.

Takes pandoc's own default reference.docx (so every named style pandoc emits is
present) and restyles it: 1.15 line spacing, plus numbered pages and a running
header with the author name. The default font is left in place (i.e. reverted
off the earlier Times New Roman override) — set a font explicitly in the build if
a specific one is wanted. Standard library only — no python-docx.

Run from the thesis/ directory:  python make_reference_docx.py
"""
from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

AUTHOR = "Cedric Emmanuel KIRE"
INDICATION = "Data Science for Business – Research Paper – June 2026"
HEADER_TEXT = f"HEC PARIS — {INDICATION}"  # top of page: institution + indication + date
FOOTER_NAME = AUTHOR                        # bottom of page: student name (+ page number)
LINE_SPACING = "264"  # twentieths of a line: 264 / 240 = 1.1

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
BUILD.mkdir(exist_ok=True)
DEFAULT_REF = BUILD / "_ref_default.docx"
OUT = BUILD / "hec_reference.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

HEADER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<w:hdr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
    '<w:p><w:pPr><w:jc w:val="right"/></w:pPr>'
    f'<w:r><w:t xml:space="preserve">{HEADER_TEXT}</w:t></w:r>'
    '</w:p></w:hdr>'
)

FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    f'<w:r><w:t xml:space="preserve">{FOOTER_NAME}      </w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> PAGE \\* MERGEFORMAT </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    '<w:r><w:t>1</w:t></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    '</w:p></w:ftr>'
)

HDR_RID = "rId900"
FTR_RID = "rId901"


def get_default_reference() -> bytes:
    """pandoc's bundled default reference.docx (binary on stdout)."""
    out = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"],
        check=True,
        capture_output=True,
    )
    DEFAULT_REF.write_bytes(out.stdout)
    return out.stdout


def set_line_spacing(xml: str) -> str:
    """Set the document-default line spacing; leave the default font untouched."""
    return xml.replace(
        '<w:spacing w:after="200" />',
        f'<w:spacing w:after="200" w:line="{LINE_SPACING}" w:lineRule="auto" />',
    )


def wire_header_footer(doc: str, rels: str, ctypes: str) -> tuple[str, str, str]:
    """Reference the header/footer parts from the section + register them."""
    doc = doc.replace(
        "<w:sectPr>",
        f'<w:sectPr><w:pgSz w:w="11906" w:h="16838" />'  # A4 (twentieths of a point)
        f'<w:headerReference w:type="default" r:id="{HDR_RID}" />'
        f'<w:footerReference w:type="default" r:id="{FTR_RID}" />',
        1,
    )
    rel_hdr = f'<Relationship Type="{R_NS}/header" Id="{HDR_RID}" Target="header2.xml" />'
    rel_ftr = f'<Relationship Type="{R_NS}/footer" Id="{FTR_RID}" Target="footer2.xml" />'
    rels = rels.replace("</Relationships>", rel_hdr + rel_ftr + "</Relationships>")
    ov = (
        '<Override PartName="/word/header2.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.wordprocessingml.header+xml" />'
        '<Override PartName="/word/footer2.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.wordprocessingml.footer+xml" />'
    )
    ctypes = ctypes.replace("</Types>", ov + "</Types>")
    return doc, rels, ctypes


def main() -> int:
    get_default_reference()
    with zipfile.ZipFile(DEFAULT_REF, "r") as zin:
        items = {name: zin.read(name) for name in zin.namelist()}

    items["word/styles.xml"] = set_line_spacing(
        items["word/styles.xml"].decode("utf-8")
    ).encode("utf-8")

    doc, rels, ctypes = wire_header_footer(
        items["word/document.xml"].decode("utf-8"),
        items["word/_rels/document.xml.rels"].decode("utf-8"),
        items["[Content_Types].xml"].decode("utf-8"),
    )
    items["word/document.xml"] = doc.encode("utf-8")
    items["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    items["[Content_Types].xml"] = ctypes.encode("utf-8")
    items["word/header2.xml"] = HEADER_XML.encode("utf-8")
    items["word/footer2.xml"] = FOOTER_XML.encode("utf-8")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)

    print(f"Wrote: {OUT} ({OUT.stat().st_size} bytes) — default font / 12pt / 1.15 / page numbers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
