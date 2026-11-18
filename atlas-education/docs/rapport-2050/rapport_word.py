"""Rendu Word éditable du contenu scientifique commun aux deux formats."""
from io import BytesIO
from xml.etree import ElementTree

from lxml import etree
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Mm, Pt, RGBColor
from PIL import Image
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas


GREEN = "14583F"
INK = "182D26"
GRAY = "44554D"


def rich(paragraph, markup, *, cell_color=None, size=None, bold=False):
    """Conserve les indices, exposants et liens externes du texte scientifique."""
    def append(text, tags, parent):
        if not text:
            return
        run = paragraph.add_run(text)
        if bold or "b" in tags:
            run.bold = True
        if size is not None:
            run.font.size = Pt(size)
        if cell_color:
            run.font.color.rgb = RGBColor.from_string(cell_color)
        if "sub" in tags:
            run.font.subscript = True
        if "super" in tags:
            run.font.superscript = True
        if "link" in tags:
            run.underline = True
            run.font.color.rgb = RGBColor.from_string(GREEN)
        if parent is not None:
            parent.append(run._r)

    def visit(node, tags=(), parent=None):
        if node.tag == "br":
            paragraph.add_run().add_break()
            return
        if node.tag == "link":
            parent = OxmlElement("w:hyperlink")
            rid = paragraph.part.relate_to(node.attrib["href"], RT.HYPERLINK, is_external=True)
            parent.set(qn("r:id"), rid)
            paragraph._p.append(parent)
        tags = (*tags, node.tag)
        append(node.text, tags, parent)
        for child in node:
            visit(child, tags, parent)
            append(child.tail, tags, parent)
    visit(ElementTree.fromstring("<texte>" + str(markup) + "</texte>"))


def field(paragraph, instruction):
    field_xml = OxmlElement("w:fldSimple")
    field_xml.set(qn("w:instr"), instruction)
    paragraph._p.append(field_xml)


class WordReport:
    def __init__(self, path, figure_path, draw_trend, trend_caption):
        self.path, self.figure_path = path, figure_path
        self.draw_trend, self.trend_caption = draw_trend, trend_caption
        self.document = Document()
        self.part = None
        self.pages = 0
        doc = self.document
        doc.core_properties.title = "Salles de classe et enseignants du primaire public en 2050"
        doc.core_properties.subject = "Défi 3 du Data Challenge Burkina Faso"
        doc.core_properties.author = "Atlas Éducation"
        section = doc.sections[0]
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.left_margin = section.right_margin = Mm(18)
        section.top_margin, section.bottom_margin = Mm(19), Mm(17)
        section.header_distance = section.footer_distance = Mm(8)
        self.width = (section.page_width-section.left_margin-section.right_margin)/12700
        normal = doc.styles["Normal"]
        normal.font.name = "Arial"
        normal.font.size = Pt(11)
        normal.font.color.rgb = RGBColor.from_string(INK)
        normal.paragraph_format.space_after = Pt(8)
        normal.paragraph_format.line_spacing = Pt(15)
        for name, face, size, leading, after, color, bold in [
            ("Title","Georgia",25,30,7,"111111",False),
            ("Heading 1","Arial",9,12,8,GREEN,True),
            ("Heading 2","Georgia",23,27.5,7,INK,False),
            ("Heading 3","Arial",12,15,4,GREEN,True),
            ("Partie suite","Arial",9,12,8,GREEN,True),
            ("Chapeau","Arial",11.5,15.5,10,GRAY,False),
            ("Légende Atlas","Arial",9,11.9,7,GRAY,False),
            ("Formule Atlas","Georgia",13,17.5,7,GREEN,False),
            ("Commande Atlas","Courier New",8.8,13,8,INK,False),
            ("Mention Atlas","Arial",8,10,0,GRAY,False),
        ]:
            style = doc.styles[name] if name in doc.styles else doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            style.base_style = normal
            style.font.name, style.font.size, style.font.bold = face, Pt(size), bold
            style.font.color.rgb = RGBColor.from_string(color)
            fmt=style.paragraph_format
            fmt.space_before,fmt.space_after,fmt.line_spacing = Pt(0),Pt(after),Pt(leading)
            fmt.keep_with_next = name in ("Heading 1","Heading 2","Heading 3","Title","Partie suite")
            rpr=style.element.get_or_add_rPr()
            font=rpr.find(qn("w:rFonts"))
            for attr in ("asciiTheme","hAnsiTheme","cstheme"):
                if font is not None:
                    font.attrib.pop(qn("w:"+attr),None)
            ppr=style.element.get_or_add_pPr()
            border=ppr.find(qn("w:pBdr"))
            if border is not None:
                ppr.remove(border)
        language = normal.element.get_or_add_rPr().find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            normal.element.get_or_add_rPr().append(language)
        language.set(qn("w:val"),"fr-FR")
        h = section.header.paragraphs[0]
        h.style = "Mention Atlas"
        h.paragraph_format.tab_stops.add_tab_stop(Pt(self.width),WD_TAB_ALIGNMENT.RIGHT)
        h.add_run("ATLAS ÉDUCATION").bold = True
        h.add_run("\tBURKINA FASO   /   PLANIFICATION SCOLAIRE")
        f = section.footer.paragraphs[0]
        f.style = "Mention Atlas"
        f.paragraph_format.tab_stops.add_tab_stop(Pt(self.width),WD_TAB_ALIGNMENT.RIGHT)
        f.add_run("Primaire public   ·   Annuaire 2024–2025   ·   18 novembre 2026\t")
        field(f,"PAGE"); f.add_run(" / "); field(f,"NUMPAGES")

    def page(self, part, section, title, subtitle):
        first = self.part is None
        self.pages += 1
        p = self.document.add_paragraph(style="Heading 1" if self.part != part else "Partie suite")
        p.paragraph_format.page_break_before = not first
        p.add_run(part + "   /   " + section.upper())
        self.part = part
        rich(self.document.add_paragraph(style="Title" if first else "Heading 2"),title)
        rich(self.document.add_paragraph(style="Chapeau"),subtitle)

    def p(self, content):
        rich(self.document.add_paragraph(),content)

    def h(self, content):
        rich(self.document.add_paragraph(style="Heading 3"),content)

    def note(self, content):
        rich(self.document.add_paragraph(style="Légende Atlas"),content)

    def formula(self, content):
        rich(self.document.add_paragraph(style="Formule Atlas"),content)

    def code(self, lines):
        p = self.document.add_paragraph(style="Commande Atlas")
        p.add_run("\n".join(lines))

    def table(self, headers, rows, widths, align_right=(), size=9):
        t = self.document.add_table(rows=0, cols=len(headers))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for col,width in zip(t.columns,widths):
            col.width = Pt(self.width*width)
        margins = OxmlElement("w:tblCellMar")
        for edge,value in (("top",65),("bottom",65),("start",95),("end",95)):
            m=OxmlElement("w:"+edge)
            m.set(qn("w:w"),str(value));m.set(qn("w:type"),"dxa")
            margins.append(m)
        t._tbl.tblPr.append(margins)
        for i, values in enumerate([headers,*rows]):
            row = t.add_row()
            trpr=row._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if i == 0:
                trpr.append(OxmlElement("w:tblHeader"))
            for j,(cell,value) in enumerate(zip(row.cells,values)):
                cell.width = Pt(self.width*widths[j])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                if i == 0 or i % 2 == 0:
                    shade=OxmlElement("w:shd");shade.set(qn("w:fill"),GREEN if i==0 else "EDF4EF")
                    cell._tc.get_or_add_tcPr().append(shade)
                p=cell.paragraphs[0]
                p.paragraph_format.space_after=Pt(0)
                p.paragraph_format.line_spacing=Pt(size+2.2)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if j in align_right else WD_ALIGN_PARAGRAPH.LEFT
                rich(p,value,cell_color="FFFFFF" if i==0 else INK,size=size,bold=i==0)
        pad=self.document.add_paragraph()
        pad.paragraph_format.space_after=Pt(0)
        pad.paragraph_format.line_spacing=Pt(5)

    def picture(self, stream, width, alt):
        p=self.document.add_paragraph()
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing=1
        p.paragraph_format.space_after=Pt(3)
        p.paragraph_format.keep_with_next=True
        picture=p.add_run().add_picture(stream,width=Pt(width))
        picture._inline.docPr.set("descr",alt)

    def image(self,name,caption,height):
        src=self.figure_path(name)
        with Image.open(src) as img:
            width=min(self.width,height*img.width/img.height)
        self.picture(str(src),width,caption)
        self.note(caption)

    def trend(self,historical,trajectories):
        vector=BytesIO()
        height=158
        c=canvas.Canvas(vector,pagesize=(self.width,height))
        self.draw_trend(c,0,height,self.width,historical,trajectories)
        c.save()
        bitmap=BytesIO()
        with pdfium.PdfDocument(vector.getvalue()) as pdf:
            page=pdf[0]
            raster=page.render(scale=3)
            raster.to_pil().save(bitmap,"PNG")
            raster.close(); page.close()
        bitmap.seek(0)
        self.picture(bitmap,self.width,self.trend_caption)
        self.note(self.trend_caption)

    def save(self):
        # L’aperçu de fichiers lit ces propriétés avant le premier recalcul des champs dans Word.
        part = self.document.part.package.part_related_by(RT.EXTENDED_PROPERTIES)
        props = etree.fromstring(part.blob)
        props.find("{*}Pages").text = str(self.pages)
        text = self.document.element.body.xpath(".//w:t/text()")
        props.find("{*}Words").text = str(len(" ".join(text).split()))
        part._blob = etree.tostring(props, encoding="UTF-8", xml_declaration=True, standalone=True)
        self.document.save(self.path)
