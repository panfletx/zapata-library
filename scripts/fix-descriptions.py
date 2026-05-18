#!/usr/bin/env python3
"""Fix spelling, grammar, encoding, and content issues in book descriptions."""

import os
import re

CONTENT_DIR = "content/catalogue"

# Keys whose body should be cleared entirely (catalog artifacts, Dutch, truncated, etc.)
CLEAR_BODY = {
    "VWS5ZTFQ",   # just "27-28" volume numbers
    "YGVPD54N",   # just "Traducción de: Heart of Darkness"
    "H4EAPD77",   # WorldCat URL artifact
    "ZDB6GIHY",   # WorldCat URL artifact
    "NX4FV8KB",   # subject tags only
    "NQQ6JN53",   # "Analyse : Roman d'amour" catalog entry
    "L7LGQIYS",   # "[Cent nouvelles nouvelles (français moyen). 1879]"
    "CPFRU8CT",   # German library classification tags
    "KVC472AN",   # just the title repeated
    "4DMXDH5V",   # just the title repeated
    "6ZG562PR",   # "En colección pasiva" repeated twice
    "RRLUPDCB",   # Dutch description (French book)
    "U8Q4AU6S",   # Dutch description (Spanish book)
    "385BZAZA",   # truncated mid-word
    "YLGEIJAJ",   # truncated mid-list
    "HU5B7XZV",   # incomplete final sentence
}

# Per-key targeted string replacements: key -> list of (old, new) pairs
REPLACEMENTS = {
    # --- Group 1: Spelling & Grammar ---
    "5AAMNTGH": [
        # combining breve (U+0306) above n instead of precomposed ñ
        ("suen̆o", "sueño"),
    ],
    "5XXQ5GUU": [
        ("soliers", "soldiers"),
        ("international acclaimed", "internationally acclaimed"),
        ("The book present Latin American gays", "The book presents Latin American gays"),
        ("thirty different selection", "thirty different selections"),
    ],
    "DLMCXYLC": [
        ("soliers", "soldiers"),
        ("international acclaimed", "internationally acclaimed"),
        ("The book present Latin American gays", "The book presents Latin American gays"),
        ("thirty different selection", "thirty different selections"),
    ],
    "7W2QLJFH": [
        ("a languages spoken", "a language spoken"),
        (" - from www.powells.com", ""),
    ],
    "AFT8IHXW": [
        ("convertio", "convertido"),
        ("com si en ellos", "como si en ellos"),
    ],
    "CJSBFJU7": [
        ("estilio", "estilo"),
    ],
    "EAL7ZMIE": [
        ("el punto y como está desapareciendo", "el punto y coma está desapareciendo"),
        ("pude permanecer", "puede permanecer"),
    ],
    "F4HAYH4Z": [
        ("Guillemo Samperio", "Guillermo Samperio"),
    ],
    "F7WF7B3L": [
        ("World War 11", "World War II"),
    ],
    "HZ4KXL69": [
        ("el amore", "el amor"),
        ("¿Que se hace", "¿Qué se hace"),
        ("¿como arreglar", "¿cómo arreglar"),
        ("los mas importante", "lo más importante"),
    ],
    "JXKPSAJM": [
        ("la barberie", "la barbarie"),
    ],
    "JQAZUIRX": [
        ("se heurent", "se heurtent"),
    ],
    "K9E6E6E3": [
        ("son los mas cercano", "son los más cercanos"),
    ],
    "KD6LS5KL": [
        ("Kerouac?s", "Kerouac’s"),
        ("be?Beat?", 'be “Beat”'),
        ('that?set them free.?', 'that “set them free.”'),
    ],
    "LI7JQGCH": [
        ("Gzuerra", "Guerra"),
        ("#x93;", "“"),
        ("#x94;", "”"),
    ],
    "MJXWN27N": [
        ("Pharoahs", "Pharaohs"),
    ],
    "NZYKE9WS": [
        ("oversome", "overcome"),
    ],
    "QXKFXJ82": [
        ("sequal", "sequel"),
    ],
    "SRSDFGMM": [
        ("Santa Mariá", "Santa María"),
    ],
    "T5GHCJFI": [
        ("thoughout", "throughout"),
    ],
    "URD2KUES": [
        # "numéro" (French, é=U+00E9) → "número" (Spanish, ú=U+00FA)
        ("numéro", "número"),
    ],
    "DYAFJUKA": [
        ("Autoliberacion", "Autoliberación"),
        ("paginas", "páginas"),
    ],
    "K9E6E6E3": [
        ("resulta mas sana y mucho mas efectiva", "resulta más sana y mucho más efectiva"),
    ],
    "Y2HLREPE": [
        ("An history", "A history"),
    ],
    "DITB6CET": [
        ("heat lightening", "heat lightning"),
    ],
    "2CV9BZK4": [
        ("with another priest win the southwest", "with another priest wins the southwest"),
    ],
    "MW3SK4A2": [
        (", Agriculture,", ", agriculture,"),
        (", Commerce and", ", commerce and"),
    ],

    # --- Group 2: HTML / Encoding Artifacts ---
    "IRTDS7QA": [
        # fac + U+0326 (combining comma below) + ade → façade (precomposed ç U+00E7)
        ("fac̦ade", "façade"),
    ],
    "TJD9L7AL": [
        ("&#39;", "’"),
    ],
    "YVPVKKL6": [
        ("&#39;", "’"),
    ],

    # --- Group 6: Misc Cleanup ---
    "F4HN3C4W": [
        ("--[Source inconnue]", ""),
    ],
}

SPANISH_HISTOIRE = (
    "«Nombrado en el Collège de France, Michel Foucault emprendió, a finales de los "
    "años setenta, un ciclo de cursos dedicado al lugar de la sexualidad en la cultura "
    "occidental: la Historia de la sexualidad, articulada en tres volúmenes (La voluntad "
    "de saber, El uso de los placeres y La inquietud de sí). En ellos prolonga las "
    "investigaciones iniciadas con La arqueología del saber y Vigilar y castigar, pero "
    "concentrando sus análisis en la constelación de fenómenos que designamos como el "
    "«sexo» y la sexualidad. El eje de este proyecto no es erigirse contra una «represión» "
    "de la sexualidad para «liberarla», sino mostrar cómo la vida sexual ha desencadenado "
    "una voluntad sistemática de saberlo todo sobre el sexo que se ha sistematizado en "
    "una «ciencia de la sexualidad» que, a su vez, abre la vía a una administración de "
    "la vida sexual social, cada vez más presente en nuestra existencia. Foucault traza "
    "así la arqueología de los discursos sobre la sexualidad (literatura erótica, práctica "
    "de la confesión, medicina, antropología, psicoanálisis, teoría política, derecho, "
    "etc.) desde el siglo XVII y, sobre todo, en el XIX, del que heredamos hasta en las "
    "posturas recientes de «liberación sexual», donde la actitud censora y la de "
    "emancipación confluyen finalmente en el mismo tipo de presupuesto: el sexo sería "
    "la causa de todos los fenómenos de nuestra vida, como si gobernara el conjunto "
    "de la existencia social.» —Nota del editor"
)

FULL_BODY_REPLACEMENTS = {
    "5SLZ42LZ": SPANISH_HISTOIRE,
    "76NRP8VB": SPANISH_HISTOIRE,
    # Spanish translations of French descriptions (French is not a site language)
    "2DBDBXFX": (
        "Una de las primeras novelas del célebre escritor japonés, redactada entre 1950 y "
        "1953. Todos sus temas y obsesiones están presentes en esta larga crónica situada "
        "en el Tokio de la posguerra sacudido por la ocupación estadounidense"
    ),
    "593WILGJ": (
        "Al llegar en 1327 al refugio de serenidad y neutralidad que es la abadía situada "
        "entre Provenza y Liguria, Guillaume de Baskerville, acompañado de su secretario, "
        "es rogado por el abad para que descubra quién empujó a uno de los monjes a "
        "estrellarse contra el suelo al pie de las venerables murallas. Crímenes, estupro, "
        "vicio, herejía: todo ocurrirá en el transcurso de siete días"
    ),
    "8RJ6N2JI": (
        "Reúne quince extractos de textos modernos o clásicos, franceses o extranjeros, "
        "que presentan un personaje lector: «Fahrenheit 451», «Septentrion», «Balzac y la "
        "pequeña costurera china», «Madame Bovary», «A contrapelo», etc."
    ),
    "97DFM3L6": (
        "En esta novela, Mauriac se ocupa principalmente de los «restos de la nobleza "
        "provinciana, empobrecidos y casi osificados por la ineficacia y el orgullo», y "
        "del maestro rural radical que intenta salvarlos de sí mismos"
    ),
    "9RJL6YTF": (
        "Tres relatos situados en el medio eclesiástico, en el momento en que se instalan "
        "los primeros monasterios benedictinos en los pantanos vendéanos, hacia el año mil, "
        "época en que el cristianismo y el paganismo se aproximan"
    ),
    "A5UR6ZAF": (
        'No se trata de una biografía sino de un ensayo, pues es «a través de su obra, con '
        'sus lecturas e interpretaciones diversas, siempre "inacabada", como vive Rabelais». '
        'Tres partes: la obra en la vida, la obra y el tiempo, Rabelais testigo y juez de '
        'su época. Dirigido principalmente a un público universitario'
    ),
    "CVWDLDTG": (
        "Marguerite Duras vivió la última guerra a la vez como mujer cuyo marido había sido "
        "deportado, como resistente y también como escritora. Lúcida, asombrada, desesperada "
        "a veces, durante esos años llevó un diario y escribió textos inspirados en todo lo "
        "que veía, en lo que vivía, en las personas que encontraba o a las que se enfrentaba"
    ),
    "EG2PIBYK": (
        "Con el estilo deslumbrante del escritor, un diálogo no tan imaginario como parece, "
        "en el que se desvelan con una ironía a la vez burlona y seria las relaciones entre "
        "autor y editor, y viceversa. Entre las invectivas propias del autor afloran algunas "
        "verdades que es mejor no decir. Un panfleto de interés incluso para quienes no han "
        "leído a Céline"
    ),
    "I5WZL8IV": (
        "De la Alemania fue como un poderoso instrumento que hizo la primera brecha en la "
        "muralla de antiguos prejuicios levantada entre nosotros y Francia. No creo que haya "
        "que buscar en otro lugar la viva imagen de ese florecimiento del genio alemán, el "
        "cuadro de esa época brillante y poética que puede llamarse el siglo de Goethe. "
        "Sainte-Beuve — [Contraportada]"
    ),
    "JQAZUIRX": (
        "Este libro está destinado a los estudiantes extranjeros que, habiendo adquirido el "
        "vocabulario básico y las frases más simples de la lengua francesa, y contando también "
        "con algunas nociones gramaticales, se enfrentan a las estructuras más complejas del "
        "idioma"
    ),
    "PGHK4FLP": (
        "Fantasía parabólica situada en Milán a finales del siglo XV, narra la desventurada "
        "historia del modelo que utilizó el pintor para La Última Cena"
    ),
    "QYDXX6PL": (
        "Un hombre, su esposa y su grupo de diecinueve niños adoptados discapacitados "
        "atraviesan la Alemania devastada al final de la Segunda Guerra Mundial hasta ser "
        "rescatados por la Cruz Roja"
    ),
    "RQBRSWQL": (
        "Cada una de las ocho novelas y narraciones de Perec, miembro del Oulipo fallecido "
        "en 1982, va precedida de un prefacio inédito y acompañada de un estudio general "
        "sobre el novelista y de referencias biográficas"
    ),
    "T5GHCJFI": "El Principito descubre los secretos de la amistad a lo largo de sus viajes por el universo",
    "U5HWNHDU": (
        "Crónica del día a día en una isla cargada de historia, cuyo presente —los años "
        "cincuenta— presagia las convulsiones de la modernidad y las luchas por la "
        "independencia de 1955 a 1959. Lo que fascina a Durrell: la sencillez, la elegancia, "
        "la autenticidad de los seres que lo rodean, la belleza de los paisajes, la riqueza "
        "y diversidad de una naturaleza exuberante, cálida y vibrante de sol. Un artista que "
        "pasea por el país de los sueños y reinventa el abecedario de lo maravilloso"
    ),
    "VBV38PML": (
        "En un país en guerra, dos gemelos se separan. Uno de ellos cruza la frontera, "
        "dejando al otro desvalido y privado de una parte de sí mismo. Lucas parece querer "
        "consagrarse al bien. Cuando Claus regresa treinta años después, Lucas ha "
        "desaparecido. El único testimonio de su existencia compartida: el Gran Cuaderno"
    ),
    "WEUXT52I": (
        "Selección de 19 fabliaux ingeniosos o representativos, extraídos de un conjunto de "
        "entre 130 y 160. Más de treinta páginas de notas de carácter filológico o histórico"
    ),
    "WIA7JNAD": (
        "Un profesor universitario en la edad del demonio de mediodía no logra satisfacer "
        "las exigencias de su esposa. Sobre este tema, el autor ha construido un estudio "
        "psicológico cuyo patético interés alcanza lo trágico"
    ),
    # Spanish translation of Portuguese description (Portuguese is not a site language)
    "JR6E9Z99": (
        "Gilberto Cabeggi ofrece en este libro numerosos consejos sobre actitudes y formas "
        "de pensar que traerán más felicidad a tu vida. Son píldoras de entusiasmo, con la "
        "fuerza de las cosas simples y el poder de ayudarte a ser más feliz"
    ),
    # Spanish translations of English WorldCat descriptions
    "39XF6WZ8": "Recoge las definiciones de más de 70 000 palabras de la lengua española",
    "4I65F8FF": (
        "Novela brasileña del siglo XIX que sigue las aventuras de Amaro, conocido como "
        "«Bom Crioulo», un hombre gay generoso y cariñoso, aunque a veces dado a la bebida"
    ),
    "8LZND5LF": (
        "En La Habana, Cuba, una mujer es golpeada, violada y estrangulada con una toalla. "
        "En su apartamento se encuentra marihuana y su guardarropa resulta sospechosamente "
        "por encima de las posibilidades de una profesora de secundaria"
    ),
    "CD5MSCQ3": (
        "La más reciente novela de uno de los autores costarricenses más exitosos y prolíficos, "
        "su séptima obra literaria publicada. El libro se centra en los viajes de un joven que "
        "regresa a su Costa Rica natal para enfrentarse a la esquizofrenia y la homofobia universales"
    ),
    "GASSHZL7": (
        "Novela brasileña del siglo XIX que sigue las aventuras de Amaro, conocido como "
        "«Bom Crioulo», un hombre gay generoso y cariñoso, aunque a veces dado a la bebida"
    ),
    "MRX5ALJS": "Breve novela que explora el tema de la homosexualidad en la Cuba posrevolucionaria",
    "MW3SK4A2": (
        "[Libro 1]. Consideraciones generales sobre la extensión y el aspecto físico del reino "
        "de la Nueva España. Influencia de la configuración del suelo en el clima, la agricultura, "
        "el comercio y la defensa militar del país"
    ),
    "NNBT22R3": (
        "Nueve cuentos que revelan el mundo íntimo de una pequeña comunidad puertorriqueña "
        "unida por su sexualidad transgresora. Las historias exploran la naturaleza a veces "
        "hilarante y a veces desgarradora de la supervivencia en un mundo decididamente cruel"
    ),
    "QW2G6CUU": (
        "Analiza la geografía de la literatura homoerótica desde finales del siglo XIX hasta "
        "la actualidad, ofreciendo una panorámica de los temas y referencias gay en la poesía, "
        "el cuento y la novela. Traza la trayectoria de la literatura gay desde las notas "
        "escandalosas de la prensa decimonónica hasta los estereotipos de principios del siglo XX "
        "y la creciente complejidad y seguridad de voces como las de Carlos Pellicer, "
        "Germán Pardo García, José T. de Cuéllar y otros"
    ),
    "RVAHYJAE": (
        "Los temas del desamor y la tristeza de las mujeres que envejecen dominan esta "
        "colección de relatos de la célebre autora canadiense"
    ),
    "SQ78AKEE": "Fragmentos de los escritos de exploradores y folcloristas",
    "SRSDFGMM": (
        "Carr, hundido en la mala suerte tras el abandono de su esposa, acepta un trabajo "
        "en el puerto de Santa María y, al descubrir que sirve de tapadera para traficantes "
        "de drogas, comprende que lo único que le queda es registrar sus sentimientos en un diario"
    ),
    "UTFL8G5C": (
        "La colección de 1978 de Thomas Bernhard, compuesta por 104 microrrelatos o viñetas, "
        "ninguno de más de una página, refleja su profundo odio hacia su Austria natal, "
        "a la que describe como «un infierno común donde el intelecto es incesantemente "
        "difamado y el arte y la ciencia son destruidos»; una miniantología de sus obsesiones "
        "con la locura, el crimen, la corrupción política y la incapacidad del lenguaje para "
        "capturar o aliviar el absurdo de la vida"
    ),
    "WJJ8GUKJ": "Ofrece consejos para el tratamiento de una amplia variedad de dolencias humanas",
    "YC32RCRQ": (
        "«Saltatriz es una mujer diminuta que vende canciones usadas, y Diminuto tiene "
        "un minuto en el lugar donde debería estar su corazón; los dos se encuentran en el "
        "centro de este insólito libro dos en uno.» —Nota del editor"
    ),
    "YMT2DETY": (
        "Entreteje las historias de amor de un hombre y una mujer en el mundo prehistórico "
        "con las del director de orquesta Gabriel Atlan-Ferrera y la cantante Inez Prada "
        "durante una producción de la ópera de Berlioz «La condenación de Fausto»"
    ),
    "YTT3SVPH": (
        "Novela brasileña del siglo XIX que sigue las aventuras de Amaro, conocido como "
        "«Bom Crioulo», un hombre gay generoso y cariñoso, aunque a veces dado a la bebida"
    ),
    # Fix double-s from idempotency bug ("selectionss" → "selections")
    "5XXQ5GUU": (
        "This is an in-depth anthology of fiction of gay themes by twenty-four writers, "
        "among them the internationally acclaimed Mariel Puig (Argentina), "
        "Mário de Andrade (Brazil), and Reinaldo Arenas (Cuba). The book presents Latin "
        "American gays as part of a lively, fascinating social reality--as soldiers, "
        "businessman, office workers, students, cattle ranchers, circus performers... "
        "Included are two complete novellas--one about homosexuality in the marines, "
        "the other about a sexual encounter between two high-school boys; also the "
        'brilliant "Orgy"--an erotic diary based on experiences in tropical Brazil. '
        "Almost 400 pages with thirty different selections by a dazzling array of talent"
    ),
    "DLMCXYLC": (
        "This is an in-depth anthology of fiction of gay themes by twenty-four writers, "
        "among them the internationally acclaimed Mariel Puig (Argentina), "
        "Mário de Andrade (Brazil), and Reinaldo Arenas (Cuba). The book presents Latin "
        "American gays as part of a lively, fascinating social reality--as soldiers, "
        "businessman, office workers, students, cattle ranchers, circus performers... "
        "Included are two complete novellas--one about homosexuality in the marines, "
        "the other about a sexual encounter between two high-school boys; also the "
        'brilliant "Orgy"--an erotic diary based on experiences in tropical Brazil. '
        "Almost 400 pages with thirty different selections by a dazzling array of talent"
    ),
    # Fix missing accents in Spanish text
    "CJSBFJU7": (
        "Con un estilo sobrio, sencillo y directo B. Traven recrea varias anécdotas que "
        "seguramente vivió y en las cuales puede disfrutarse la bucólica sabiduría de un "
        "indio artista frente a la obtusa visión de la modernidad en Canastitas en serie "
        "o el inefable sentido común de un modesto minero en El suplicio de San Antonio. "
        "El mundo urbano del México de los cuarenta también asoma en este fonograma, "
        "cuya lectura estuvo a cargo de Francisco Rebolledo, en el tierno relato Amistad"
    ),
    # Spanish translations of English WorldCat descriptions (second pass)
    "2DLHRYSN": (
        "Joaquín lucha con los valores tradicionales, el machismo de su padre, "
        "su adicción a la cocaína y sus tendencias homosexuales en Lima, Perú, "
        "antes de escapar a Miami"
    ),
    "7W2QLJFH": (
        "El Diccionario Panhispánico de Dudas orienta a sus usuarios en el uso correcto "
        "de la lengua española. Ofrece recomendaciones ilustradas con ejemplos extraídos "
        "de los bancos de datos de la Real Academia Española. Es una obra concebida desde "
        "todos los países hispanohablantes, que mantiene el equilibrio fundamental entre "
        "la variedad de hablas de tan distintas regiones y la unidad lingüística que debe "
        "preservarse. En suma, da respuestas claras a las dudas de quienes se preocupan "
        "por hablar y escribir bien en español"
    ),
    "9KL5X9PT": "Traducción al español del poema épico de Homero",
    "F4HAYH4Z": (
        "Antología crítica de narrativa gay que revisa y actualiza la publicada por el "
        "mismo sello en 1996. Además de 25 cuentos de autores reconocidos como Inés "
        "Arredondo, Juan Vicente Melo, Enrique Serna, Guillermo Samperio y otros, el "
        "volumen incluye dos ensayos sobre la evolución de la literatura gay en México "
        "y aspectos de las obras reunidas en esta antología"
    ),
    "I8HBY8GX": (
        "Un tour de force del humor negro compuesto de breves biografías de autores "
        "panamericanos imaginarios, con retratos a veces patéticamente cómicos, "
        "otras veces sorprendentemente conmovedores y en ocasiones genuinamente "
        "escalofriantes"
    ),
    "JV4F6W5D": (
        "Estudia las cartas enviadas por el poeta colombiano al célebre escritor mexicano "
        "Carlos Pellicer (1897-1977). Aunque Pardo no conservó las cartas que Pellicer "
        "le escribió, sus misivas apuntan a una relación amorosa entre los dos hombres. "
        "Da cuenta de lo que Pardo García llamó la amistad «perfecta y única» entre ambos, "
        "así como de las semillas de gran parte de la propia poesía de Pardo García. "
        "Incluye un ensayo de 2013 de León Guillermo Gutiérrez sobre el poema «Recinto» "
        "de Pellicer como «primer poema homoerótico en la poesía mexicana»"
    ),
    "PTD3ZAXD": (
        "Relato del viaje por tierra que realizó Madame Calderón de la Barca, esposa del "
        "primer embajador español en México, de Veracruz a la Ciudad de México en el "
        "siglo XIX"
    ),
    "WZK7SV59": (
        "Una novela sin censura que va donde ninguna obra de ficción norteamericana ha "
        "llegado antes. Una estrella del porno se propone coronar su carrera rompiendo "
        "el récord de escenas de sexo en pantalla"
    ),
    "XU5APNK5": (
        "César es un traductor que atraviesa tiempos muy difíciles a causa de la crisis "
        "económica mundial; es también escritor y un científico loco empeñado en dominar "
        "el mundo. En una visita a la playa resuelve intuitivamente un enigma ancestral, "
        "encuentra un tesoro pirata y se convierte en hombre muy rico. Aun así, su "
        "proyecto de dominación mundial sigue siendo su prioridad, por lo que asiste a "
        "un congreso literario para acercarse al hombre cuyo clon espera que encabece "
        "un ejército victorioso: el mundialmente célebre escritor mexicano Carlos Fuentes. "
        "Una fantasía de ciencia ficción cómica"
    ),
}


def split_file(text):
    m = re.match(r'^(---\n.*?\n---\n?)', text, re.DOTALL)
    if not m:
        return text, ""
    header = m.group(1)
    body = text[len(header):]
    return header, body


# Front-matter field corrections: key -> list of (old_line, new_line) pairs
FRONTMATTER_FIXES = {
    # Book is in Spanish; WorldCat had it incorrectly catalogued as English
    "K9E6E6E3": [("- English", "- Español")],
}


def process_file(key, path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    header, body = split_file(text)
    original_header = header

    if key in FRONTMATTER_FIXES:
        for old_line, new_line in FRONTMATTER_FIXES[key]:
            header = header.replace(old_line, new_line, 1)

    original_body = body

    if key in CLEAR_BODY:
        body = ""
    elif key in FULL_BODY_REPLACEMENTS:
        body = FULL_BODY_REPLACEMENTS[key] + "\n"
    elif key == "F7KJ96FC":
        # Keep only the Spanish paragraph; strip from ENGLISH DESCRIPTION onward
        marker = " ENGLISH DESCRIPTION"
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx].rstrip() + "\n"
    else:
        if key in REPLACEMENTS:
            for old, new in REPLACEMENTS[key]:
                body = body.replace(old, new)

    if body != original_body or header != original_header:
        if body:
            body = body.rstrip('\n') + '\n'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(header + body)
        return True
    return False


def main():
    changed = 0
    skipped = 0
    all_keys = CLEAR_BODY | set(FULL_BODY_REPLACEMENTS) | set(REPLACEMENTS) | set(FRONTMATTER_FIXES) | {"F7KJ96FC"}

    for key in sorted(all_keys):
        path = os.path.join(CONTENT_DIR, f"{key}.md")
        if not os.path.exists(path):
            print(f"  MISSING: {key}")
            skipped += 1
            continue
        if process_file(key, path):
            print(f"  fixed:   {key}")
            changed += 1
        else:
            print(f"  no-op:   {key}")

    print(f"\nDone. {changed} files changed, {skipped} missing.")


if __name__ == "__main__":
    main()
