"""Compose le rapport scientifique PDF ou Word à partir d’une même édition du calcul Atlas."""
import argparse
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

HERE = Path(__file__).resolve().parent
GREEN = "#14583F"
INK = "#182D26"
GRAY = "#44554D"
LINE = "#CEDBD3"
LIGHT = "#EDF4EF"
RED = "#9B432F"
W,H=A4
M=47
INNER=W-2*M
NAMES={"bas":"Basse","central":"Centrale","haut":"Haute"}
PAGES = 15
EDITION = "https://github.com/szidama/datachallenge2026/tree/188dd58ba1e444603d3aeace54ef217503719ff6"
TREND_CAPTION = ("Figure 4. Inscriptions du primaire public. La ligne sombre représente les observations PRI02. "
                 "À partir de 2025, les traits bleu court, vert continu et rouge long indiquent respectivement "
                 "les demandes basse, centrale et haute. L’axe horizontal indique l’année de fin de l’année scolaire.")


def figure_path(name):
    path = Path(name)
    return HERE / "figures" / (path if path.suffix else path.with_suffix(".png"))


def register():
    mac=Path("/System/Library/Fonts/Supplemental")
    linux=Path("/usr/share/fonts/truetype/dejavu")
    windows=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
    for name,mac_name,linux_name,windows_name in [
        ("Texte","Arial.ttf","DejaVuSans.ttf","arial.ttf"),("Gras","Arial Bold.ttf","DejaVuSans-Bold.ttf","arialbd.ttf"),
        ("Titre","Georgia.ttf","DejaVuSerif.ttf","georgia.ttf"),("Italique","Georgia Italic.ttf","DejaVuSerif-Italic.ttf","georgiai.ttf"),
        ("Code","Courier New.ttf","DejaVuSansMono.ttf","cour.ttf")]:
        path=next((p for p in (mac/mac_name,windows/windows_name) if p.is_file()),linux/linux_name)
        pdfmetrics.registerFont(TTFont(name,str(path)))
    pdfmetrics.registerFontFamily("Texte", normal="Texte", bold="Gras", italic="Italique", boldItalic="Gras")


def num(value,decimals=0):
    return f"{value:,.{decimals}f}".replace(","," ").replace(".",",")


def link(url,label):
    return '<link href="'+escape(url, {'"': '&quot;'})+'" color="'+GREEN+'"><u>'+escape(label)+'</u></link>'


class Report:
    def __init__(self,path):
        self.c=canvas.Canvas(str(path),pagesize=A4,pageCompression=1)
        self.c.setTitle("Burkina Faso · Planifier les salles et les enseignants jusqu’en 2050")
        self.c.setAuthor("Atlas Éducation · Data Challenge Burkina")
        self.no=0
        self.y=0
        self.part=None

    def page(self,part,section,title,subtitle):
        if self.no:self.c.showPage()
        self.no+=1; c=self.c
        if self.part != part:
            key="section-"+part
            c.bookmarkPage(key)
            c.addOutlineEntry(section,key,level=0,closed=False)
            self.part=part
        c.setFillColor(GREEN);c.setFont("Gras",9);c.drawString(M,H-36,"ATLAS ÉDUCATION")
        c.setFont("Texte",8.5);c.drawRightString(W-M,H-36,"BURKINA FASO    /    PLANIFICATION SCOLAIRE")
        c.setStrokeColor(LINE);c.line(M,H-45,W-M,H-45)
        c.setFillColor(GRAY);c.setFont("Gras",9);c.drawString(M,H-74,f"{part}   /   {section.upper()}")
        self.y=H-86
        self.p(title,"Titre",29,34,INK,8)
        self.p(subtitle,"Texte",12,16.5,GRAY,14)
        c.setStrokeColor(LINE);c.line(M,36,W-M,36)
        c.setFillColor(GRAY);c.setFont("Texte",8);c.drawString(M,23,"Étude du primaire public    ·    Millésime de base 2024–2025    ·    Édition du 18 novembre 2026")
        c.setFont("Gras",8);c.drawRightString(W-M,23,f"{self.no}  /  {PAGES}")

    def p(self,content,font="Texte",size=10.7,leading=15.3,color=INK,after=9):
        sty=ParagraphStyle("p",fontName=font,fontSize=size,leading=leading,textColor=colors.HexColor(color),splitLongWords=False)
        para=Paragraph(content.replace(" ","&nbsp;"),sty); _,h=para.wrap(INNER,1000)
        self.y-=h;para.drawOn(self.c,M,self.y);self.y-=after;self.check()

    def check(self):
        if self.y<42:raise ValueError(f"Page {self.no} déborde de {42-self.y:.1f} points")

    def h(self,text):
        self.y-=2
        self.p(text,"Gras",12,15,GREEN,5)

    def note(self,text):
        self.p(text,"Texte",8.75,12.1,GRAY,9)

    def formula(self,text):
        self.p(text,"Titre",14,20,GREEN,8)

    def code(self,lines):
        for line in lines:
            self.p(escape(line),"Code",8.8,13,INK,0)
        self.y-=8

    def table(self,headers,rows,widths,align_right=(),size=9):
        assert abs(sum(widths)-1)<.001
        lines=[]
        for i,row in enumerate([headers,*rows]):
            cells=[]
            for k,item in enumerate(row):
                style=ParagraphStyle("cell",fontName=("Gras" if i==0 else "Texte"),fontSize=size if i else size-.2,
                    leading=size+2.4,textColor=colors.HexColor("#FFFFFF" if i==0 else INK),splitLongWords=False,
                    alignment=TA_RIGHT if k in align_right else 0)
                cells.append(Paragraph(str(item).replace(" ","&nbsp;"),style))
            lines.append(cells)
        t=Table(lines,colWidths=[INNER*x for x in widths],hAlign="LEFT")
        style=[("BACKGROUND",(0,0),(-1,0),colors.HexColor(GREEN)),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),4.5),("BOTTOMPADDING",(0,0),(-1,-1),4.5),
            ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
            ("LINEBELOW",(0,-1),(-1,-1),.5,colors.HexColor(LINE))]
        for i in range(2,len(lines),2):style.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor(LIGHT)))
        t.setStyle(TableStyle(style));_,ht=t.wrap(INNER,1000)
        self.y-=ht;t.drawOn(self.c,M,self.y);self.y-=11;self.check()

    def image(self,name,caption,height):
        img=ImageReader(str(figure_path(name)));wi,hi=img.getSize()
        scale=min(INNER/wi,height/hi)
        wi*=scale;hi*=scale;x=(W-wi)/2
        self.y-=hi;self.c.drawImage(img,x,self.y,wi,hi,mask="auto")
        self.c.setStrokeColor(LINE);self.c.setLineWidth(.5);self.c.rect(x,self.y,wi,hi,stroke=1,fill=0)
        self.y-=6;self.note(caption)

    def trend(self,historical,trajectories):
        self.draw_trend(self.c,M,self.y,INNER,historical,trajectories)
        self.y-=162
        self.note(TREND_CAPTION)

    @staticmethod
    def draw_trend(c,margin,top_edge,width,historical,trajectories):
        left,right=margin+43,margin+width-13; bottom,top=top_edge-141,top_edge-15
        xp=lambda y:left+(right-left)*(y-2016)/34
        yp=lambda n:bottom+(top-bottom)*n/4500000
        for n in [0,1000000,2000000,3000000,4000000]:
            c.setStrokeColor(LINE);c.setLineWidth(.45);c.line(left,yp(n),right,yp(n))
            c.setFont("Texte",8);c.setFillColor(GRAY);c.drawRightString(left-6,yp(n)-3,num(n/1000000,0))
        c.setFillColor(GRAY);c.setFont("Texte",8);c.drawString(margin,top_edge-9,"Millions d’élèves")
        c.setDash([2,3]);c.setStrokeColor("#839890");c.line(xp(2025),bottom,xp(2025),top)
        base=historical[-1];curves=[(INK,[(r["year"],r["value"]) for r in historical],None)]
        for scenario,color,dash in [("bas","#397588",[3,2]),("central",GREEN,None),("haut",RED,[7,2])]:
            curves.append((color,[(base["year"],base["value"])]+[(r["year"],r[scenario]) for r in trajectories],dash))
        for color,pts,dash in curves:
            c.setStrokeColor(color);c.setLineWidth(2);c.setDash(dash or []);path=c.beginPath()
            for i,(year,n) in enumerate(pts):(path.lineTo if i else path.moveTo)(xp(year),yp(n))
            c.drawPath(path)
        c.setDash([]);c.setFont("Texte",8);c.setFillColor(GRAY)
        for y in (2016,2020,2025,2030,2035,2040,2045,2050):c.drawCentredString(xp(y),bottom-12,str(y))

    def save(self):
        if self.no!=PAGES:raise ValueError(f"Le rapport doit contenir {PAGES} pages")
        self.c.save()


def write(data,path):
    register()
    if path.suffix.lower() == ".docx":
        from rapport_word import WordReport
        a = WordReport(path, figure_path, Report.draw_trend, TREND_CAPTION)
    elif path.suffix.lower() == ".pdf":
        a = Report(path)
    else:
        raise ValueError("Choisir une sortie .pdf ou .docx.")
    n=data["national"]; regions=data["regions"]; prov=data["provinces"]
    def national(year,sc,opt):return next(v for v in n if (v["year"],v["scenario"],v["option"])==(year,sc,opt))
    def area(year,sc,opt):return [v for v in regions if (v["year"],v["scenario"],v["option"])==(year,sc,opt)]
    def provinces(sc,year=2050):return [v for v in prov if v["scenario"]==sc and v["year"]==year]
    sources=data["sources"];dg=sources["annuaire"]["url"];insd=sources["demographie"]["url"];local=sources["localites"]["url"]
    post="https://www.cns.bf/publications/telecharger/183/"
    central=national(2050,"central","combine"); ref=national(2050,"central","reference")
    a.page("01","Le défi","Salles de classe et enseignants du primaire public en 2050",
           "Burkina Faso · Où investir et où affecter les enseignants dans les 13 régions et les 45 provinces historiques ?")
    a.p("Une salle supplémentaire crée des places si un enseignant peut y prendre une classe. Une affectation produit le même effet si une salle utilisable attend un groupe. Atlas confronte ces deux conditions à trois trajectoires d’inscriptions pour éclairer les choix de construction, de remise en service, de recrutement et de redéploiement.")
    a.h("Le résultat central")
    a.formula(f"{num(central['rooms_needed'])} salles et {num(central['teachers_needed'])} enseignants manquants en 2050")
    a.p(f"Le programme combiné simule {num(central['served'])} places servies pour {num(central['demand'])} inscriptions projetées. Il couvre {num(100*central['coverage'],1)} % de la demande et sert {num(ref['unserved']-central['unserved'])} élèves de plus que la référence. Ces estimations sont conditionnelles aux hypothèses de disponibilité, de départs et aux plafonds annuels du programme.")
    a.table(["Échelle de décision","Question opérationnelle","Résultat disponible"],[
      ["Province","Où la pression actuelle et future justifie-t-elle une vérification de terrain ?","Diagnostic à stocks de 2025 constants, offre d’eau et de latrines."],
      ["Région","Comment articuler salles et personnel quand les stocks évoluent ?","Référence et interventions avec flux annuels et déficits séparés."],
      ["Établissement ou localité","Quel site peut recevoir une classe ?","Page du répertoire des localités et observations à confirmer sur place."]],[.23,.38,.39])
    a.h("Calendrier de lecture")
    a.p("2025 fixe la base scolaire. 2030 sert de premier jalon de programmation. 2035 marque la fin des projections démographiques mobilisées. Les jalons 2040, 2045 et 2050 prolongent les trois trajectoires scolaires.")
    a.note("Clé de lecture. L’année 2050 désigne l’année scolaire 2049/2050. Les scénarios bas, central et haut portent sur la demande. Pour chacun, la référence et l’intervention combinée décrivent deux politiques de ressources.")
    a.note("Plan. Le défi p. 1 · Les données p. 2–3 · La préparation p. 4–6 · La méthode p. 7–9 · Les résultats p. 10–12 · La réponse au défi p. 13–14 · Reproduction p. 15.")

    a.page("02","Les données","Le point de départ scolaire","Les inscriptions nationales et les ressources provinciales proviennent de deux collections rapprochées sur le même millésime.")
    a.h("Le classeur du Data Challenge")
    a.p("Les 14 feuilles contiennent 21 tableaux structurés, dont huit au préscolaire et treize au primaire. L’import restitue 6 636 observations avec leurs dimensions. Pour la demande, la série PRI02 contient dix valeurs nationales d’effectifs du primaire public, de 2015/2016 à 2024/2025. PRI01 documente les régions tous statuts.")
    a.h("L’inventaire DGESS 2024–2025")
    a.table(["Primaire public","Total national","Interprétation"],[
      ["Écoles", "9 526","Établissements du statut public."],["Salles de classe","45 921","Salles recensées dans l’inventaire."],
      ["Groupes pédagogiques","45 543","Groupes dénombrés par l’annuaire."],["Maîtres chargés de cours","44 623","Personnel qui assure les cours dans le tableau I.1."],
      ["Élèves inscrits","2 391 345","La somme des 45 provinces retrouve PRI02."],
      ["Écoles avec eau potable","7 343","2 183 écoles sans eau potable recensée."],["Écoles avec latrines fonctionnelles","8 001","1 525 écoles sans latrines fonctionnelles."]],[.38,.19,.43],(1,))
    a.p("Les deux manques d’équipement portent sur des écoles. Les mêmes établissements peuvent cumuler les deux situations. L’inventaire des salles et l’effectif de maîtres servent à construire un stock disponible sous hypothèses.")
    a.note("Source. Ministère chargé de l’éducation, DGESS, Annuaire statistique de l’enseignement primaire 2024–2025, tableaux "+link(dg+"#page=12","I.1, pages PDF 12–16")+" et "+link(dg+"#page=279","V.4.1, pages PDF 279–281")+".")
    a.h("Éditions antérieures d’Atlas")
    a.p("Les premières éditions de démonstration simulaient les enseignants, les salles du primaire et la répartition régionale des effectifs publics. Ici, le tableau I.1 fournit ces trois grandeurs par province. Dans Atlas, ce choix correspond à « Annuaire du primaire 2024–2025 et démographie provinciale ».")

    a.page("02","Les données","La population et les localités","La démographie renseigne la géographie de la demande. Son horizon officiel balise la portée de l’analyse.")
    population=sum(p["population_base"] for p in provinces("central"))
    a.table(["Périmètre des 45 provinces","2025","2030","2035","2050"],[["Enfants de 6 à 11 ans",num(population),num(sum(p['population_target'] for p in provinces('central',2030))),num(sum(p['population_target'] for p in provinces('central',2035))),"Hors série"]],[.32,.175,.175,.175,.155],(1,2,3,4))
    a.p("Le RGPH 2019 fournit des projections provinciales annuelles de 2020 à 2035. Les valeurs 2025 du tableau sont déjà des projections démographiques. Le dénominateur inclut tous les enfants d’âge primaire. Le numérateur inclut les inscrits du public de tous âges. On compte ainsi "+num(2391345/population*100,1)+" inscrits pour 100 enfants de 6 à 11 ans en 2025. Calculer un taux net de scolarisation exigerait de connaître l’âge des élèves inscrits.")
    a.note("Source. INSD, cinquième RGPH, "+link(insd,"volume 4, Projections démographiques 2020–2035, édition 2")+". Somme des fiches provinciales après contrôle des colonnes par sexe.")
    a.h("Deux références complémentaires")
    a.p("Le fichier des localités du RGPH 2019 situe les communes, villages et secteurs sous leur province. L’interface renvoie à la page de chacune des 45 provinces. Ces entrées constituent un point de départ pour rapprocher écoles et localités. "+link(local,"Fichier des localités du Burkina Faso")+".")
    a.p("L’annuaire post-primaire et secondaire 2019–2020 documente un autre cycle et une autre année. Son tableau II.1 recense, pour le public des enseignements général, technique et professionnel réunis, 2 077 établissements, 13 800 salles et 769 753 élèves. Cette base contextualise la poursuite des études en aval du primaire. "+link(post+"#page=27","Annuaire 2019–2020, tableau II.1, page PDF 27")+".")
    a.h("Écoles géolocalisées, fermetures et déplacements")
    a.p("Les implantations OpenStreetMap, rapports d’éducation en situation d’urgence (ESU) et séries de personnes déplacées internes (PDI) restent des données d’appui à rapprocher. L’étude utilise une carte régionale historique et les localités de l’INSD. Aucun indicateur de distance ou de personne déplacée n’entre dans les calculs publiés ici.")

    a.page("03","La préparation","Passer des feuilles aux séries","Chaque valeur analysée conserve son cycle, son unité, sa période, son territoire, son statut et son origine.")
    a.h("De la cellule au registre")
    a.p("L’import identifie les tableaux par leur ancrage, vérifie les feuilles et conserve la cellule source. Les années scolaires prennent l’année de fin comme clé. Le statut public, le sexe total et le cycle primaire définissent la série PRI02. Les totaux régionaux, par sexe, par statut et par niveau sont contrôlés lorsque les marges permettent le rapprochement.")
    a.table(["Contrôle exécuté sur le classeur","Constat","Traitement scientifique"],[
      ["Valeurs disponibles","6 621 sur 6 636","Les 15 valeurs manquantes conservent leur état."],
      ["Formules avec résultat enregistré","420","Conserver formule et valeur source pour l’audit."],
      ["Contenus extérieurs aux tableaux","18 signalements","Isoler le texte et conserver son empreinte."],
      ["Indice de parité incohérent","1 signalement","Conserver l’indice publié avec son signalement."],
      ["Nouvel import des mêmes données","Identique","Associer la version à l’empreinte du fichier." ]],[.34,.23,.43])
    a.image("qualite-import","Figure 1. Écran « Données et qualité » après import du classeur. Le compteur d’écarts statistiques isole l’indice de parité à examiner. Les 18 textes hors tableaux sont répertoriés séparément dans le journal des contrôles.",66)
    a.h("Lire un ratio dans son périmètre")
    a.p("Le rapport élèves par salle divise les élèves du primaire public d’une province par ses salles publiques recensées dans la même année. Le rapport élèves par enseignant utilise les maîtres chargés de cours. Le calcul conserve l’absence d’un dénominateur utilisable. Pour une agrégation, on somme d’abord les numérateurs et les dénominateurs.")
    a.formula("En 2025, 2 391 345 ÷ 45 921 ≈ 52,1 élèves par salle.")
    a.p("Le même effectif rapporté aux 44 623 maîtres donne 53,6 élèves par enseignant. Ce diagnostic du stock recensé précède les hypothèses de simulation sur la disponibilité des moyens.")
    a.note("Sources. Classeur du Data Challenge, contrôles de l’import Atlas, et DGESS, "+link(dg+"#page=16","tableau I.1, total national")+". Le journal distingue les anomalies de structure et les données indisponibles.")

    a.page("03","La préparation","Vérifier le point de départ de la projection","La cellule L5 de la feuille Feuil2 permet de contrôler à la fois le public étudié, le millésime et l’unité de la série nationale.")
    a.h("Retrouver l’observation dans Atlas")
    a.p("Dans « Données et qualité », ouvrir « Consulter les observations ». Choisir l’origine « Observée », l’année de fin 2025 et le tableau PRI02. Appliquer, puis ouvrir Feuil2!L5. La ligne « National · Ensemble · Public » réunit les filles et les garçons inscrits dans le primaire public en 2024/2025.")
    a.image("trace-pri02","Figure 2. Détail de PRI02:L5 dans l’instance personnelle d’Atlas. L’écran associe les 2 391 345 élèves à leur cellule, au classeur et à l’empreinte de sa version. La valeur originale apparaît au bas de la fiche.",165)
    a.h("Trois contrôles sur le même millésime")
    a.table(["Rapprochement","Calcul ou source","Effectif obtenu"],[
        ["Sexe, secteur public","1 196 415 garçons + 1 194 930 filles","2 391 345"],
        ["Statut de l’école","2 391 345 élèves du public + 916 751 du privé","3 308 096"],
        ["Territoire, secteur public","Somme des effectifs publics des 45 provinces de l’annuaire",num(sum(p["enrolment"] for p in provinces("central")))]],[.26,.52,.22],(2,))
    a.p("Prendre le total tous statuts de Feuil2!L11 ajouterait 916 751 élèves du privé au point de départ. Pour projeter les besoins du public, Atlas ajuste le modèle sur la série PRI02 du seul secteur public et utilise les effectifs publics de l’annuaire pour la répartition territoriale.")
    a.note("Sources. Classeur du Data Challenge, Feuil2, cellules L3 à L11. DGESS, "+link(dg+"#page=16","annuaire du primaire 2024–2025, tableau I.1, total national")+".")

    a.page("03","La préparation","Raccorder les 45 provinces","La jointure territoriale est contrôlée ligne par ligne entre l’annuaire scolaire, les projections par âge et le répertoire des localités.")
    a.p("Chaque province reçoit la clé de sa région historique. Casse, accents, apostrophes et espaces sont normalisés. Les graphies divergentes ont une correspondance explicite, par exemple « LES BALE » avec Balés et « KOURITTENGA » avec Kouritenga. Les sous-totaux régionaux et la ligne nationale sont écartés du comptage des provinces.")
    a.h("Une anomalie démographique traçable")
    a.p("Dans la fiche de l’Oudalan, la ligne des 6–11 ans de 2031 porte 17 066 hommes, 16 511 femmes et un ensemble imprimé de 17 030. La préparation retient 33 577, somme des deux sexes. Elle conserve le total imprimé, les composantes, l’année et la page. La règle accepte un écart d’arrondi d’une personne. Ce cas est l’unique écart supérieur à un sur les 720 valeurs provinciales.")
    a.note("Source. INSD, "+link(insd+"#page=466","fiche Oudalan, page PDF 466")+". Cette correction de travail reste révisable si l’INSD publie un erratum.")
    a.image("inventaire-nord","Figure 3. Inventaire du Nord dans l’environnement de test d’Atlas. Au Loroum, on compte 112,3 élèves par salle en moyenne. « Eau » et « Latrines » dénombrent les écoles dépourvues de l’équipement. La mention « Hors horizon INSD » rappelle que la série des 6–11 ans s’arrête en 2035.",154)
    a.p("Le total des élèves par province se réconcilie avec les 2 391 345 du primaire public national. Les nombres de salles, d’enseignants et d’écoles équipées se réconcilient séparément aux lignes nationales imprimées. Une collecte régionale qui contredit la marge de l’annuaire bloque ce mode jusqu’à résolution du conflit.")
    a.note("Les nouveaux dossiers conservent les empreintes SHA-256 des trois PDF, les pages de l’inventaire et des équipements, la page des localités et la plage des pages de population.")

    a.page("04","La méthode","Apprendre trois trajectoires","Une régression quantile parcimonieuse est ajustée aux variations observées de la demande publique nationale.")
    a.p("Avec dix millésimes, une pente par scénario limite le nombre de paramètres. Chaque année d’origine t est appariée aux années disponibles à horizons h de un ou deux ans. Les 17 paires ainsi constituées proviennent de neuf origines. L’amortissement réduit progressivement l’influence d’une variation historique répétée sur 25 ans.")
    a.formula("g(h, φ) = (1 − φ<super>h</super>) / (1 − φ)     ·     D<sub>τ</sub>(t+h) = Y<sub>t</sub> + β<sub>τ</sub> g(h, φ)")
    a.p("Y désigne les inscriptions. Pour chaque quantile τ de 0,20, 0,50 et 0,80, la pente β minimise la somme des pertes asymétriques ρ<sub>τ</sub>(u) = max(τu, (τ − 1)u), avec u égal à la variation observée moins βg. Comme g est positif, le minimum est le quantile pondéré des variations divisées par g, de poids g. Le résultat est arrondi à l’élève entier, avec un plancher à zéro.")
    a.h("Validation à origine glissante")
    a.p("À chaque origine, l’ajustement utilise les années déjà observées. Six cibles à un an et cinq à deux ans servent au choix de l’amortissement et à la comparaison des modèles. La perte quantile moyenne retient φ = 0,95 (103 722 élèves) devant 0,80 (104 003). Une évaluation indépendante demanderait de nouveaux millésimes.")
    stats=data["validation"]
    def score(model,h):return next(r for r in stats if r["model"]==model and r["horizon"]==h)
    a.table(["Modèle","MAE à 1 an","MAE à 2 ans","Biais à 1 an"],[[label,num(score(k,1)["mae"]),num(score(k,2)["mae"]),num(score(k,1)["bias"])] for k,label in [("last","Dernier niveau observé"),("trend","Tendance linéaire"),("damped","Tendance amortie"),("quantile80","Régression quantile, φ = 0,80"),("quantile95","Régression quantile, φ = 0,95")]], [.45,.19,.19,.17],(1,2,3))
    a.p("Les trois pentes apprises valent environ −73 731, −26 747 et +125 535 élèves par unité d’horizon amorti. La reconduction du dernier effectif obtient la plus faible MAE pour le niveau central, aux deux horizons testés. Le modèle quantile fournit trois trajectoires ordonnées avec un seul coefficient par scénario. Les 17 paires se recouvrent dans le temps et les tests portent sur onze prévisions à court terme.")
    a.note("La MAE est la moyenne des écarts absolus en élèves. Un biais positif indique une surestimation moyenne. Les rangs de 20 %, 50 % et 80 % décrivent les variations apprises. Leur couverture probabiliste à 25 ans reste inconnue. "+link("https://www.aeaweb.org/articles?id=10.1257/jep.15.4.143","Koenker et Hallock (2001), Quantile Regression")+". "+link("https://otexts.com/fpp3/toolbox.html","Hyndman et Athanasopoulos, Forecasting: Principles and Practice, 3e éd., § 5.10")+".")

    a.page("04","La méthode","Répartir la demande par province","Le modèle apprend la trajectoire nationale. Les données locales déterminent comment cette demande se répartit sur le territoire.")
    a.p("Soit E<sub>p,2025</sub> l’effectif public recensé dans la province p et P<sub>p,t</sub> sa population projetée de 6 à 11 ans. Une province gagne du poids relatif si cette population augmente plus vite que celle de ses voisines. Le comportement de scolarisation et la part du public sont représentés par le rapport initial, qui constitue une hypothèse de stabilité.")
    a.formula("w<sub>p,t</sub> = E<sub>p,2025</sub> × P<sub>p,min(t,2035)</sub> / P<sub>p,2025</sub>")
    a.p("La part d’une province est son poids divisé par la somme des poids du périmètre autorisé. La trajectoire basse entière est répartie par la méthode des plus forts restes. Les mêmes parts servent ensuite à répartir les incréments centrale moins basse, puis haute moins centrale. Chaque province conserve l’ordre des scénarios. Leur somme retrouve, à l’élève près, le total national de chaque année.")
    a.h("Jusqu’en 2035, puis jusqu’en 2050")
    a.p("De 2026 à 2035, le profil démographique varie chaque année. De 2036 à 2050, les parts relatives de 2035 restent constantes et la demande scolaire continue d’évoluer selon les trois trajectoires apprises. La colonne population à l’horizon reste vide après 2035. Une estimation de population en 2050 exigerait d’autres hypothèses de fécondité, mortalité et migration.")
    a.h("Transformer la demande en groupes")
    a.formula("q = max(1, plancher(45 × 0,95)) = 42     ·     G = plafond(D / q)")
    a.p("La taille de groupe et le facteur de correspondance sont des paramètres de travail. À l’échelle provinciale, les salles manquantes valent max(0, G − salles inventoriées en 2025). Les enseignants manquants valent max(0, G − maîtres recensés en 2025). L’arrondi supérieur sert à pourvoir la dernière fraction de groupe.")
    a.h("Exemple vérifiable au Kadiogo")
    a.p("Au centre de la distribution en 2050, 175 649 élèves demandent 4 183 groupes de 42 places. Face aux 3 074 salles et 3 066 maîtres de 2025, les écarts atteignent 1 109 salles et 1 117 enseignants. Le diagnostic provincial maintient ces stocks constants.")
    a.h("Sensibilité à la démographie territoriale")
    a.p("À demande nationale centrale identique, le gel des parts scolaires dès 2025 attribuerait 166 811 élèves au Kadiogo en 2050. L’ajustement par les 6–11 ans jusqu’en 2035 porte ce chiffre à 175 649, soit 8 838 élèves d’écart. L’évolution de la géographie change ainsi les priorités même lorsque le total national est fixé.")

    a.page("04","La méthode","Faire évoluer les ressources","La simulation régionale tient un compte annuel distinct des salles utilisables, des salles fermées et des enseignants disponibles.")
    a.p("Au départ, le modèle retient 95 % de disponibilité pour les salles et les maîtres recensés, avec arrondi inférieur par région. Une collecte validée de ressources effectivement utilisables prime pour la région correspondante. Chaque année, 0,5 % des salles sont retirées, puis 0,5 % des salles utilisables restantes deviennent indisponibles. Le taux de départ du personnel est de 1,5 %. Les flux d’attrition sont arrondis à l’entier inférieur.")
    a.formula("Places servies = min(demande, 42 × min(salles utilisables, enseignants disponibles))")
    a.p("Le déficit d’une ressource vaut max(0, plafond(demande / 42) − stock régional disponible). Les déficits positifs régionaux sont additionnés. Pour le personnel, le stock annuel reprend le stock précédent, retranche les départs, ajoute les recrues et les transferts entrants, puis retranche les transferts sortants. Pour les salles, les constructions et les réouvertures compensent les retraits et les fermetures.")
    a.table(["Hypothèse de programme","Plafond pour les 13 régions","Première livraison possible"],[
      ["Construire","20 salles par an","2027 · délai de 2 ans"],["Réhabiliter","5 salles par an","2026 · délai de 1 an"],["Recruter","25 enseignants par an","2026 · délai de 1 an"],["Redéployer","10 transferts par an","2026 · départ et arrivée simultanés"]],[.32,.30,.38])
    a.p("La référence laisse agir les pertes de stock. L’intervention combinée choisit successivement les actions qui ouvrent un groupe. Elle privilégie le gain de places, puis le déficit relatif, le nombre d’actions nécessaires, le coût d’investissement et, à égalité, la réhabilitation. Un transfert mobilise un excédent du donneur et conserve le nombre national d’enseignants.")
    a.p("L’investissement annuel additionne constructions × coût de construction et réhabilitations × coût de remise en service. Le fonctionnement annuel associe salaires et maintenance. En l’absence de tarifs, une dépense qui mobilise une ressource reste indéterminée. Une action sans livraison porte un investissement nul. L’algorithme produit une solution réalisable sous les plafonds indiqués. L’optimalité globale et les déplacements individuels restent à instruire.")
    a.note("À stocks combinés inchangés en 2050, le test de sensibilité central donne 875 893 places à couvrir pour une classe cible de 40 élèves, 757 061 pour 45 et 608 521 pour 50. Le facteur de correspondance reste fixé à 0,95. Une fermeture temporaire et une réhabilitation changent la disponibilité d’une salle existante. La construction accroît le parc. Les périodes de programmation sont consultables par tranches de cinq ans dans Atlas.")

    a.page("05","Les résultats","Trois demandes possibles en 2050","L’enveloppe des scénarios provient de la variabilité des inscriptions observées. Les écarts de couverture changent fortement avec l’hypothèse de demande.")
    a.trend(data["historical"],data["trajectories"])
    a.table(["2050","Demande","Salles réf.","Salles comb.","Ens. réf.","Ens. comb.","Couverture comb."],[
      [NAMES[sc],num(national(2050,sc,"combine")["demand"]),*[num(national(2050,sc,opt)[k]) for k in ("rooms_needed","teachers_needed") for opt in ("reference","combine")],num(100*national(2050,sc,"combine")["coverage"],1)+" %"] for sc in NAMES],[.11,.155,.14,.15,.13,.14,.175],(1,2,3,4,5,6),8.6)
    a.note("Les colonnes « Salles » et « Ens. » comptent les salles et les enseignants manquants, en référence (réf.) et après intervention combinée (comb.). La couverture divise les places servies par la demande. Les déficits s’additionnent sur les 13 régions.")
    a.h("Le jalon 2030 dans le scénario central")
    a.p("Pour 2 270 333 inscriptions, l’intervention combinée laisse 12 722 salles et 14 609 enseignants à couvrir en 2030. La référence laisse 12 724 salles et 14 731 enseignants. De 2030 à 2050, la demande centrale baisse, tandis que les pertes de capacité cumulées augmentent le besoin résiduel.")
    a.image("m13-exercice","Figure 5. Comparateur M13 du portail de l’instance personnelle. Les deux éditions d’exercice ont le même périmètre et le même horizon. Le comparateur reprend la trajectoire enregistrée dans chacune.",80)
    diff= national(2050,"haut","combine")["demand"]-national(2050,"bas","combine")["demand"]
    a.p(f"Les trajectoires haute et basse sont séparées de {num(diff)} inscriptions en 2050. Les baisses et les reprises de la série courte, dont le creux de 2022/2023, contribuent à cette amplitude. Seule l’intervention change entre les deux politiques d’une même trajectoire.")

    a.page("05","Les résultats","Quels écarts entre les régions ?","Scénario central en 2050. Les déficits tiennent compte du vieillissement des stocks et des actions effectivement allouées.")
    refs={r["region"]:r for r in area(2050,"central","reference")}
    combined=area(2050,"central","combine")
    a.table(["Région historique","Salles<br/>référence","Salles<br/>combinée","Enseignants<br/>référence","Enseignants<br/>combinée","Places restant<br/>à couvrir¹"],
      [[r['name'],num(refs[r['region']]['rooms_needed']),num(r['rooms_needed']),num(refs[r['region']]['teachers_needed']),num(r['teachers_needed']),num(r['unserved'])] for r in combined]+[["<b>Total</b>",num(ref["rooms_needed"]),num(central["rooms_needed"]),num(ref["teachers_needed"]),num(central["teachers_needed"]),num(central["unserved"])]],
      [.245,.14,.14,.155,.155,.165],(1,2,3,4,5),8.6)
    a.note("¹ Places encore nécessaires après l’intervention combinée. L’écart national atteint 757 061 places. Il mesure des élèves dont la demande simulée dépasse la capacité.")
    a.p("Au Sud-Ouest, dix enseignants sont transférés vers d’autres régions dès 2026. Avec les départs ultérieurs et leur arrondi annuel, l’écart restant en 2050 est de huit enseignants. Le besoin enseignant y passe de 429 en référence à 437 en intervention combinée.")

    def three(sc,k):
        return " · ".join(f"{r['name']} ({num(r[k])})" for r in sorted(area(2050,sc,"combine"),key=lambda r:-r[k])[:3])
    a.table(["Demande en 2050","Trois premières régions pour les salles","Trois premières pour les enseignants"],[[NAMES[sc],three(sc,"rooms_needed"),three(sc,"teachers_needed")] for sc in NAMES],[.20,.40,.40])
    a.page("05","Les résultats","Trois provinces à examiner d’abord","Le diagnostic provincial identifie la pression sur l’inventaire public recensé en 2025, avant toute attribution locale du programme régional.")
    top=sorted(provinces("central"),key=lambda x:-x["rooms_gap"])[:3]
    a.table(["Province","Demande 2050","Salles 2025","Maîtres 2025","Salles manq.","Ens. manq."],[[r["province"],*[num(r[k]) for k in ("demand","rooms","teachers","rooms_gap","teachers_gap")]] for r in top],[.23,.17,.15,.15,.15,.15],(1,2,3,4,5))
    a.image("diagnostic-provincial","Figure 6. Comparateur d’interventions d’Atlas, profil Analyste. Le classement porte sur les enseignants manquants parmi les 45 provinces. Le filtre régional et le téléchargement permettent de reprendre les lignes affichées.",344)
    a.p("Kadiogo, Houet et Sanmatenga arrivent en tête des deux classements centraux à stocks constants. En scénario haut, leurs déficits atteignent respectivement 5 700, 4 302 et 3 336 salles. En scénario bas, seul le Loroum conserve un déficit de salles (61), tandis que les manques d’enseignants persistent notamment au Loroum (61), au Séno (19) et en Kompienga (3).")
    a.note("Les stocks régionaux intègrent annuellement départs et interventions. La somme des déficits provinciaux à inventaire figé répond à une question différente. La base scolaire figure dans l’"+link(dg+"#page=12","annuaire primaire 2024–2025")+".")

    a.page("06","La réponse au défi","Programmer les vérifications de terrain","Le classement donne une priorité d’instruction. Le choix d’une parcelle, d’une école ou d’une affectation nominative exige une enquête locale.")
    a.h("Arbitrer conjointement locaux et personnel")
    a.p("En scénario central, 625 recrutements, 10 transferts, deux réhabilitations et aucune construction sont retenus de 2026 à 2050 par l’heuristique combinée. L’action doit ouvrir un groupe immédiatement. Lorsque le personnel limite la capacité, une salle isolée peut rester sans gain immédiat. Le recrutement seul sert 42 élèves de plus que la combinaison par défaut en 2050. Le décideur peut ainsi comparer l’efficacité, l’équité et la situation des régions donneuses avant de retenir un programme.")
    a.p("Le Yatenga compte 166 écoles sans eau potable et 104 sans latrines fonctionnelles en 2025. La Comoé compte 159 écoles sans eau. Le Sanmatenga cumule 121 écoles sans eau et 107 sans latrines fonctionnelles avec le troisième déficit provincial de salles du scénario central. Ces indicateurs peuvent orienter les visites et les dossiers de réhabilitation.")
    a.h("Localiser un investissement")
    a.p("Pour chaque province prioritaire, la direction territoriale peut rapprocher les identifiants et noms d’écoles, les localités INSD et les points OpenStreetMap, puis vérifier les ouvertures avec les rapports ESU. Confronter ensuite les temps de trajet, le foncier, l’eau, les latrines, les qualifications disponibles et les coûts. Une absence dans OpenStreetMap ne suffit pas pour classer une localité en « zone blanche ».")
    a.image("interventions","Figure 7. Comparateur d’interventions, scénario central, environnement de test. Le programme combiné sert 21 840 élèves de plus que la référence. Les coûts non renseignés apparaissent comme indisponibles.",246)

    a.page("06","La réponse au défi","Arbitrer entre les trois trajectoires","Une priorité de terrain gagne en solidité lorsqu’elle persiste dans plusieurs hypothèses de demande.")
    a.p("Les Hauts-Bassins figurent parmi les trois premiers déficits d’enseignants dans les trois scénarios. Le Centre est prioritaire pour les salles en demandes basse et centrale. Si la demande suit la trajectoire haute, le Centre-Ouest arrive en tête pour les deux ressources. Une première instruction peut donc porter sur les affectations dans les Hauts-Bassins et sur la capacité à augmenter rapidement l’offre au Centre-Ouest.")
    a.table(["Demande en 2050","Salles neuves","Salles réhabilitées","Recrues","Transferts","Places gagnées¹"],
        [[NAMES[sc],*[num(national(2050,sc,"combine")[k]) for k in ("new_rooms","rehabilitated","new_teachers","transfers")],
          num(national(2050,sc,"combine")["served"]-national(2050,sc,"reference")["served"])] for sc in NAMES],
        [.20,.145,.17,.14,.145,.20],(1,2,3,4,5))
    a.note("¹ Différence de places servies en 2050 par rapport à la référence de la même trajectoire. Les quatre colonnes de moyens cumulent les livraisons ou mouvements de 2026 à 2050. Une même personne peut faire l’objet de plusieurs mouvements.")
    a.h("Comment interpréter un plafond peu utilisé")
    a.p("Dans le scénario haut, 625 recrutements ouvrent des groupes, tandis que l’algorithme ne livre aucune salle neuve. Cette allocation traduit le critère de gain immédiat et les plafonds annuels. Les 65 910 salles manquantes justifient de chiffrer un programme associant plus de salles et d’enseignants, puis de le tester avec les régions.")
    a.h("Du résultat calculé à sa diffusion")
    a.image("autorisation-2050.jpg","Figure 8. Extrait du registre du portail de travail au 18 novembre 2026. Les deux éditions nationales sont au stade « Diffusion autorisée ». La mention « Mise en ligne attendue » situe précisément l’étape atteinte.",145)
    a.p("Le validateur examine les calculs dans M11 puis vérifie la fiche de diffusion. Dans M12, le décideur autorise la diffusion et un autre titulaire publie l’édition. La figure 5 a été prise sur le portail de l’instance personnelle, où les éditions d’exercice ont parcouru toutes ces étapes.")

    a.page("07","Reproduction","Refaire et contrôler les calculs","Le classeur, le référentiel des provinces et les deux bibliothèques Excel sont inclus dans l’édition du dépôt utilisée pour cette étude.")
    a.h("1. Préparer une copie du dépôt")
    a.p("Télécharger "+link(EDITION,"Atlas Éducation, version 188dd58")+". Depuis sa racine, lancer python3 demarrer.py preparer, ou py -3 demarrer.py preparer sous Windows. Avec Python 3.10 ou ultérieur et son module venv, cette commande prépare une instance hors ligne. Le moteur utilisé est "+data["version"]+".")
    a.h("2. Recalculer les cinq jalons et exporter le classeur")
    a.p("Se placer dans le dossier atlas-education. Ouvrir l’interpréteur du projet avec ../.venv/bin/python sur macOS ou Linux, ou ..\\.venv\\Scripts\\python.exe sous Windows. Y saisir ces trois lignes.")
    a.code(["from pathlib import Path",
            "from scripts.reproduire_defi import replay",
            'replay(next(Path("..").glob("DONNEES*.xlsx")), Path("../resultats-personnels"), excel=True)'])
    a.p("Le dossier resultats-personnels contient Atlas-resultats-calcules.xlsx, trois CSV et resultats.json. Pour les jalons 2030, 2035, 2040, 2045 et 2050, attendre 30 lignes nationales, 390 régionales et 675 provinciales hors en-têtes. Chaque somme territoriale de demande retrouve la demande nationale du même scénario.")
    a.h("3. Vérifier un résultat dans l’interface")
    a.p("Depuis la racine, lancer python3 demarrer.py (py -3 demarrer.py sous Windows). Dans « Publications », comparer les éditions d’exercice basse et haute. En 2049/2050, M13 doit afficher 1 325 765 et 4 205 603 élèves. En demande centrale, le classeur doit donner 13 522 salles et 18 033 enseignants manquants après intervention combinée.")
    a.h("Identifier exactement les sources")
    a.table(["Entrée du calcul","Début de l’empreinte SHA-256"],[
        ["Classeur du Data Challenge",data["workbook"]["sha256"][:24]],
        *[[label,sources[k]["sha256"][:24]] for k,label in (("annuaire","Annuaire du primaire 2024–2025"),("demographie","Projections démographiques INSD"),("localites","Fichier des localités 2019"))]],[.55,.45],size=8.8)
    a.note("Les empreintes intégrales figurent dans resultats.json. Pour refaire l’extraction des trois PDF avec Poppler ou relancer la recette des modules M00 à M14 et les 57 tests distincts, consulter le "+link("https://github.com/szidama/datachallenge2026/blob/188dd58ba1e444603d3aeace54ef217503719ff6/atlas-education/README.md","guide de reproduction et de vérification")+".")
    a.save()


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("resultats",type=Path)
    cli.add_argument("sortie",type=Path,help="Rapport en .pdf ou .docx")
    args=cli.parse_args()
    write(json.loads(args.resultats.read_text(encoding="utf-8")),args.sortie)
