"""
WordprocessingML writer targeting the ITIJ journal template.

Rather than authoring OOXML from a blank document, this module keeps every part
of the supplied template (styles.xml, numbering.xml, headers, footers, embedded
fonts, theme) and replaces only the document body. That guarantees the output
inherits the journal's page geometry, margins, header/footer furniture and
heading definitions exactly.

Element ordering inside <w:pPr> and <w:rPr> is schema-significant in WordprocessingML,
so the builders below emit children in the order the ECMA-376 sequence requires.
"""
from __future__ import annotations

import copy
import os
import re
import shutil
import zipfile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

FONT = "Times New Roman"
CONTENT_WIDTH_TWIPS = 8788  # A4 (11907) minus template left (1701) + right (1418)


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------
# run properties
# --------------------------------------------------------------------------
def rpr(*, b: bool = False, i: bool = False, sz: int | None = None,
        font: str | None = FONT, color: str | None = None,
        sup: bool = False, sub: bool = False, smallcaps: bool = False,
        u: bool = False, spacing: int | None = None) -> str:
    """Build a <w:rPr>. sz is expressed in points (converted to half-points)."""
    parts = []
    if font:
        parts.append(f'<w:rFonts w:ascii="{font}" w:eastAsia="{font}" '
                     f'w:hAnsi="{font}" w:cs="{font}"/>')
    if b:
        parts.append("<w:b/>")
    if i:
        parts.append("<w:i/>")
    if smallcaps:
        parts.append("<w:smallCaps/>")
    if color:
        parts.append(f'<w:color w:val="{color}"/>')
    if spacing is not None:
        parts.append(f'<w:spacing w:val="{spacing}"/>')
    if sz is not None:
        half = int(round(sz * 2))
        parts.append(f'<w:sz w:val="{half}"/><w:szCs w:val="{half}"/>')
    if u:
        parts.append('<w:u w:val="single"/>')
    if sup:
        parts.append('<w:vertAlign w:val="superscript"/>')
    if sub:
        parts.append('<w:vertAlign w:val="subscript"/>')
    return "<w:rPr>" + "".join(parts) + "</w:rPr>" if parts else ""


def run(text: str, **kw) -> str:
    """A single <w:r>. Newlines become <w:br/>, tabs become <w:tab/>."""
    props = rpr(**kw)
    out = []
    for chunk in re.split(r"(\n|\t)", text):
        if chunk == "\n":
            out.append(f"<w:r>{props}<w:br/></w:r>")
        elif chunk == "\t":
            out.append(f"<w:r>{props}<w:tab/></w:r>")
        elif chunk:
            out.append(f'<w:r>{props}<w:t xml:space="preserve">{esc(chunk)}</w:t></w:r>')
    return "".join(out)


def rich(parts, **base) -> str:
    """Build runs from [(text, {overrides}), ...]."""
    out = []
    for item in parts:
        if isinstance(item, str):
            out.append(run(item, **base))
        else:
            text, over = item
            kw = dict(base)
            kw.update(over)
            out.append(run(text, **kw))
    return "".join(out)


# --------------------------------------------------------------------------
# paragraph properties
# --------------------------------------------------------------------------
def ppr(*, style: str | None = None, keep_next: bool = False,
        page_break_before: bool = False, no_numbering: bool = False,
        before: int | None = None, after: int | None = 120,
        line: int = 228, align: str | None = "both",
        left: int = 0, hanging: int = 2, right: int = 0,
        keep_lines: bool = False, shading: str | None = None) -> str:
    parts = []
    if style:
        parts.append(f'<w:pStyle w:val="{style}"/>')
    if keep_next:
        parts.append("<w:keepNext/>")
    if keep_lines:
        parts.append("<w:keepLines/>")
    if page_break_before:
        parts.append("<w:pageBreakBefore/>")
    if no_numbering:
        # numId 0 detaches the paragraph from the numbering attached to its
        # style; section numbers are supplied as literal text instead.
        parts.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>')
    if shading:
        parts.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shading}"/>')
    spacing = []
    if before is not None:
        spacing.append(f'w:before="{before}"')
    if after is not None:
        spacing.append(f'w:after="{after}"')
    spacing.append(f'w:line="{line}" w:lineRule="auto"')
    parts.append("<w:spacing " + " ".join(spacing) + "/>")
    ind = [f'w:left="{left}"']
    if hanging:
        ind.append(f'w:hanging="{hanging}"')
    if right:
        ind.append(f'w:right="{right}"')
    parts.append("<w:ind " + " ".join(ind) + "/>")
    if align:
        parts.append(f'<w:jc w:val="{align}"/>')
    return "<w:pPr>" + "".join(parts) + "</w:pPr>"


def para(content: str = "", **kw) -> str:
    return f"<w:p>{ppr(**kw)}{content}</w:p>"


def text_para(text: str, *, run_kw: dict | None = None, **kw) -> str:
    return para(run(text, **(run_kw or {})), **kw)


# --------------------------------------------------------------------------
# structural helpers
# --------------------------------------------------------------------------
def heading(text: str, level: int = 1, *, before: int | None = None) -> str:
    style = "Heading1" if level == 1 else "Heading2"
    return para(run(text), style=style, no_numbering=True,
                before=before if before is not None else (360 if level == 1 else 240),
                after=120 if level == 1 else 80, align=None, keep_next=True)


def page_break() -> str:
    return ('<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
            '</w:pPr><w:r><w:br w:type="page"/></w:r></w:p>')


def caption(kind: str, text: str, *, above: bool = False) -> str:
    """Figure/Table caption, matching the template's small-bold-left style."""
    label = f"{kind} {text}"
    return para(run(label, b=True, sz=8), align="left",
                before=120 if above else 60, after=120 if not above else 60,
                keep_next=above)


def _borders(sz: int = 4) -> str:
    return ("<w:tblBorders>"
            f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="000000"/>'
            '<w:left w:val="nil"/>'
            f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="000000"/>'
            '<w:right w:val="nil"/>'
            f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="000000"/>'
            '<w:insideV w:val="nil"/>'
            "</w:tblBorders>")


def table(rows: list[list[str]], widths: list[int], *, align: str | None = None,
          header: bool = True, font_sz: float = 8.0, header_sz: float | None = None,
          row_shading: bool = True) -> str:
    """
    Three-line academic table (top rule, header rule, bottom rule; no vertical
    rules), matching the template's own table formatting.
    """
    total = sum(widths)
    if total != CONTENT_WIDTH_TWIPS:
        scale = CONTENT_WIDTH_TWIPS / total
        widths = [int(round(w * scale)) for w in widths]
    hdr_sz = header_sz if header_sz is not None else font_sz

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    xml = ["<w:tbl><w:tblPr>"]
    xml.append(f'<w:tblW w:w="{sum(widths)}" w:type="dxa"/>')
    if align:
        xml.append(f'<w:jc w:val="{align}"/>')
    xml.append(_borders())
    xml.append('<w:tblLayout w:type="fixed"/>')
    xml.append('<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" '
               'w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0"/>')
    xml.append("</w:tblPr>")
    xml.append(f"<w:tblGrid>{grid}</w:tblGrid>")

    for ri, row in enumerate(rows):
        is_head = header and ri == 0
        xml.append("<w:tr>")
        if is_head:
            xml.append("<w:trPr><w:tblHeader/></w:trPr>")
        for ci, cell in enumerate(row):
            w = widths[ci] if ci < len(widths) else widths[-1]
            shade = ""
            if is_head:
                shade = ""
            elif row_shading and ri % 2 == 0:
                shade = 'w:fill="F2F2F2"'
            xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>')
            if shade:
                xml.append(f'<w:shd w:val="clear" w:color="auto" {shade}/>')
            xml.append('<w:vAlign w:val="center"/></w:tcPr>')
            cell_align = "left" if ci == 0 else "center"
            for li, line in enumerate(str(cell).split("\n")):
                xml.append(para(
                    run(line, b=is_head, sz=hdr_sz if is_head else font_sz),
                    align=cell_align, before=30, after=30, line=240,
                    left=60, hanging=0))
            xml.append("</w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    # Word needs a paragraph after a table
    xml.append(text_para("", after=0, line=240, align=None))
    return "".join(xml)


class ImageRegistry:
    """Collects figures and allocates relationship ids."""

    def __init__(self, start: int = 100):
        self.next_id = start
        self.items: list[tuple[str, str, int, int]] = []  # (rid, path, cx, cy)

    def add_png(self, path: str, width_emu: int) -> str:
        with open(path, "rb") as fh:
            head = fh.read(32)
        w, h = struct_unpack_size(head)
        rid = f"rId{self.next_id}"
        self.next_id += 1
        self.items.append((rid, path, width_emu, int(width_emu * h / w)))
        return rid

    def drawing_xml(self, rid: str, cx: int, cy: int, name: str = "Figure") -> str:
        pid = abs(hash(rid)) % 100000 + 1
        return (
            "<w:r><w:drawing>"
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{pid}" name="{name}"/>'
            "<wp:cNvGraphicFramePr>"
            '<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            "</wp:cNvGraphicFramePr>"
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{pid}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/>'
            "<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            "</pic:pic></a:graphicData></a:graphic></wp:inline>"
            "</w:drawing></w:r>"
        )

    def figure_para(self, path: str, width_emu: int) -> str:
        rid = self.add_png(path, width_emu)
        _, _, cx, cy = self.items[-1]
        return para(self.drawing_xml(rid, cx, cy), align="center",
                    before=120, after=60, keep_next=True)


def struct_unpack_size(png_head: bytes) -> tuple[int, int]:
    import struct
    if png_head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    w, h = struct.unpack(">II", png_head[16:24])
    return w, h


# --------------------------------------------------------------------------
# document assembly
# --------------------------------------------------------------------------
def build(template_path: str, out_path: str, body_xml: str,
          images: ImageRegistry) -> None:
    """Write out_path: the template with its body replaced by body_xml."""
    with zipfile.ZipFile(template_path) as zin:
        parts = {n: zin.read(n) for n in zin.namelist()}
        infos = {i.filename: i for i in zin.infolist()}

    doc = parts["word/document.xml"].decode("utf-8")
    m = re.search(r"<w:body>(.*)</w:body>", doc, re.S)
    if not m:
        raise ValueError("template has no <w:body>")
    sect_pr = ""
    sm = re.search(r"<w:sectPr\b.*?</w:sectPr>", m.group(1), re.S)
    if sm:
        sect_pr = sm.group(0)

    parts["word/document.xml"] = (
        doc[:m.start(1)] + body_xml + sect_pr + "</w:body></w:document>"
    ).encode("utf-8")

    # register figures
    rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
    add_rels, add_media = [], {}
    for rid, path, _, _ in images.items:
        base = os.path.basename(path)
        # the relationship target is relative to word/, but the part itself must
        # live at word/media/<base> inside the package
        add_rels.append(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
            f'officeDocument/2006/relationships/image" Target="media/{base}"/>')
        add_media[f"word/media/{base}"] = open(path, "rb").read()
    if add_rels:
        rels = rels.replace("</Relationships>", "".join(add_rels) + "</Relationships>")
        parts["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    parts.update(add_media)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in parts.items():
            info = infos.get(name)
            zi = zipfile.ZipInfo(name, date_time=(info.date_time if info else (2026, 1, 1, 0, 0, 0)))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr if info else 0o600 << 16
            zout.writestr(zi, data)