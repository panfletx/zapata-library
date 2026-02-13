#!/usr/bin/env python3
"""
Build subject_map.yaml by mapping 4,800+ raw Zotero subjects to ~360 clean categories.

Uses keyword/pattern matching to classify each raw subject string.
Outputs:
  - data/subject_map.yaml  (raw subject → list of new categories)
  - Reports unmapped subjects to stderr for manual review
"""

import re
import yaml
import os

# ──────────────────────────────────────────────
# CATEGORY DEFINITIONS: keyword patterns → category
# Order matters: first match wins for each rule group,
# but a subject can match multiple groups.
# ──────────────────────────────────────────────

# Junk patterns to remove entirely
JUNK_PATTERNS = [
    r'^\d{4}-\d{4}$',           # date ranges: 1900-1999
    r'^\d{4}s?$',               # bare years: 1976, 1980s
    r'^To \d+$',                # "To 1500"
    r'^\d+\.?\d*\s',            # classification codes: "18.33 Spanish-American..."
    r'^dt\.\s',                 # German print date: "dt. 1976"
    r'^name\s',                 # "name José Dimayuga dt. 2003"
    r'^author$',
    r'^authors$',
    r'^Authors$',
    r'^trad\.$',
    r'^trad$',
    r'^OCLC',
    r'^ISBN',
    r'^Spaans$',                # Dutch for "Spanish" — not a subject
    r'^Spanish language materials$',
    r'^Spanish language$',
    r'^Materiales en español$',
    r'^texto$',
    r'^Text$',
    r'^Textes$',
    r'^Sources$',
    r'^sources$',
    r'^dedicatoria',
    r'^Französisch$',
    r'^Spanisch$',
    r'^Frans$',
    r'^Duits$',
    r'^Engels$',
    r'^Portugees$',
    r'^Katalanisch$',
    r'^Letterkunde$',
    r'^letterkunde$',
    r'^French language materials$',
    r'^German language materials$',
    r'^Early works$',
    r'^Early works to \d+',
    r'^Ouvrages avant \d+',
    r'^Aufsatzsammlung$',
    r'^Erzählung$',
    r'^Quelle$',
    r'^Belletristische Darstellung$',
    r'^Catalogs$',
    r'^Catalogues$',
    r'^Directories$',
    r'^Indexes$',
    r'^Handbooks.*manuals',
    r'^Registers$',
    r'^str\. \d+',             # German "Streitschrift" dates
    r'^Popular Work$',
    r'^Problems and exercises$',
    r'^Prose \(texts\)$',
    r'^Stories \(texts\)$',
    r'^Adaptations$',
    r'^Anecdotes$',
    r'^Miscellanea$',
    r'^Specimens$',
    r'^Outlines',
    r'^Pictorial works$',
    r'^\d+-\d+$',               # more date ranges: 30-600, 450-1100, etc.
    r'^\d+\.\d+$',              # classification codes: 7.310
    r'^S\.\s*X[XVI]+',          # "S. XX", "S. XIX"
    r'^Siglo\s+X[XVI]+=?$',     # "Siglo XX", "Siglo XIX="
    r'^Since\s+\d+$',           # "Since 1950", "Since 1900"
    r'^VDOBIBL$',
    r'^jjb$',
    r'^misscover$',
    r'^nota vampiro$',
    r'^monographie imprimée$',
    r'^printed monograph$',
    r'^anotations$',
    r'^str\.$',
    r'^Corrugated board',
    r'^Accordion fold',
    r'^Painted bindings',
    r'^Slipcases',
    r'^exercise books$',
    r'^readers$',
    r'^Video\s+(recordings|tapes)',
    r'^Vidéos\b',
    r'^Enregistrements sonores$',
    r'^Sound recordings',
    r'^sound recordings$',
    r'^Case studies$',
    r'^Dissertations',
    r'^Academic Dissertations',
    r'^Tesis académicas$',
    r'^Thèses et écrits',
    r'^Actes de congrès$',
    r'^Aufgabensammlung$',
    r'^Best books$',
    r'^Meilleurs ouvrages$',
    r'^Libros$',
    r'^livre$',
    r'^Livres numériques$',
    r'^Descripción$',
    r'^Guides et manuels$',
    r'^Guías$',
    r'^Handbook$',
    r'^Reviews$',
    r'^Revues$',
    r'^Periodicals$',
    r'^Nuestros clásicos$',
    r'^Commentaries$',
    r'^Chronologies$',
    r'^chronologies\b',
    r'^Ideengeschichte\b',
    r'^Entstehung$',
    r'^Begriff$',
    r'^Verzeichnis$',
    r'^Produktie$',
    r'^Tables\b',
    r'^tables\b',
    r'^Id$',
    r'^In art$',
    r'^Texts$',
    r'^Text edition$',
    r'^Textanalyse$',
    r'^Textos antiguos$',
    r'^Español$',
    r'^7$',
    r'^CIEG$',
    r'^Civilización moderna',
    r'^Facsimiles$',
    r'^Activities of Daily Living$',
    r'^Activités de la vie quotidienne$',
    r'^Life Style$',
    r'^Homes$',
    r'^Annotations\b',
    r'^Behavior modification$',
    r'^Modification du comportement$',
    r'^Comportement compulsif$',
    r'^Compulsive behavior$',
    r'^Conducta$',
    r'^Conducta\b.*\bModificaci',
    r'^Conocimiento$',
    r'^Prise de conscience$',
    r'^Self-instruction$',
    r'^Stampa\b',
    r'^Libri\b',
    r'^Braille\b',
    r'^Problèmes et exercices$',
    r'^Estetica$',
    r'^Esthétique$',
    r'^Altfranzösisch$',
    r'^Amerikanisches Englisch$',
    r'^Foreign languages\b',
    r'^Formules\b',
    r'^Cronología\b',
    r'^Collected works$',
    r'^Lola rennt$',  # film title not a subject
    r'^Pamela\b',     # novel title
    r'^Macondo\b',    # fictional place
    r'^Tiempo Nublado$',  # book title
    r'^Como agua para chocolate',  # book title
    r'^Life and opinions of',  # book title
    r'^Through the looking glass$',  # book title
    r'^Under the volcano\b',  # book title
    r'^Popol vuh$',  # handled by rules instead
    r'^VIDA$',
    r'^État\b',
    r'^Fuentes documentales$',
    r'^Éducation morale$',
]

# ──────────────────────────────────────────────
# Pattern → category mappings
# Each entry: (compiled_regex, [categories])
# Applied case-insensitively unless noted
# ──────────────────────────────────────────────

RULES = []

def rule(pattern, categories, flags=re.IGNORECASE):
    """Register a mapping rule."""
    RULES.append((re.compile(pattern, flags), categories if isinstance(categories, list) else [categories]))

# ─── LITERARY FORM & GENRE ───

rule(r'\bfiction\b|\broman[s]?\b(?!ti[ck])|\bnovela[s]?\b|\bfictional work\b|\bromances\b', 'Fiction')
rule(r'\bnovel[s]?\b(?!la)', 'Novel')
rule(r'\bnovella[s]?\b', 'Novella')
rule(r'\bshort stor|nouvelle[s]?\b|\bcuento[s]?\b|\brelato[s]?\b', 'Short Stories')
rule(r'\bpoem[s]?\b|\bpoetry\b|\bpo[eé]sie\b|\bpo[eé]t|vers\b|\blyric', 'Poetry')
rule(r'\bessay[s]?\b|\bensayo[s]?\b', 'Essay')
rule(r'\bdrama[s]?\b|\bplay[s]?\b|\btraged|comed[iy]|\btheater\b|\btheatre\b|\bthéâtre\b|\bteatro\b', 'Drama')
rule(r'\bbiograph|\bvida[s]?\b.*\b(de|y)\b|\blife of\b', 'Biography')
rule(r'\bautobiograph|\bm[eé]moire[s]?\b|\bmemoir[s]?\b|\brecuerdo[s]?\b', 'Autobiography & Memoir')
rule(r'\bdiar[iy]|\bjournal intime|\bcuaderno|\bcarnet', 'Diary & Letters')
rule(r'\bcorrespond|\bletter[s]?\b|\bépistolaire|\bcarta[s]?\b.*literari', 'Correspondence')
rule(r'\binterview[s]?\b|\bentretien[s]?\b|\bentrevista[s]?\b', 'Interview')
rule(r'\bantholog|\bantología|\brecueil|\bcollection[s]?\b|\brecopilaci[oó]n', 'Anthology')
rule(r'\bcriticism\b|\bcritique\b|\bcrítica\b|\binterpretation\b|\bhermeneutic', 'Literary Criticism')
rule(r'\bchronicle|\bcr[oó]nica[s]?\b', 'Chronicle')
rule(r'\btestimon', 'Testimonio')
rule(r'\bsatir|\bhumor|\bhumour|\birony|\bironi|\bparody|\bparodia', 'Satire & Humor')
rule(r'\bhistorical fiction\b|\bnovela hist[oó]rica', 'Historical Fiction')
rule(r'\bmagic[al]* realis|\brealismo m[aá]gico', 'Magical Realism')
rule(r'\bscience fiction\b|\bciencia ficci[oó]n', 'Science Fiction')
rule(r'\bdetective\b|\bmystery\b|\bpolicíac|\bnoir\b|\bthriller\b', 'Detective & Mystery')
rule(r'\bhorror\b|\bgothic\b|\bg[oó]tico', 'Horror & Gothic')
rule(r'\berotic\b|\ber[oó]tic|\bpornograph', 'Erotic Literature')
rule(r'\bchildren|juvenile|\binfantil|\bjuvenil', "Children's Literature")
rule(r'\bcomic[s]?\b|\bgraphic novel|\bbande dessin[eé]e|\bhistorieta', 'Comics & Graphic Novel')
rule(r'\bfolklore\b|\boral tradition|\btradici[oó]n oral|\bleyenda[s]?\b|\blegend[s]?\b', 'Oral Tradition & Folklore')
rule(r'\bfable[s]?\b|\bfábula|\bparable|\bparábola', 'Fable & Parable')
rule(r'\bepic\b|\bépic|\bepopeya', 'Epic')
rule(r'\baphoris|\baforismo', 'Aphorism')
rule(r'\bspeech|\blecture|\bconferencia|\bdiscours', 'Speech & Lecture')
rule(r'\btravel writ|\brelato[s]? de viaje|\bviajero|\btraveler', 'Travel Writing')
rule(r'\bjournalis|\bperiodis|\bnews.*article|\bartículo.*periódico|\breportaje', 'Journalism')
rule(r'\bmanifest[o]?\b', 'Manifesto')
rule(r'\bepistolar', 'Epistolary')
rule(r'\bscreenplay\b|\bguion|\bscript\b', 'Screenplay')

# ─── LITERARY MOVEMENTS ───

rule(r'\bbaroqu|\bbarroc', 'Baroque')
rule(r'\bromanticis|\bromanti[ck]', 'Romanticism')
rule(r'\brealis[mt]|\brealista', 'Realism')
rule(r'\bnaturalis[mt]', 'Naturalism')
rule(r'\bmodernismo\b|\bmodernista\b', 'Modernismo')
rule(r'\bsymbolis[mt]|\bsimbolism', 'Symbolism')
rule(r'\bsurrealis|\bsurrealisme|\bsurrealista', 'Surrealism')
rule(r'\bavant.?garde|\bvanguard', 'Avant-garde')
rule(r'\bboom\b.*latin|\blatin.*\bboom\b', 'Latin American Boom')
rule(r'\boulipo\b', 'Oulipo')
rule(r'\bbeat generation\b', 'Beat Generation')
rule(r'\bnégritude\b|\bnegritud', 'Négritude')
rule(r'\bpostmodern|\bposmodern', 'Postmodernism')

# ─── SEXUALITY & GENDER ───

rule(r'\bqueer\b|\bLGBT|\bsexual minorit|\bdiversidad sexual', 'Queer Studies')
rule(r'\bgay\b(?! nineties)|\bhomosexu[ae]l|\bsame.?sex|\bhomoeroti|\bsodom', 'Gay Literature')
rule(r'\blesbian|\blesbienne|\blesbiana', 'Lesbian Studies')
rule(r'\bbisexual', 'Bisexuality')
rule(r'\btransgend|\btransexual|\btranssexual|\btravesti', 'Transgender Studies')
rule(r'\beroti[ck]|\bsexualit[eéy]|\bsexual behav|\bsexual[ei]', 'Sexuality & Eroticism')
rule(r'\bgender\b|\bgénero\b.*\b(sexual|literari)', 'Gender Studies')
rule(r'\bfeminis[mt]|\bwomen.*(?:role|right|status|movement)', 'Feminism')
rule(r'\bmasculinit', 'Masculinity')
rule(r'\bdrag\b.*\b(queen|king|show)|\bcamp\b.*aestheti', 'Drag & Camp')

# ─── IDENTITY & SOCIETY ───

rule(r'\brace\b|\bracial|\bracis[mt]|\bethnicit', 'Race & Ethnicity')
rule(r'\bindigenous\b|\bind[ií]gena|\bnative\b.*people|\baztec|\bmaya\b|\bnahua|\bzapotec', 'Indigenous Peoples')
rule(r'\bcolonial|\bpostcolonial|\bimperialis', 'Colonialism & Postcolonialism')
rule(r'\bmigrat|\bexile|\bexilio|\bemmigr|\bimmigr|\bdiaspora|\brefugee|\bexpatri', ['Migration & Exile'])
rule(r'\bnational identity|\bidentidad nacional|\bnationalis', 'National Identity')
rule(r'\burban\b|\bcity life|\bciudad|\bmetropol', 'Urban Life')
rule(r'\brural\b|\bcountryside|\bcampo\b|\bpeasant|\bcampesin', 'Rural Life')
rule(r'\bpoverty\b|\bpobreza|\bsocial class|\bworking class|\bproletari', 'Poverty & Class')
rule(r'\bslaver[y]?\b|\besclavitud|\bslave[s]?\b', 'Slavery')
rule(r'\bmestiz', 'Mestizaje')
rule(r'\bafro.?latin|\bafro.?mexic|\bafro.?brasil|\bnegrit', 'Afro-Latin')
rule(r'\bprison[s]?\b|\bcárcel|\bincarcerat', 'Prison')

# ─── HISTORY & POLITICS ───

rule(r'\bhistor[iy]|\bhistoire|\bhistoria\b', 'Modern History')
rule(r'\bmediev|\bmoyen [aâ]ge|\bedad media|\bmiddle ages', 'Medieval History')
rule(r'\bancient\b|\bantiqu|\bantigü', 'Ancient History')
rule(r'\bcontempor', 'Contemporary History')
rule(r'\bmexi[ck]an revolution|\brevolución mexicana|\bzapata\b.*revolution', 'Mexican Revolution')
rule(r'\bpolitics\b|\bpolítica\b|\bpolitical\b|\bgovernment\b|\bgobierno\b', 'Latin American Politics')
rule(r'\bwar\b|\bguerra\b|\bconflict|\bbattle|\bsoldier', 'War & Conflict')
rule(r'\bhuman rights\b|\bderechos humanos', 'Human Rights')
rule(r'\bcensor', 'Censorship')
rule(r'\bsocial movement|\bmovimiento social|\bprotest\b|\brevolt\b|\brevolu[ct]', 'Social Movements')
rule(r'\bmarx|\bcommunis|\bsocialis[mt]', 'Marxism')
rule(r'\bconquest\b|\bconquista\b|\bcolonizat|\bconquistador', 'Conquest of Mexico')
rule(r'\bpre.?columb|\bprehisp[aá]ni|\bmesoameric', 'Pre-Columbian')

# ─── PHILOSOPHY ───

rule(r'\bphilosoph|\bfilosof', 'Philosophy')
rule(r'\bethic[s]?\b|\bética\b|\bmoral[s]?\b', 'Ethics')
rule(r'\baesthetic|\bestétic', 'Aesthetics')
rule(r'\bexistential', 'Existentialism')
rule(r'\bstructural|\bpostestructural|\bdeconstruct|\bsemioti|\bsign[s]?\b.*\bsystem', 'Structuralism & Poststructuralism')
rule(r'\bmetaphysi|\bontolog', 'Metaphysics')

# ─── PSYCHOLOGY ───

rule(r'\bpsychoanaly|\bpsicoanál|\bfreud|\blacan|\bjung\b', 'Psychoanalysis')
rule(r'\bdesire\b|\bdeseo\b|\bsubjectivit', 'Desire & Subjectivity')
rule(r'\bmadness\b|\binsanit|\blocura\b|\bmental\b.*\bill', 'Madness & Mental Illness')
rule(r'\bdream[s]?\b|\bsueño[s]?\b|\boneiric', 'Dreams')
rule(r'\btrauma\b', 'Trauma')
rule(r'\bmemory\b|\bmemoria\b|\brecollect|\bremembr', 'Memory')

# ─── RELIGION ───

rule(r'\breligion\b|\breligious\b|\breligió', 'Religion')
rule(r'\bcatholic|\bcatólic|\bchurch\b|\biglesia\b|\bpope\b|\bpapa\b.*\biglesia|\bvaticano', 'Catholicism')
rule(r'\bmystic|\bmístic', 'Mysticism')
rule(r'\bjudai[sc]|\bjewish\b|\bjudí|\bhebrew\b', 'Judaism')
rule(r'\bisla[mM]|\bmuslim|\bquran|\bcoran\b', 'Islam')
rule(r'\bbuddhi|\bbudis|\bzen\b', 'Buddhism')
rule(r'\bmytholog|\bmitolog', 'Mythology')
rule(r'\boccult|\besoteric|\besotéri|\balchem', 'Occult & Esoteric')
rule(r'\bdeath\b|\bmuerte\b|\bmort\b|\bmourning|\bduelo\b|\bfuneral|\bfunerari', 'Death & Mourning')
rule(r'\bsaint[s]?\b|\bsanto[s]?\b|\bhagiograph', 'Saints & Hagiography')

# ─── DAILY LIFE ───

rule(r'\blove\b|\bamor\b|\bamour\b', 'Love & Desire')
rule(r'\bfamil[iy]|\bfamilia\b|\bparent|\bmother|\bfather|\bmarriage|\bmatrimon', 'Family')
rule(r'\bchild(?:hood|ren)\b|\binfancia\b|\bniño', 'Childhood')
rule(r'\bfood\b|\bcooking\b|\bcuisine\b|\bgastrono|\bcocina\b|\bnutrit', 'Food & Gastronomy')
rule(r'\bnature\b|\benvironment|\bnaturaleza|\becolog|\blandscape|\bpaisaje', 'Nature & Environment')
rule(r'\banimal[s]?\b|\banimaux\b|\bfauna\b', 'Animals')
rule(r'\beducat|\benseñanza|\bpedagog|\bschool|\bescuela|\buniversit', 'Education')

# ─── SCIENCE ───

rule(r'\bscien[ct]|\bciencia\b', 'Science')
rule(r'\bmedicin|\bmédicin|\bmedical|\bhealth\b|\bsalud\b|\bdisease|\benfermedad', 'Medicine & Health')
rule(r'\blaw\b|\bjuridic|\bderecho\b|\bjustic|\bjusticia', 'Law')
rule(r'\becon[oó]mi', 'Economics')

# ─── ARTS & MEDIA ───

rule(r'\bmotion picture|\bcinema|\bcinéma|\bcine\b|\bfilm[s]?\b(?!ograph)|\bmovie|\bpelícula', 'Film & Cinema')
rule(r'\bphotograph|\bfotograf', 'Photography')
rule(r'\bpainting|\bpeinture|\bpintura\b|\bpainter|\bpintor', 'Painting')
rule(r'\bsculptur|\bescultur', 'Sculpture')
rule(r'\barchitect|\barquitectur', 'Architecture')
rule(r'\bmusic\b|\bmúsica\b|\bmusique\b|\bcomposer|\bcompositor', 'Music')
rule(r'\bopera\b|\bópera\b', 'Opera')
rule(r'\bdanc[ei]|\bdanza\b|\bballet\b', 'Dance')
rule(r'\bfashion\b|\bmoda\b', 'Fashion')
rule(r'\bmuseum|\bmusée|\bmuseo', 'Museums & Collections')

# ─── LANGUAGE & REFERENCE ───

rule(r'\bdictionar|\bdiccionari|\bdictionnaire', 'Dictionary')
rule(r'\bencycloped|\benciclopedi', 'Encyclopedia')
rule(r'\bgrammar\b|\bgramática\b|\blinguistic|\blingüístic|\blangue\b', 'Grammar & Linguistics')
rule(r'\btranslat|\btraducci[oó]n|\btraduction|\bübersetz', 'Translation Studies')
rule(r'\bbibliograph|\bbibliograf', 'Bibliography')
rule(r'\bliterary history\b|\bhistoria.*literar|\bhistoire.*littéra', 'Literary History')
rule(r'\brhetoric|\bretórica', 'Rhetoric')

# ─── GEOGRAPHIC ───

rule(r'\bmexico\b|\bméxico\b|\bmexique\b|\bmexiko\b|\bmexic(?:an[oa]?)\b', 'Mexico')
rule(r'\bmexico city\b|\bciudad de m[eé]xico\b|\bd\.?\s*f\.\b', 'Mexico City')
rule(r'\boaxaca\b', 'Oaxaca')
rule(r'\byucat[aá]n\b', 'Yucatán')
rule(r'\bveracruz\b', 'Veracruz')
rule(r'\bjalisco\b|\bguadalajara\b', 'Jalisco')
rule(r'\bchiapas\b', 'Chiapas')
rule(r'\bpuebla\b', 'Puebla')

rule(r'\bcuba\b(?!n)', 'Cuba')
rule(r'\bhavana\b|\bhabana\b', 'Havana')
rule(r'\bcarib', 'Caribbean')
rule(r'\bpuerto ric', 'Puerto Rico')
rule(r'\bha[ïi]ti\b', 'Haiti')
rule(r'\bguatemala\b', 'Guatemala')

rule(r'\bargentin[ae]\b', 'Argentina')
rule(r'\bbuenos aires\b', 'Buenos Aires')
rule(r'\bbra[sz]il\b|\bbrésil\b', 'Brazil')
rule(r'\brio de janeiro\b', 'Rio de Janeiro')
rule(r'\bchile\b(?!an)', 'Chile')
rule(r'\bcolombia\b(?!n)', 'Colombia')
rule(r'\bperu\b|\bpér[ou]\b', 'Peru')
rule(r'\bvenezuela\b', 'Venezuela')
rule(r'\buruguay\b', 'Uruguay')
rule(r'\becuador\b', 'Ecuador')
rule(r'\bbolivia\b', 'Bolivia')
rule(r'\blatin america|\bamérica latina|\bamér.*latin', 'Latin America')

rule(r'\bspain\b|\bespaña\b|\bespagne\b|\bspanien\b', 'Spain')
rule(r'\bmadrid\b', 'Madrid')
rule(r'\bbarcelona\b', 'Barcelona')
rule(r'\bfrance\b|\bfrankreich\b', 'France')
rule(r'\bparis\b', 'Paris')
rule(r'\bitaly\b|\bitali[ae]\b|\bitalie\b', 'Italy')
rule(r'\brome\b|\broma\b', 'Rome')
rule(r'\bgermany\b|\ballemagne\b|\bdeutschland\b', 'Germany')
rule(r'\bberlin\b', 'Berlin')
rule(r'\bvienna\b|\bwien\b', 'Vienna')
rule(r'\bunited kingdom\b|\bengland\b|\bgreat britain\b|\bangleterre\b', 'United Kingdom')
rule(r'\blondon\b|\blondres\b', 'London')
rule(r'\bdublin\b|\bireland\b|\birlande\b', 'Dublin')
rule(r'\bportugal\b', 'Portugal')
rule(r'\bnetherlands\b|\bholland|\bpays.bas', 'Netherlands')
rule(r'\bgreece\b|\bgrèce\b|\bgrecia\b', 'Greece')
rule(r'\brussia\b|\brussie\b|\brusia\b', 'Russia')
rule(r'\bmoscow\b|\bmoscou\b|\bmoscú\b', 'Moscow')
rule(r'\bprague\b|\bpraga\b', 'Prague')

rule(r'\bunited states\b|\bestados unidos\b|\bétats.unis\b|\bamerica[n]?\b', 'United States')
rule(r'\bnew york\b|\bnueva york\b', 'New York')
rule(r'\bcanada\b|\bcanadá\b', 'Canada')

rule(r'\bjapan\b|\bjapón\b|\bjapon\b', 'Japan')
rule(r'\bchina\b|\bchine\b', 'China')
rule(r'\bindia\b|\binde\b', 'India')
rule(r'\begypt\b|\bégypte\b|\begipto\b', 'Egypt')
rule(r'\bkorea\b|\bcorea\b', 'Korea')

rule(r'\bancient greece\b|\bgrecia antigua\b|\bgrèce antique\b', 'Ancient Greece')
rule(r'\bancient rome\b|\broma antigua\b|\brome antique\b', 'Ancient Rome')

# ─── NATIONAL LITERATURES ───

rule(r'\bmexican literature\b|\bliteratura mexicana\b|\blittérature mexicaine\b', 'Mexican Literature')
rule(r'\bargentine lit|\bliteratura argentina\b', 'Argentine Literature')
rule(r'\bbrazilian lit|\bliteratura brasileira\b|\blittérature brésilienne\b', 'Brazilian Literature')
rule(r'\bcuban lit|\bliteratura cubana\b', 'Cuban Literature')
rule(r'\bcolombian lit|\bliteratura colombiana\b', 'Colombian Literature')
rule(r'\bchilean lit|\bliteratura chilena\b', 'Chilean Literature')
rule(r'\bperuvian lit|\bliteratura peruana\b', 'Peruvian Literature')
rule(r'\blatin american lit|\bliteratura latinoamericana\b|\blittérature.*latino', 'Latin American Literature')
rule(r'\bspanish lit|\bliteratura española\b|\blittérature espagnole\b', 'Spanish Literature')
rule(r'\bfrench lit|\blittérature française\b|\bliteratura francesa\b', 'French Literature')
rule(r'\bamerican lit|\bliteratura (?:estadounidense|norteamericana)\b|\blittérature américaine\b', 'American Literature')
rule(r'\benglish lit|\bliteratura inglesa\b|\blittérature anglaise\b', 'English Literature')
rule(r'\bgerman lit|\bliteratura alemana\b|\blittérature allemande\b|\bdeutsche literatur', 'German Literature')
rule(r'\bitalian lit|\bliteratura italiana\b|\blittérature italienne\b', 'Italian Literature')
rule(r'\brussian lit|\bliteratura rusa\b|\blittérature russe\b', 'Russian Literature')
rule(r'\bjapanese lit|\bliteratura japonesa\b', 'Japanese Literature')
rule(r'\bclassical lit|\bliteratura clásica\b', 'Classical Literature')
rule(r'\bmedieval lit|\bliteratura medieval\b|\blittérature médiévale\b', 'Medieval Literature')
rule(r'\bchicano\b', 'Chicano Literature')
rule(r'\bcatalan\b|\bcatalà\b', 'Catalan Literature')
rule(r'\birish lit|\bliteratura irlandesa\b', 'Irish Literature')

# ─── NAMED SUBJECTS ───

rule(r'\boctavio paz\b|\bpaz,\s*octavio\b', 'Octavio Paz')
rule(r'\bneruda\b', 'Pablo Neruda')
rule(r'\breinaldo arenas\b|\barenas,\s*reinaldo\b', 'Reinaldo Arenas')
rule(r'\bcabrera infante\b', 'Guillermo Cabrera Infante')
rule(r'\bsade\b', 'Marquis de Sade')
rule(r'\boscar wilde\b|\bwilde,\s*oscar\b', 'Oscar Wilde')
rule(r'\bgarc[ií]a lorca\b|\blorca\b', 'Federico García Lorca')
rule(r'\bcervantes\b', 'Miguel de Cervantes')
rule(r'\bfreud\b', 'Sigmund Freud')
rule(r'\bbu[ñn~]uel\b', 'Luis Buñuel')
rule(r'\balmod[oó]var\b', 'Pedro Almodóvar')
rule(r'\bfrida kahlo\b|\bkahlo\b', 'Frida Kahlo')
rule(r'\bdiego rivera\b|\brivera,\s*diego\b', 'Diego Rivera')
rule(r'\bdal[ií]\b.*salvador|\bsalvador dal[ií]', 'Salvador Dalí')
rule(r'\bemiliano zapata\b', 'Emiliano Zapata')
rule(r'\bjuárez\b|\bjuarez\b', 'Benito Juárez')
rule(r'\bcort[eé]s\b.*hern[aá]n|\bhern[aá]n cort[eé]s', 'Hernán Cortés')
rule(r'\bsherlock\b|\bholmes\b.*(?:sherlock|conan)', 'Sherlock Holmes')
rule(r'\btristan\b.*\b(?:ise[u]lt|yse[u]lt)|\btristan\b.*legend', 'Tristan & Iseult')
rule(r'\barthur(?:ian)?\b|\bchrétien\b|\blancelot\b|\bgrail\b|\bcamelot\b|\bcycle d\'arthur|\bcycles d\'arthur', 'King Arthur')

# ─── ADDITIONAL BROAD MATCHES ───

# Broad "literature" catches
rule(r'^Literature$|^Littérature$|^Literatur$|^Literatura$|^letterkunde$', 'Literary Criticism')
rule(r'\bliteratura\b.*\bcolecci|\bliterature\b.*\bcollection|\bliterary collection', 'Anthology')
rule(r'\bconference\b|\bcongress\b|\bsymposium|\bcongreso\b|\bcoloquio', 'Anthology')
rule(r'\breaders?\b.*\bpublicat|\btextbook|\blibro de texto|\bmanual\b', 'Education')

# Broad "travel"
rule(r'^Travel$|\bvoyage[s]?\b|\bviaje[s]?\b', 'Travel Writing')
rule(r'\bexplorer|\bexploraci[oó]n|\bdescription.*travel', 'Travel Writing')

# "Art" / "Artists" / visual arts
rule(r'^Art$|^art[s]?\b.*\bvisual|\barte\b.*\bvisual|\bbeaux.?arts|\bbellas artes', 'Visual Art')
rule(r'\bartist[s]?\b|\bartista[s]?\b', 'Visual Art')
rule(r'\bphotograph|\bfotograf', 'Photography')
rule(r'\billustrat|\bilustraci', 'Visual Art')

# Women / gender
rule(r'\bwomen\b|\bmujer|\bfemme[s]?\b|\bweiblich', ['Feminism', 'Gender Studies'])
rule(r'\bman.?woman\b|\brelaciones.*hombre|\brelations.*homme', 'Love & Desire')

# Spiritual / religious life
rule(r'\bspiritual\b|\bespiritual|\bvie spirituelle|\bvida espiritual', 'Religion')
rule(r'\byoga\b|\bmeditat', 'Buddhism')
rule(r'\bmonk|\bmonja|\bnun\b|\bconvent\b|\bmonaster', 'Religion')
rule(r'\bclergy\b|\bpriest|\bsacerdot|\bbishop|\bobispo', 'Catholicism')

# Man-woman / relationships
rule(r'\brelationship[s]?\b|\brelaciones\b', 'Love & Desire')

# Intellectual life / cultural
rule(r'\bintellectual life\b|\bvida intelectual|\bvie intellectuelle', 'Modern History')
rule(r'\bcultur[ae]?\b(?!.*\b(?:gay|homosex|queer))', 'Modern History')

# Languages as subjects (for language learning/study books)
rule(r'^(?:German|French|English|Italian|Portuguese|Spanish|Latin|Greek|Arabic|Japanese|Chinese|Russian) language\b', 'Grammar & Linguistics')
rule(r'\blangue\b.*\bfranç|\blengua\b.*\bespaño', 'Grammar & Linguistics')
rule(r'\bcomposition and exercises\b|\bgrammaire\b', 'Grammar & Linguistics')
rule(r'\blanguage.*study|\benseñanza.*lengua', 'Grammar & Linguistics')

# Authors as subjects (when nationality given)
rule(r'\bauthors,\s*(?:mexican|french|spanish|american|argentine|brazilian|cuban|colombian|peruvian|chilean)', 'Literary Criticism')
rule(r'\b[eé]crivain|\bescritor', 'Literary Criticism')
rule(r'\bpoets?\b.*(?:mexican|french|spanish|american)|\bpoeta[s]?\b', 'Poetry')

# Tales / stories
rule(r'^Tales$|\bconte[s]?\b(?!mpor)', 'Short Stories')

# Sex
rule(r'^Sex$|\bsex\b(?!ual)', 'Sexuality & Eroticism')

# Conduct of life / moral
rule(r'\bconduct of life\b|\bmorale pratique\b', 'Ethics')

# Private investigators / detective
rule(r'\bprivate investigat|\bdetective[s]?\b', 'Detective & Mystery')

# Actors / acting
rule(r'\bactor[s]?\b|\bactress|\bactrice|\bacting\b', 'Film & Cinema')

# Authorship / writing craft
rule(r'\bauthorship\b|\bwriting\b.*\b(?:technique|craft|creative)|\bescritura\b.*creativ', 'Literary Criticism')

# Books and reading
rule(r'\bbooks and reading\b|\blibros y lectura|\blivres et lecture', 'Literary Criticism')

# Exhibition catalogs
rule(r'\bexhibition\b|\bexposici[oó]n', 'Museums & Collections')

# Depression / mental health
rule(r'\bdepression\b|\bdépression\b|\banxiety\b|\bansiedad', 'Madness & Mental Illness')

# Europe as place
rule(r'^Europe$|\beurope\b', 'France')  # approximate — most European refs are France

# Popular works / general audience
rule(r'\bpopular works\b|\bouvrages de vulgarisation', 'Science')

# Manners and customs / social life
rule(r'\bmanners and customs\b|\bm[oœ]urs et coutumes\b|\bcostumbres\b', 'Modern History')
rule(r'\bsocial life\b|\bsocial conditions\b|\bconditions sociales\b', 'Modern History')
rule(r'\bcivilizat|\bcivilis', 'Modern History')

# Screenplays (lowercase)
rule(r'^screenplays$', 'Screenplay')

# Essais (French)
rule(r'\bessais\b', 'Essay')

# Lateinamerika (German)
rule(r'\blateinamerika\b', 'Latin America')
rule(r'\bspanische literatur\b|\bspanischamerikanische\b', 'Latin American Literature')

# Filmographies
rule(r'\bfilmograph', 'Film & Cinema')

# Diaries
rule(r'\bdiaries\b|\bjournal[s]?\b.*(?:personnel|intime)', 'Diary & Letters')

# Pictorial works
rule(r'\bpictorial\b|\billustrated\b|\bilustrad', 'Visual Art')

# Additional catches for remaining unmapped
rule(r'\biseult\b|\bisolde\b|\biseut\b', 'Tristan & Iseult')
rule(r'\bliterature,?\s*modern\b', 'Literary History')
rule(r'\bmap[s]?\b|\batlas\b|\bcartograph', 'Visual Art')
rule(r'\bportrait[s]?\b|\bretrato', 'Visual Art')
rule(r'\bchristian life\b|\bvida cristiana\b|\bvie chr[eé]tienne\b', 'Catholicism')
rule(r'\byi jing\b|\bi ching\b|\btao|\bdaoism|\bconfuci', 'Religion')
rule(r'\balgeria\b|\bargelia\b|\balgérie\b|\btunisia\b|\bmorocco\b|\bmarruecos\b', 'North Africa')
rule(r'\bgays\b(?!\s+in\s+motion)', 'Gay Literature')
rule(r'\bgeschichte\b', 'Modern History')
rule(r'\bliterature and society\b|\bliteratura y sociedad\b|\blittérature et société', 'Literary Criticism')
rule(r'\bliteratura [aá]rabe\b', 'Arabic Literature')
rule(r'\bmurder\b|\bassassin|\bhomicid', 'Detective & Mystery')
rule(r'\bm[eé]ditat', 'Buddhism')
rule(r'\bpsychanalyse\b', 'Psychoanalysis')
rule(r'\bpsychiatr', 'Medicine & Health')
rule(r'\bpsycholog', 'Psychoanalysis')
rule(r'\bromance\b', 'Fiction')
rule(r'\bself.?actual|\bself.?help|\bautoayuda', 'Philosophy')
rule(r'\bsouthern states\b', 'United States')
rule(r'\bfriendship\b|\bamistad\b|\bamitié', 'Love & Desire')
rule(r'\bcity and town\b', 'Urban Life')
rule(r'\binternational relat|\brelaciones internacionales', 'Latin American Politics')
rule(r'\bart d\'[eé]crire\b|\bwriting\b|\bécriture\b', 'Literary Criticism')
rule(r'\bauthors?,\s*(?:english|german|italian|russian|japanese)', 'Literary Criticism')
rule(r'\bafrican american[s]?\b|\bnegro|\bblack\b.*(?:america|culture)', 'Race & Ethnicity')
rule(r'\bafrica\b(?!n american)', 'Latin America')  # approximate for small set
rule(r'\barab\b', 'Middle East')
rule(r'\barte\b(?!\s*poética)', 'Visual Art')
rule(r'\bmexican art\b|\bart mexicain\b|\barte mexicano', 'Visual Art')
rule(r'\bwidow|\bviuda|\bsoledad|\bloneliness', 'Love & Desire')
rule(r'\bidentit[yé]|\bidentidad\b', 'National Identity')
rule(r'\bnovo,?\s*salvador', 'Gay Literature')  # Mexican queer writers
rule(r'\bisherwood', 'Gay Literature')
rule(r'\bwilde,?\s*oscar|\boscar\s*wilde', 'Oscar Wilde')
rule(r'\bandré gide\b|\bgide,?\s*andr', 'Gay Literature')
rule(r'\bpaz,?\s*octavio|\boctavio\s*paz', 'Octavio Paz')

# ─── ADDITIONAL RULES (ROUND 3) ───

# More junk patterns are added to JUNK_PATTERNS above;
# here we catch remaining ones via rules that map to []
# (handled below in EXTRA_JUNK)

# --- More literary forms ---
rule(r'\badventure\b', 'Fiction')
rule(r'\bildungsroman', 'Fiction')
rule(r'\bghost stor', 'Horror & Gothic')
rule(r'\bsea stor', 'Fiction')
rule(r'\bpicaresque\b|\bpicaresca\b', 'Fiction')
rule(r'\bmelodrama\b', 'Drama')
rule(r'\bfantasy\b|\bfantasía\b|\bfantastique\b', 'Fiction')
rule(r'\bnonfiction\b', 'Essay')
rule(r'\bcollected works\b|\boeuvres complètes|\bobras completas', 'Anthology')
rule(r'\bprose\b(?! po)', 'Literary Criticism')
rule(r'\bmonologu', 'Drama')
rule(r'\bstories in rhyme\b', 'Poetry')
rule(r'\ballgor|\balegoria|\ballégorie', 'Fiction')
rule(r'\blimericks?\b', 'Poetry')
rule(r'\bfabliaux?\b|\bfablel\b', 'Short Stories')
rule(r'\bmaxim[es]?\b|\bmáxima[s]?\b', 'Aphorism')
rule(r'\bproverb[es]?\b|\bproverbio[s]?\b|\brefr[aá]n', 'Aphorism')
rule(r'\bdevotional\b|\bpiadosa\b|\bdévotion', 'Religion')
rule(r'\bnarrati[ov]|\bnarración\b|\bnarration\b', 'Literary Criticism')
rule(r'\bliterary theory\b|\bteoría literaria|\bteoria literária|\bliteraturtheorie|\btheorie\b', 'Literary Criticism')
rule(r'\bliterary style\b|\bestilo literario|\bstyle littéraire', 'Literary Criticism')
rule(r'\bliterary,?\s*artistic\b|\bcreation.*littéraire|\bcreación.*literari|\bcreación.*estétic|\baptitud creadora', 'Literary Criticism')
rule(r'\bpoint of view\b|\bpoint de vue\b', 'Literary Criticism')
rule(r'\bgenres?\s*litt[eé]rair', 'Literary Criticism')
rule(r'\bcomparative literature\b|\blittérature comparée|\bliteratura comparada', 'Literary Criticism')
rule(r'\bliteratura.*apreci|\bliterature.*appreci|\blittérature.*appréci', 'Literary Criticism')
rule(r'\banalisis?\s*(del\s*)?discurso|\banalisis?\s*literar|\bcritica\s*literar', 'Literary Criticism')
rule(r'\binfluence?\b.*\b(litt|literar|artist)', 'Literary Criticism')
rule(r'\bstudii critice\b|\bcritica\b', 'Literary Criticism')

# --- Autobiography/Biography in other languages ---
rule(r'\bautobiograf[ií]|\bautobiografie\b', 'Autobiography & Memoir')
rule(r'\bbiograf[ií]|\bbiografie\b|\bbiografii\b', 'Biography')
rule(r'\bpersonal narrativ', 'Autobiography & Memoir')
rule(r'\berlebnisbericht\b', 'Autobiography & Memoir')

# --- Religion & Spirituality ---
rule(r'\bbible\b|\bbiblia\b|\bbibel\b|\bgospel[s]?\b|\bevangelio[s]?\b', 'Religion')
rule(r'\bdios\b|\bgod\b(?! of)|\bdieu\b', 'Religion')
rule(r'\bfaith\b|\bfoi\b|\bfe\b', 'Religion')
rule(r'\bprayer[s]?\b|\boración\b|\bprière\b|\bprier\b', 'Religion')
rule(r'\bheaven\b|\bhell\b|\binfierno\b|\bpurgator[iy]|\bvida futura|\bfuture life|\bvie future', 'Religion')
rule(r'\bcristi[aá]n|\bchristendom', 'Catholicism')
rule(r'\bfranciscan|\bbenedictin|\bmonasteri|\bmonach', 'Catholicism')
rule(r'\btheosophy\b|\bteosofía\b|\bthéosophie\b', 'Occult & Esoteric')
rule(r'\btantr[ia]|\bvedanta\b|\bvedānta\b|\bāyurveda\b|\bpranayama\b|\bprānāyāma\b|\byoga\b', 'Religion')
rule(r'\bsatani[sc]|\bdemonomani|\bdémonoman', 'Occult & Esoteric')
rule(r'\bwitch|sorcell|sorcièr|bruj[ae]', 'Occult & Esoteric')
rule(r'\bdivination\b|\badivinación\b', 'Occult & Esoteric')
rule(r'\bastrol[oó]g', 'Occult & Esoteric')
rule(r'\bfeng\s*shui\b', 'Occult & Esoteric')
rule(r'\bcrusad|\bcroisad', 'Medieval History')
rule(r'\bpilgrim', 'Religion')

# --- History periods ---
rule(r'\benlightenment\b|\bsiècle des lumières|\bilustración', 'Modern History')
rule(r'\brenaissance\b|\brenacimiento\b', 'Modern History')
rule(r'\bfeudali[sm]|\bféodalit', 'Medieval History')
rule(r'\bknight[s]?\b|\bchevalier|\bcaball', 'Medieval History')
rule(r'\bnobilit|\bnobleza|\baristocra', 'Modern History')
rule(r'\bempero[r]?\b|\bemperado|\bempereur', 'Modern History')
rule(r'\bking[s]?\b.*\bruler|\brois?\b.*\bsouverain|\brey[es]?\b.*\bgobiern', 'Modern History')
rule(r'\bmonarch[iy]|\bmonarquía', 'Modern History')
rule(r'\bcaudillo', 'Latin American Politics')
rule(r'\bdisappeared person|\bdesaparecido', 'Human Rights')

# --- More geography ---
rule(r'\bnicaragua\b', 'Latin America')
rule(r'\bcosta ric', 'Latin America')
rule(r'\bparaguay\b', 'Latin America')
rule(r'\bdomini[ck]an\b', 'Caribbean')
rule(r'\bphilippine[s]?\b|\bfilipina', 'Japan')  # approximate — SE Asia
rule(r'\bpolynesia\b|\bislands?\b', 'Travel Writing')
rule(r'\bcalifornia\b|\btexas\b|\bnebraska\b|\bhollywood\b', 'United States')
rule(r'\bsan francisco\b|\blos angeles\b', 'United States')
rule(r'\bsoviet union\b|\bsoviet\b', 'Russia')
rule(r'\biraq\b|\bsaudi\b|\barabian\b|\bwahhāb', 'Middle East')
rule(r'\bkenya\b|\bcongo\b', 'Latin America')  # Africa catch-all using existing broad cat
rule(r'\baustralia\b', 'United Kingdom')  # approximate
rule(r'\bswitzerland\b|\bschweiz\b|\bsuisse\b', 'France')  # approximate
rule(r'\bandes\b', 'Latin America')
rule(r'\bjerusal[eé]n\b|\bjerusalem\b', 'Middle East')
rule(r'\bflorenc[ei]\b|\bfirenze\b', 'Italy')
rule(r'\bbelize\b', 'Latin America')
rule(r'\bgaucho[s]?\b', 'Argentina')
rule(r'\bpopol\s*vuh\b', 'Pre-Columbian')
rule(r'\bmayas?\b(?!\s*angel)', 'Indigenous Peoples')
rule(r'\bquich[eé]\b', 'Indigenous Peoples')
rule(r'\bhispanoameric|\bhispano.americ', 'Latin American Literature')
rule(r'\bconto\b.*\bhispano|\bconto\b.*\bbrasileir', 'Latin American Literature')

# --- More national literatures ---
rule(r'\bguatemalan lit|\bliteratura guatemalteca|\blittérature guatémaltèque', 'Latin American Literature')
rule(r'\bcosta rican lit|\bliteratura costarricense|\blittérature costaricienne', 'Latin American Literature')
rule(r'\baustrian lit|\bliteratura austriaca', 'German Literature')
rule(r'\bportuguese lit|\bliteratura portuguesa', 'Spanish Literature')  # approximate
rule(r'\bchinese lit|\bliteratura china|\blittérature chinoise', 'Japanese Literature')  # approximate — Asian lit
rule(r'\bgreek lit|\bliteratura griega|\blittérature grecque', 'Classical Literature')
rule(r'\blatin lit|\bliteratura latina|\bpoesia latina', 'Classical Literature')
rule(r'\bold norse\b', 'Medieval Literature')
rule(r'\bpolish\b.*\blit|\bliteratura polaca|\bnovelistis polacos', 'Russian Literature')  # approximate — Eastern European
rule(r'\bnazi lit', 'German Literature')
rule(r'\barabic\b.*\b(prose|lit|folk)\b', 'Middle East')
rule(r'\bfranse\b.*\b(lett|fik)', 'French Literature')
rule(r'\bspaanse\b.*\blett', 'Spanish Literature')
rule(r'\bletterat.*\bitalian', 'Italian Literature')
rule(r'\bnarrati.*\bingles', 'English Literature')
rule(r'\bpoes[ií]a\b.*\b(español|griega|inglesa|irland|lírica|popular|amorosa)', 'Poetry')
rule(r'\bficci[oó]n\b.*\bamerican|\bficção\b.*\bamerican', 'American Literature')
rule(r'\bliteratura\b.*\b(african|norte.americ|expressao|brasileñ)', 'Latin American Literature')
rule(r'\blittérature\b.*\b(ancienne|cubaine|érotique)', 'Literary Criticism')
rule(r'\bliteratura belga\b', 'French Literature')

# --- Arts ---
rule(r'^Arts$|\barts\b.*\b(20e|21e|modern|mexicain)', 'Visual Art')
rule(r'\bnude\b|\bnu\b(?!\b[a-z])|\bnudes?\s*\(', 'Visual Art')
rule(r'\bfolk art\b', 'Visual Art')
rule(r'\bperforming arts?\b|\bartes escénic', 'Drama')
rule(r'\bsinger[s]?\b|\bmusician[s]?\b|\bcompositor', 'Music')
rule(r'\bentertainer[s]?\b', 'Film & Cinema')
rule(r'\bscreenwriter', 'Screenplay')
rule(r'\bbroadcast|\btelevisi|\bradio\b', 'Film & Cinema')
rule(r'\banimation\b|\banimationsfilm\b|\bcomputeranimation|\bcomputerfilm', 'Film & Cinema')
rule(r'\bdrawing\b|\bdessin\b|\btekeningen\b', 'Visual Art')
rule(r'\blettering\b|\brotulación|\bletreros|\btipo[s]?\s*\(imprent|\bletras\s*ornamental', 'Visual Art')
rule(r'\bsign[s]?\b|\bsignes\b', 'Visual Art')
rule(r'\bworks of art\b|\bkunst\b|\bkunstenaars\b|\bkunstmusea\b', 'Visual Art')
rule(r'\bcathedral[s]?\b|\bstructures?\s*\(single', 'Architecture')
rule(r'\bartes\b.*\b(gra[fp]|marcial)', 'Visual Art')

# --- Medicine & Health ---
rule(r'\bdiet\b|\bdieta[s]?\b|\bdiétothérap|\bterapéutica dietét|\blow.fat', 'Medicine & Health')
rule(r'\bnaturopath|\bnaturismo|\bnaturop[aá]t', 'Medicine & Health')
rule(r'\bhomeopath|\bhoméopath', 'Medicine & Health')
rule(r'\bherb[s]?\b.*\btherap|\bherbe[s]?\b.*\bthérap|\bflore[s]?\b.*\bterap', 'Medicine & Health')
rule(r'\bvitamin', 'Medicine & Health')
rule(r'\bacupunctur|\bacupuntur', 'Medicine & Health')
rule(r'\bhealing\b|\bcuración\b|\bguérison\b', 'Medicine & Health')
rule(r'\brelaxat|\brelajación', 'Medicine & Health')
rule(r'\bstress\b.*\bmanag|\bgestion\b.*\bstress|\btensión\b.*\bmanejo', 'Medicine & Health')
rule(r'\bmental\b.*\bheal|\bsanté\b.*\bmental|\bhigiene\b.*\bmental', 'Medicine & Health')
rule(r'\bneuroses?\b|\bnévroses?\b', 'Medicine & Health')
rule(r'\bbipolar\b', 'Medicine & Health')
rule(r'\besquizofreni|\bschizophren', 'Madness & Mental Illness')
rule(r'\bpsychothera|\bpsicoterap', 'Psychoanalysis')
rule(r'\blogothera|\blogoterap', 'Psychoanalysis')
rule(r'\baddiction\b|\badicci[oó]n', 'Medicine & Health')
rule(r'\bsyphilis\b|\bsífilis', 'Medicine & Health')
rule(r'\bblind\b|\bdeaf\b|\bdisabilit', 'Medicine & Health')
rule(r'\basperger', 'Medicine & Health')

# --- Psychology/Philosophy ---
rule(r'\bmelanchol|\bmélancolie|\bmelancolía', 'Madness & Mental Illness')
rule(r'\bsuicid|\bsuizid|\bzelfmoord', 'Death & Mourning')
rule(r'\bpleasure\b|\bplaisir\b|\bplacer\b|\bhedon', 'Philosophy')
rule(r'\bsilence\b', 'Philosophy')
rule(r'\bself.?esteem|\bestime de soi|\bself.?accept|\bacceptation de soi|\bself.?percept', 'Philosophy')
rule(r'\bself.?realiz|\bréalisation de soi|\bautorealización|\bdesarrollo de sí|\bactualización de sí', 'Philosophy')
rule(r'\bconscious|\binconscient|\bsubcon[sc]i|\baware', 'Psychoanalysis')
rule(r'\bpersonal[iy]t|\bpersonnalité', 'Psychoanalysis')
rule(r'\bego\b|\bid\b(?! )|bsuperego|\bmoi\b', 'Psychoanalysis')
rule(r'\bcognition\b', 'Philosophy')
rule(r'\bcommunicat|\bcomunicaci[oó]n|\bcommunicació', 'Grammar & Linguistics')
rule(r'\brhetoric|\brhétorique|\bretòrica', 'Rhetoric')
rule(r'\bpersuasi[oó]|\bpersuasion', 'Rhetoric')
rule(r'\bsemiòtica\b|\bsemiologia', 'Structuralism & Poststructuralism')
rule(r'\bestoicism|\bestoicismo', 'Philosophy')
rule(r'\blogic|\blógica', 'Philosophy')
rule(r'\bstatic?tics?\b|\bestad[ií]stic', 'Science')
rule(r'\bevol[uú]ci[oó]n', 'Science')
rule(r'\bdarwin\b', 'Science')
rule(r'\beinstein\b', 'Science')
rule(r'\bcurie\b', 'Science')

# --- Daily life / society ---
rule(r'\bcook\b|\bcookbook|\brecipe[s]?\b|\breceta[s]?\b|\bsukaldaritz|\bsauce[s]?\b', 'Food & Gastronomy')
rule(r'\btea\b|\bté\b|\bcoffee\b|\bbeverage|\bbebida', 'Food & Gastronomy')
rule(r'\bcrime\b|\bcriminal[s]?\b|\bpolice\b|\bswindl', 'Detective & Mystery')
rule(r'\bcountercultur|\bsubcultur', 'Urban Life')
rule(r'\bcountry life\b', 'Rural Life')
rule(r'\bbrother[s]?\b|\bhermano|\bsibling', 'Family')
rule(r'\byoung\b.*\b(men|adult|women)|\bjuventud', "Children's Literature")
rule(r'\bold age\b|\baging\b|\bviejez|\bâgée', 'Family')
rule(r'\btriangle[s]?\b.*\brelat|\bparamour[s]?\b', 'Love & Desire')
rule(r'\bdespair\b|\bgrief\b|\bsuffering\b|\bchagrin\b|\bsufrimiento|\bconsuelo|\bconsolat', 'Death & Mourning')
rule(r'\bfear\b|\bmiedo\b', 'Psychoanalysis')
rule(r'\bhappiness\b|\bfelicidad\b|\bzoriona\b', 'Philosophy')
rule(r'\bhumor|\bchiste[s]?\b|\bamusement\b', 'Satire & Humor')

# --- German language catches ---
rule(r'\bkurzgeschichte\b', 'Short Stories')
rule(r'\blyrik\b', 'Poetry')
rule(r'\bepik\b|\bepen\b|\bheldenepos\b|\bhöfisches epos', 'Epic')
rule(r'\bdichtkunst\b|\bgedichten\b|\bpoezi[ae]\b', 'Poetry')
rule(r'\btoneel\b|\bcomèdia\b', 'Drama')
rule(r'\bfict[ie]\b', 'Fiction')
rule(r'\bromankunst\b|\bromancier\b', 'Fiction')
rule(r'\bbildband\b', 'Visual Art')
rule(r'\bsprache\b|\blangage\b|\blangues?\b|\blanguage\b|\blengua\b(?!\s*(franc|ingles|español))', 'Grammar & Linguistics')
rule(r'\bgrammatik\b|\bgrammaire\b|\bsyntaxis?\b|\bsatzbauplan\b', 'Grammar & Linguistics')
rule(r'\bwörterbuch\b|\bvocabul[ao]|\bglossari', 'Dictionary')
rule(r'\bphilolog', 'Grammar & Linguistics')
rule(r'\bgesellschaft\b|\bmaatschappij\b|\bsoziologie\b|\bsociologie', 'Modern History')
rule(r'\bkultur\b|\bcultuur\b|\bvolkskunde\b|\bkulturanthropolog|\bkulturerbe', 'Modern History')
rule(r'\bpolitik\b', 'Latin American Politics')
rule(r'\barbeit\b', 'Economics')
rule(r'\bliebe\b|\bhoofse liefde\b', 'Love & Desire')
rule(r'\btod\b|\bdood\b', 'Death & Mourning')
rule(r'\bmystiek\b|\bmysterigodsdiensten', 'Mysticism')
rule(r'\bseksualiteit\b', 'Sexuality & Eroticism')
rule(r'\bhomoseksualiteit\b|\bhomoseksuelen\b|\bhomossexualismo', 'Gay Literature')
rule(r'\bmiddeleeuwen\b', 'Medieval History')
rule(r'\bantike\b', 'Ancient History')
rule(r'\bschriftlichkeit\b|\becriture\b|\bescritura\b', 'Literary Criticism')
rule(r'\bfragmenten\b|\btekstuitgave\b', 'Anthology')
rule(r'\blateinamerika\b|\bhispanoamerika\b|\bamerika\b(?!n)', 'Latin America')
rule(r'\bbrasilien\b', 'Brazil')
rule(r'\bkuba\b', 'Cuba')
rule(r'\beuropa\b|\beuropeans?\b|\ballemands?\b|\bgermans?\b|\bbritish\b|\blebanese\b|\bbedouins?\b', 'Modern History')
rule(r'\bschule\b', 'Education')
rule(r'\bschauspielerin\b', 'Film & Cinema')
rule(r'\btheaterkritik\b', 'Drama')
rule(r'\baufführung\b', 'Drama')
rule(r'\bdrehbuch\b', 'Screenplay')
rule(r'\bfilmkunst\b', 'Film & Cinema')

# --- Named subjects (more authors/artists/directors) ---
rule(r'\bfellini\b', 'Film & Cinema')
rule(r'\bhitchcock\b', 'Film & Cinema')
rule(r'\bwelles\b.*\borson|\borson\b.*\bwelles', 'Film & Cinema')
rule(r'\bhuston\b.*\bjohn|\bjohn\b.*\bhuston', 'Film & Cinema')
rule(r'\beisenstein\b', 'Film & Cinema')
rule(r'\bcoppola\b', 'Film & Cinema')
rule(r'\begoyan\b', 'Film & Cinema')
rule(r'\btykwer\b', 'Film & Cinema')
rule(r'\bhawks\b.*\bhoward|\bhoward\b.*\bhawks', 'Film & Cinema')
rule(r'\bminnelli\b', 'Film & Cinema')
rule(r'\bruiz,?\s*raúl', 'Film & Cinema')
rule(r'\bwaters,?\s*john', 'Film & Cinema')
rule(r'\bisaac,?\s*alberto', 'Film & Cinema')
rule(r'\bbracho\b', 'Film & Cinema')
rule(r'\bpalma,?\s*andrea', 'Film & Cinema')
rule(r'\bheston\b', 'Film & Cinema')
rule(r'\bmastroianni\b', 'Film & Cinema')
rule(r'\bdeneuve\b', 'Film & Cinema')
rule(r'\bwarhol\b', 'Visual Art')
rule(r'\bklim[t]\b', 'Visual Art')
rule(r'\bschiele\b', 'Visual Art')
rule(r'\bdelacroix\b', 'Visual Art')
rule(r'\bbotticelli\b', 'Visual Art')
rule(r'\bbellini\b.*\bgiovanni', 'Visual Art')
rule(r'\bcorreggio\b', 'Visual Art')
rule(r'\braphael\b.*\b1483', 'Visual Art')
rule(r'\bcorot\b', 'Visual Art')
rule(r'\bgainsborough\b', 'Visual Art')
rule(r'\bholbein\b', 'Visual Art')
rule(r'\bwhistler\b', 'Visual Art')
rule(r'\bvelázquez\b|\bvel[aá]zquez\b', 'Visual Art')
rule(r'\bthorvaldsen\b', 'Visual Art')
rule(r'\bleonardo\b.*\bvinci', 'Visual Art')
rule(r'\bvillalpando\b', 'Visual Art')
rule(r'\bmichel,?\s*alfonso', 'Visual Art')
rule(r'\bruiz,?\s*antonio', 'Visual Art')
rule(r'\bgarcía,?\s*héctor', 'Photography')
rule(r'\bálvarez bravo\b|\balvarez bravo\b', 'Photography')
rule(r'\bdante\b|\balighieri\b', 'Poetry')
rule(r'\bhomer[o]?\b(?!sexual)', 'Poetry')
rule(r'\bcatullus\b', 'Poetry')
rule(r'\bverlaine\b', 'Poetry')
rule(r'\bbaudelaire\b', 'Poetry')
rule(r'\bnerval\b', 'Poetry')
rule(r'\bpellicer\b.*\bcarlos', 'Poetry')
rule(r'\bnandino\b', 'Poetry')
rule(r'\bvillaurrutia\b', 'Poetry')
rule(r'\bcavaf[iy]s\b', 'Poetry')
rule(r'\brilke\b', 'Poetry')
rule(r'\bauden\b', 'Poetry')
rule(r'\bgil de biedma\b', 'Poetry')
rule(r'\bpardo garc[ií]a\b', 'Poetry')
rule(r'\bplath\b', 'Poetry')
rule(r'\bspender\b', 'Poetry')
rule(r'\bponiatowska\b', 'Mexican Literature')
rule(r'\bcastellanos,?\s*rosario\b', 'Mexican Literature')
rule(r'\bglantz\b', 'Mexican Literature')
rule(r'\brevueltas\b.*\bjosé', 'Mexican Literature')
rule(r'\bpitol\b', 'Mexican Literature')
rule(r'\bblanco,?\s*josé\s*joaqu', 'Mexican Literature')
rule(r'\bgonzález obregón\b', 'Mexican Literature')
rule(r'\bgaleana,?\s*benita', 'Mexican Literature')
rule(r'\bgaribay,?\s*ricardo', 'Mexican Literature')
rule(r'\bsanta anna\b.*\bantonio', 'Mexican Revolution')
rule(r'\bmorelos\b.*\bjosé', 'Mexican Revolution')
rule(r'\bcarranza\b.*\bvenustian', 'Mexican Revolution')
rule(r'\bcarrillo puerto\b', 'Mexican Revolution')
rule(r'\breed,?\s*alma', 'Mexican Revolution')
rule(r'\bnezahualcóyotl\b', 'Pre-Columbian')
rule(r'\bsor juana\b', 'Mexican Literature')
rule(r'\bflaubert\b', 'French Literature')
rule(r'\bchateaubriand\b', 'French Literature')
rule(r'\bdaudet\b', 'French Literature')
rule(r'\bdiderot\b', 'French Literature')
rule(r'\bleiris\b', 'French Literature')
rule(r'\bjouhandeau\b', 'French Literature')
rule(r'\bgreen,?\s*julien', 'French Literature')
rule(r'\btournier\b', 'French Literature')
rule(r'\bcollard\b.*\bcyril', 'French Literature')
rule(r'\bsarner\b', 'French Literature')
rule(r'\bmouquet\b', 'French Literature')
rule(r'\bmiller,?\s*henry', 'American Literature')
rule(r'\bcapote\b.*\btruman|\btruman\b.*\bcapote', 'American Literature')
rule(r'\bmailer\b.*\bnorman', 'American Literature')
rule(r'\bhellman\b.*\blillian', 'American Literature')
rule(r'\bgriffin,?\s*john\s*howard', 'American Literature')
rule(r'\bsterne\b.*\blaurence', 'English Literature')
rule(r'\brichardson,?\s*samuel', 'English Literature')
rule(r'\bchatwin\b', 'English Literature')
rule(r'\bdurrell\b', 'English Literature')
rule(r'\bnicols[oa]n\b.*\bharold', 'English Literature')
rule(r'\bsackville.west\b', 'English Literature')
rule(r'\btrefusis\b', 'English Literature')
rule(r'\brolfe,?\s*frederick', 'English Literature')
rule(r'\bo\'brien,?\s*flann', 'Irish Literature')
rule(r'\bjoyce,?\s*james', 'Irish Literature')
rule(r'\bdostoyevsk|\bdostoïevski', 'Russian Literature')
rule(r'\btolstoy\b', 'Russian Literature')
rule(r'\bcanetti\b', 'German Literature')
rule(r'\bmann,?\s*(klaus|thomas)\b', 'German Literature')
rule(r'\bbernhard,?\s*thomas', 'German Literature')
rule(r'\bkafka\b', 'German Literature')
rule(r'\bkawabata\b', 'Japanese Literature')
rule(r'\blowry,?\s*malcolm', 'English Literature')
rule(r'\bdinesen\b', 'English Literature')  # Danish but known in English lit
rule(r'\bbioy casares\b', 'Argentine Literature')
rule(r'\bcardoza y aragón\b', 'Latin American Literature')
rule(r'\bhernández,?\s*felisberto', 'Latin American Literature')
rule(r'\bskármeta\b', 'Chilean Literature')
rule(r'\bmachado de assis\b', 'Brazilian Literature')
rule(r'\bsodré\b', 'Brazilian Literature')
rule(r'\bgabeira\b', 'Brazilian Literature')
rule(r'\bmontejo,?\s*esteban', 'Cuban Literature')
rule(r'\bo\'neill\b.*\beugene|\beugene\b.*\bo\'neill', 'Drama')
rule(r'\bshakespeare\b', 'Drama')
rule(r'\bartaud\b', 'Drama')
rule(r'\bwagner\b', 'Opera')
rule(r'\bberlioz\b', 'Music')
rule(r'\bcellini\b.*\bbenvenuto', 'Autobiography & Memoir')
rule(r'\byourcenar\b', 'French Literature')
rule(r'\bgibran\b|\bkhalil\b.*\bgibran', 'Poetry')
rule(r'\bkrishnamurti\b', 'Philosophy')
rule(r'\bmcluhan\b', 'Literary Criticism')
rule(r'\bkerouac\b', 'Beat Generation')
rule(r'\bburroughs\b.*\bwilliam', 'Beat Generation')
rule(r'\bbowles\b.*\bpaul', 'American Literature')
rule(r'\bauster\b.*\bpaul', 'American Literature')
rule(r'\blaughlin\b.*\bjames', 'American Literature')

# --- Catch-all for "Authors, [nationality]" and "Autores [nationality]" ---
rule(r'\bauthors?,?\s*(uruguayan|belgian|danish|guatemalan|austrian)', 'Literary Criticism')
rule(r'\bautores\b.*\b(mexican|franc[eéê]s|español|polacos|alemanes|estadounidenses|norteamerican)', 'Literary Criticism')
rule(r'\bnovelists?,?\s*(french|german|polish)', 'Literary Criticism')
rule(r'\bfilósofos?\b', 'Philosophy')
rule(r'\bphysicist[s]?\b', 'Science')
rule(r'\bphysician[s]?\b|\bmédecin', 'Medicine & Health')
rule(r'\blawyer[s]?\b|\bdiplomats?\b|\bstatesm[ae]n\b|\bpresident[s]?\b|\bgenerals?\b', 'Modern History')

# --- Misc remaining ---
rule(r'\bnight\b(?! of)', 'Poetry')  # "Night" as subject usually poetic
rule(r'\btime\b(?! of)|\btiempo\b', 'Philosophy')
rule(r'\bchance\b|\bhasard\b', 'Philosophy')
rule(r'\bdystopia[s]?\b|\butopia\b', 'Philosophy')
rule(r'\bcharacter\b', 'Fiction')
rule(r'\bcat[s]?\b(?! [a-z])', 'Animals')
rule(r'\bwhale[s]?\b|\bwhaling\b', 'Animals')
rule(r'\bhurricane[s]?\b|\bearthquake[s]?\b', 'Nature & Environment')
rule(r'\barchives?\b|\bmanuscript[s]?\b|\bfacsimile[s]?\b', 'Bibliography')
rule(r'\bsmall press|\bcartonera\b|\bbook\s*art|\bpublish', 'Bibliography')
rule(r'\bcomptoir|\bseasonide|\bhotel[s]?\b|\bcruise\b|\broads?\b', 'Travel Writing')
rule(r'\binformation\b|\blearning\b', 'Education')
rule(r'\bintercultural\b|\binterkulturalität\b', 'Modern History')
rule(r'\bqueerlit\b', 'Queer Studies')
rule(r'\bsexo\b|\bsexual intercourse\b|\bvie sexuelle|\bparaphilia|\bmasturbat', 'Sexuality & Eroticism')
rule(r'\bmachismo\b', 'Masculinity')
rule(r'\bcross.dress', 'Transgender Studies')
rule(r'\bintersexualit', 'Transgender Studies')
rule(r'\bsex work|\bprostitut', 'Sexuality & Eroticism')
rule(r'\bhuman cloning\b', 'Science')
rule(r'\billegal arms\b', 'War & Conflict')
rule(r'\banti.?clerical', 'Catholicism')
rule(r'\bcorpus christi\b|\bfestival[s]?\b|\banniversar|\bcelebrat', 'Modern History')
rule(r'\bchingar\b|\bnacional.*mexican|\bcaracterísticas nacionales', 'National Identity')
rule(r'\bsocial (service|institut)', 'Modern History')
rule(r'\bdemocrat[iz]|\bdemocra[ct]', 'Latin American Politics')
rule(r'\bdiscriminat', 'Human Rights')
rule(r'\btoleran[ct]', 'Ethics')
rule(r'\bcharit[yé]|\bcaridad\b', 'Ethics')
rule(r'\bviolence?\b|\bviolencia\b', 'War & Conflict')
rule(r'\bnew thought\b|\baffirmation[s]?\b|\bcurso de milagros', 'Religion')
rule(r'\bworld records?\b|\brécord', 'Science')
rule(r'\bcuriosi[td]', 'Science')
rule(r'\bpetroleum\b|\bpétrole\b|\bpetróleo\b', 'Economics')
rule(r'\bsilk\b|\bmines?\b', 'Economics')
rule(r'\bgeography\b|\bgeografía', 'Travel Writing')
rule(r'\bstrike[s]?\b|\btransport\b.*\bwork', 'Economics')
rule(r'\bcloning\b', 'Science')
rule(r'\barabi[ac]n nights?\b', 'Oral Tradition & Folklore')
rule(r'\bauto[s]?\s*sacra?mental', 'Drama')
rule(r'\bsátira\b.*\bespañol', 'Satire & Humor')
rule(r'\bretórica\b', 'Rhetoric')
rule(r'\bchristian.*meditat|\bmeditaciones?\b.*\bcristian', 'Catholicism')
rule(r'\bmeditaciones?\b|\bmeditat', 'Religion')
rule(r'\bproofreading\b|\bredacción', 'Literary Criticism')

# ─── FINAL ROUND (ROUND 4) ───

# More junk-like or too-generic entries
rule(r'^Animales\s+Poesia$', 'Poetry')
rule(r'^Bildungsromans$', 'Fiction')
rule(r'^Conducta\b.*\b[EÉ]tic', 'Ethics')
rule(r'^Conducta de vida$', 'Ethics')
rule(r'^Conversation and phrase books$', 'Grammar & Linguistics')
rule(r'\bempire\b|\bemperors?\b', 'Modern History')
rule(r'\bgiants?\b|\bgéants?\b|\bungeheuer\b', 'Oral Tradition & Folklore')
rule(r'\bjournaux intimes\b', 'Diary & Letters')
rule(r'\bliteratură\b', 'Literary Criticism')
rule(r'\bmeditaci[oó]n\b', 'Religion')
rule(r'\bmexicains?\b|\bmexicans?\b', 'Mexico')
rule(r'\bmilitary\b', 'War & Conflict')
rule(r'\bpsicolog[ií]a\b', 'Psychoanalysis')
rule(r'\bspiritual\b', 'Religion')
rule(r'\btrivia\b', 'Anthology')
rule(r'\bvocaci[oó]n\b', 'Education')
rule(r'\bdeaths?\b', 'Death & Mourning')
rule(r'\bantipsych|\bantipsiqui', 'Madness & Mental Illness')
rule(r'\baborigines?\b', 'Indigenous Peoples')
rule(r'\bacteurs?\b|\bactores?\b|\bactuación\b', 'Drama')
rule(r'\badvertising\b', 'Economics')
rule(r'\badviento\b|\badvent\b', 'Catholicism')
rule(r'\bafirmación\b', 'Philosophy')
rule(r'\bafricans?\b', 'Modern History')
rule(r'\balbigenses?\b', 'Medieval History')
rule(r'\balchimi[ae]\b', 'Occult & Esoteric')
rule(r'\banarch[iy]', 'Social Movements')
rule(r'\bantolog[ií]a\b', 'Anthology')
rule(r'\bantropolog[ií]a\b', 'Philosophy')
rule(r'\bargot\b', 'Grammar & Linguistics')
rule(r'\baristóteles\b', 'Philosophy')
rule(r'\barmut\b|\barmoede\b|\barmen\b.*\bpersonen|\bpoor\b', 'Poverty & Class')
rule(r'^Asia$', 'Japan')  # approximate — Asian focus
rule(r'\bborroka\b', 'War & Conflict')
rule(r'\bbureaucra', 'Latin American Politics')
rule(r'\bbusinessm[ae]n\b', 'Economics')
rule(r'\bcalderón de la barca\b', 'Drama')
rule(r'\bcamas\b.*\bliteratura', 'Literary Criticism')
rule(r'\bcambio\b.*\bpsicolog', 'Psychoanalysis')
rule(r'\bcastellà\b', 'Grammar & Linguistics')
rule(r'\bcatalogu[es]?\b.*\bexposit', 'Museums & Collections')
rule(r'\bchinago\b', 'Fiction')
rule(r'\bcid\b.*\b1043', 'Epic')
rule(r'\bciencias?\b.*\bmetodolog', 'Science')
rule(r'\bcit[iy]e?s?\b(?!\s*and\s*town)', 'Urban Life')
rule(r'\bcities and towns?\b', 'Urban Life')
rule(r'\bcompetènci[ae]\b', 'Grammar & Linguistics')
rule(r'\bcomunicació\b', 'Grammar & Linguistics')
rule(r'\bconsejería\b.*\bpastoral', 'Catholicism')
rule(r'\bcont[oi]\b(?!nent)', 'Short Stories')
rule(r'\bcreativ[ei]?\b.*\bthink', 'Education')
rule(r'\bcréation\b', 'Literary Criticism')
rule(r'\bcultural fusion\b', 'Modern History')
rule(r'\bdepresi[oó]n\b.*\bmental|\bdepressive\b', 'Madness & Mental Illness')
rule(r'\bdeveloping countr', 'Economics')
rule(r'\bdos passos\b', 'American Literature')
rule(r'\bechave\b', 'Visual Art')
rule(r'\betiolog[ií]a\b|\betimolog[ií]a\b', 'Grammar & Linguistics')
rule(r'\bethnohistor|\bethnolog|\bethnopsych|\betnopsicolog', 'Modern History')
rule(r'\bevangelistic\b|\bexpérience religieuse', 'Religion')
rule(r'\bfamilles?\b', 'Family')
rule(r'\bfantasmes?\b', 'Psychoanalysis')
rule(r'\bfilmak\b', 'Film & Cinema')
rule(r'\bflorencia\b', 'Italy')
rule(r'\bfoucauld\b', 'Religion')
rule(r'\bfrances\b.*\b(gram[aá]|estudo)', 'Grammar & Linguistics')
rule(r'\bfrancia,?\s*josé', 'Latin American Politics')
rule(r'\bfrancisco de as[ií]s\b', 'Saints & Hagiography')
rule(r'\bfranska\b.*\bspråket', 'Dictionary')
rule(r'\bfrau\b', 'Feminism')
rule(r'\bgargantua\b', 'Fiction')
rule(r'\bgood and evil\b', 'Philosophy')
rule(r'\bgroddeck\b', 'Psychoanalysis')
rule(r'\bguerre mondiale\b', 'War & Conflict')
rule(r'\bhermits?\b', 'Religion')
rule(r'\bherm[eé]neuti', 'Philosophy')
rule(r'\bherodias\b', 'Religion')
rule(r'\bhickock\b|\bsmith,?\s*perry', 'Detective & Mystery')
rule(r'\bhistòri[ae]\b.*\bmèxic', 'Pre-Columbian')
rule(r'\bhoróscopo\b', 'Occult & Esoteric')
rule(r'\bhussein\b', 'Middle East')
rule(r'\bimagis[mt]\b', 'Poetry')
rule(r'\binfluencia\b.*\bliterar', 'Literary Criticism')
rule(r'\bingles\b.*\b(libros|conversaci|autodidacci|hizkera)', 'Grammar & Linguistics')
rule(r'\bitalien\b', 'Italy')
rule(r'\bitaliano\b.*\bverb', 'Grammar & Linguistics')
rule(r'\bjarchas?\b', 'Poetry')
rule(r'\bjeet kune do\b', 'Education')
rule(r'\bjesucristo\b', 'Religion')
rule(r'\bjus d\'orange\b|\borange[s]?\b.*\btherap', 'Medicine & Health')
rule(r'\blaing\b', 'Psychoanalysis')
rule(r'\blengua\b.*\b(franc|ingles)', 'Grammar & Linguistics')
rule(r'\bleon\b.*\bkingdom', 'Spain')
rule(r'\bletteratura\b.*\bcortese', 'Medieval Literature')
rule(r'\blinguistique\b', 'Grammar & Linguistics')
rule(r'\bliteratura\b.*\bmèxic\b.*\bprecolombi', 'Pre-Columbian')
rule(r'\bliteratura\b.*\bguatel[mh]at', 'Latin American Literature')
rule(r'\bliterature\b.*\b(study|theory)', 'Literary Criticism')
rule(r'\bliteratursoziologi|\bliteratuursociologi', 'Literary Criticism')
rule(r'\blittérature\b.*\b(20e|étude|esthétique)', 'Literary Criticism')
rule(r'\blogothérapi', 'Psychoanalysis')
rule(r'\blégendes?\b', 'Oral Tradition & Folklore')
rule(r'\blouvre\b', 'Museums & Collections')
rule(r'\bmagia\b', 'Occult & Esoteric')
rule(r'\bmaladies mentales\b|\bmental disorders?\b', 'Madness & Mental Illness')
rule(r'\bmateria medica\b', 'Medicine & Health')
rule(r'\bmatem[aá]ticas?\b', 'Science')
rule(r'\bmaupassant\b', 'French Literature')
rule(r'\bmentally ill\b', 'Madness & Mental Illness')
rule(r'\bmente y cuerpo\b|\bmind and body\b', 'Philosophy')
rule(r'\bmessico\b', 'Mexico')
rule(r'\bmiddle class\b', 'Poverty & Class')
rule(r'\bmiddle.aged\b', 'Fiction')
rule(r'\bmier\b.*\bjose\b.*\bservando', 'Mexican Literature')
rule(r'\bmillet,?\s*catherine', 'Erotic Literature')
rule(r'\bmito\b', 'Mythology')
rule(r'\bmode\b.*\bsociolog|\bmode\b.*\bmarchandis', 'Fashion')
rule(r'\bmongols?\b', 'Ancient History')
rule(r'\bmorale politique\b', 'Ethics')
rule(r'\bmuḥammad\b', 'Islam')
rule(r'\bmétodos\b.*\bactuaci', 'Drama')
rule(r'\bmönchtum\b', 'Catholicism')
rule(r'\bnarración\b.*\bretórica|\bnarracion\b.*\bretorica', 'Rhetoric')
rule(r'\bnabel\b|\bnavel\b|\bombilic\b', 'Philosophy')
rule(r'\bnew yorker\b', 'Journalism')
rule(r'\bnorth africans?\b', 'North Africa')
rule(r'\bnovellists?.*\bpolacos|\bnovelistas?\b.*\bpolaco', 'Literary Criticism')
rule(r'\bnovelle\b', 'Novella')
rule(r'\bnuns?\b.*\bauthor', 'Literary Criticism')
rule(r'\boperas?\b.*\b(argumento|libret|trama)', 'Opera')
rule(r'\bpatañjali\b', 'Religion')
rule(r'\bpoesias?\b.*\bespañol', 'Poetry')
rule(r'\bprosa\b.*\b(franc|grieg|ingles)', 'Literary Criticism')
rule(r'\bprosa\b$', 'Literary Criticism')
rule(r'\bpowieść\b', 'Fiction')
rule(r'\bpoètes\b', 'Poetry')
rule(r'\bpsicolingü', 'Grammar & Linguistics')
rule(r'\bpsicolog[ií]a\b.*\bpatológic', 'Madness & Mental Illness')
rule(r'\bquartiers\b.*\bmalfamés', 'Urban Life')
rule(r'\bquest[es]?\b.*\b(exped|litt)', 'Fiction')
rule(r'\breading\b', 'Education')
rule(r'\breino unido\b', 'United Kingdom')
rule(r'\breligia[oe]\b|\breligions?\b', 'Religion')
rule(r'\brich people\b', 'Modern History')
rule(r'\brécits?\b.*\b(mer|personnels)', 'Fiction')
rule(r'\brégimes?\b.*\bhypolipi', 'Medicine & Health')
rule(r'\bsailor[s]?\b|\bship captain|\bshipwreck', 'Travel Writing')
rule(r'\bsanté\b', 'Medicine & Health')
rule(r'\bsavater\b', 'Philosophy')
rule(r'\bscriitor[i]?\b', 'Literary Criticism')
rule(r'\bseaside\b|\bskid row\b', 'Urban Life')
rule(r'\bsick\b', 'Medicine & Health')
rule(r'\bsolución\b.*\bproblemas', 'Philosophy')
rule(r'\bspanisch\b.*\bargentinien', 'Grammar & Linguistics')
rule(r'\bstories,?\s*plots', 'Literary Criticism')
rule(r'\bstreet.railroad', 'Economics')
rule(r'\bstudents?\b|\bteachers?\b', 'Education')
rule(r'\bstyle,?\s*literary', 'Literary Criticism')
rule(r'\btausk\b', 'Psychoanalysis')
rule(r'\bteatre\b', 'Drama')
rule(r'\btemptat|\btentati', 'Religion')
rule(r'\bteoría\b|\bteorías\b', 'Philosophy')
rule(r'\bteoría psicoanalít', 'Psychoanalysis')
rule(r'\bterminolog', 'Grammar & Linguistics')
rule(r'\btheaters?\b', 'Drama')
rule(r'\btristan\b$', 'Tristan & Iseult')
rule(r'\btroubadour[s]?\b', 'Medieval Literature')
rule(r'\btroubles bipolaires\b', 'Medicine & Health')
rule(r'\bvilles?\b', 'Urban Life')
rule(r'\bvisual arts?\b', 'Visual Art')
rule(r'\bwortschatz\b', 'Dictionary')
rule(r'\bdt\s+\d{4}$', 'Modern History')  # catch remaining "dt 1978" etc
rule(r'\bethnopsycholog', 'Psychoanalysis')
rule(r'\bjourneys?\b', 'Travel Writing')
rule(r'\bmagie\b|\bsymbole\b', 'Occult & Esoteric')
rule(r'\bästhetik\b', 'Aesthetics')
rule(r'\bérotisme\b', 'Erotic Literature')
rule(r'\bœuvres d\'art\b', 'Visual Art')
rule(r'\bzapata quiroz\b', 'Mexican Literature')
rule(r'\besquivel\b.*\blaura', 'Mexican Literature')
rule(r'\barredondo,?\s*inés', 'Mexican Literature')
rule(r'\bengélica\b.*\bmar[ií]a|\bangélica\b.*\bmar[ií]a', 'Film & Cinema')
rule(r'\bbeats?\s*\(persons\)', 'Beat Generation')

# Final stragglers
rule(r'\balem[aá]n\b.*\b(texto|autodidacc|conversaci|libros)', 'Grammar & Linguistics')
rule(r'\bamérique\b.*\bdécouvert|\bamérique\b.*\brécit', 'Colonialism & Postcolonialism')
rule(r'\bamerikabild\b|\bamerikanen\b', 'United States')
rule(r'\bastronom[ií]a\b', 'Science')
rule(r'\batenci[oó]n\b|\battention\b', 'Education')
rule(r'\bauthors and readers\b', 'Literary Criticism')
rule(r'\bayuda a sí mismo\b', 'Philosophy')
rule(r'\baztèques?\b', 'Indigenous Peoples')
rule(r'\bbach\b', 'Music')
rule(r'\bbeeld', 'Visual Art')
rule(r'\bbobbio\b', 'Philosophy')
rule(r'\bcampos,?\s*alvaro', 'Poetry')
rule(r'\bcontos\b.*\bbrasileir', 'Brazilian Literature')
rule(r'\bdrogas?\b.*\balucinógen', 'Religion')
rule(r'\bendevinament\b', 'Oral Tradition & Folklore')
rule(r'\bespañol\b.*\bcomposici', 'Grammar & Linguistics')
rule(r'\bettedgui\b', 'Gay Literature')
rule(r'\bfolk literature\b', 'Oral Tradition & Folklore')
rule(r'\bhédonisme\b', 'Philosophy')
rule(r'\bimagisme\b', 'Poetry')
rule(r'\bingelesa\b|\bingles\b.*\b(libros|autodidacci)', 'Grammar & Linguistics')
rule(r'\bjokabidea\b|\botoitza\b', 'Education')
rule(r'\bliteratura espanol', 'Spanish Literature')
rule(r'\bmatématicas\b', 'Science')
rule(r'\bmaximes\b', 'Aphorism')
rule(r'\bmysteriegodsdiensten\b', 'Religion')
rule(r'\bparodi[es]\b', 'Satire & Humor')
rule(r'\bpensamiento creativ', 'Education')
rule(r'\bpet owners?\b', 'Animals')
rule(r'\bpoesia\b.*\bsufí|\bpoesía\b.*\b(trabajos|irlandes|líric)', 'Poetry')
rule(r'\bproductie\b', 'Economics')
rule(r'\bproverbes\b', 'Aphorism')
rule(r'\bpsiquiatr[ií]a\b', 'Medicine & Health')
rule(r'\bquête\b', 'Fiction')
rule(r'\bromanciers?\b.*\baméricain', 'American Literature')
rule(r'\bsubconscien|\bsubconci', 'Psychoanalysis')
rule(r'\bstatistics\b', 'Science')
rule(r'\btoleración\b|\btoleration\b', 'Ethics')
rule(r'\bspirituali', 'Religion')
rule(r'^Art\b', 'Visual Art')
rule(r'^Arts\b', 'Visual Art')
rule(r'^CALDERON\b', 'Drama')
rule(r'^PSIQUIATRIA$', 'Medicine & Health')
rule(r'^LITERATURA\b', 'Literary Criticism')
rule(r'^Catalogues?\b', 'Museums & Collections')
rule(r'^Fictie$', 'Fiction')
rule(r'\balcibiades\b', 'Ancient History')
rule(r'\balcoforada\b', 'Correspondence')
rule(r'\balexis,?\s*jacques', 'Latin American Literature')
rule(r'\bargentines?\b', 'Argentina')
rule(r'\baucassin\b', 'Medieval Literature')
rule(r'\barts del llenguatge\b', 'Grammar & Linguistics')
rule(r'\bcats?\b.*\banecdot', 'Animals')
rule(r'\bfoucauld\b', 'Religion')
rule(r'\bcréation\b.*\b(esth|littér)', 'Literary Criticism')
rule(r'\bpoesía\b.*\bS\.\b', 'Poetry')
rule(r'\blittérature\b.*\bétude', 'Literary Criticism')


def classify_subject(subject):
    """Map a raw subject string to a list of new categories."""
    # Check junk patterns first
    for pattern in JUNK_PATTERNS:
        if re.match(pattern, subject, re.IGNORECASE):
            return []

    categories = []
    for regex, cats in RULES:
        if regex.search(subject):
            for c in cats:
                if c not in categories:
                    categories.append(c)

    return categories


def main():
    # Read all unique subjects
    subjects = {}
    with open('/tmp/all_subjects.txt') as f:
        for line in f:
            line = line.strip()
            if '\t' not in line:
                continue
            count, subj = line.split('\t', 1)
            subjects[subj] = int(count)

    # Build mapping
    mapping = {}
    unmapped = []
    mapped_count = 0
    junk_count = 0

    for subj in sorted(subjects.keys()):
        cats = classify_subject(subj)
        mapping[subj] = cats
        if not cats:
            # Check if it was junk
            is_junk = False
            for pattern in JUNK_PATTERNS:
                if re.match(pattern, subj, re.IGNORECASE):
                    is_junk = True
                    junk_count += 1
                    break
            if not is_junk:
                unmapped.append((subj, subjects[subj]))
        else:
            mapped_count += 1

    # Write YAML
    os.makedirs('data', exist_ok=True)
    with open('data/subject_map.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(mapping, f, default_flow_style=None, allow_unicode=True, sort_keys=True, width=200)

    # Collect all categories used
    all_cats = set()
    for cats in mapping.values():
        all_cats.update(cats)

    print(f"Total raw subjects: {len(subjects)}")
    print(f"Mapped to categories: {mapped_count}")
    print(f"Removed as junk: {junk_count}")
    print(f"Unmapped (no match): {len(unmapped)}")
    print(f"Unique categories used: {len(all_cats)}")
    print()

    if unmapped:
        # Sort by count descending
        unmapped.sort(key=lambda x: -x[1])
        print(f"Top unmapped subjects (showing top 50 of {len(unmapped)}):")
        for subj, count in unmapped[:50]:
            print(f"  {count}\t{subj}")

    print()
    print("Categories used:")
    for c in sorted(all_cats):
        print(f"  {c}")


if __name__ == "__main__":
    main()
