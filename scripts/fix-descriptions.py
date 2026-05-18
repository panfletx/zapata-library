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

FRENCH_HISTOIRE = (
    "«Nommé au Collège de France, Michel Foucault a entrepris, "
    "durant la fin des années soixante-dix, un cycle de cours consacré "
    "à la place de la sexualité dans la culture occidentale : "
    "l’Histoire de la sexualité, articulée en trois volumes "
    "(la Volonté de savoir, L’usage des plaisirs et Le souci de soi). "
    "Il y prolonge les recherches entreprises avec L’archéologie du savoir "
    "et Surveiller et punir, mais en concentrant ses analyses sur la constellation "
    "de phénomènes que nous désignons par le « sexe » "
    "et la sexualité. L’axe de cette entreprise n’est pas de s’ériger "
    "contre une « répression » de la sexualité afin de la "
    "« libérer », mais de montrer comment la vie sexuelle a "
    "enclenché une volonté systématique de tout savoir sur le sexe "
    "qui s’est systématisée en une « science de la sexualité » "
    "laquelle, à son tour, ouvre la voie à une administration de la vie sexuelle "
    "sociale, de plus en plus présente dans notre existence. Foucault fait ainsi "
    "l’archéologie des discours sur la sexualité (littérature érotique, "
    "pratique de la confession, médecine, anthropologie, psychanalyse, théorie "
    "politique, droit, etc.) depuis le XVIIᵉ siècle et, surtout, au XIXᵉ, "
    "dont nous héritons jusque dans les postures récentes de "
    "« libération sexuelle », l’attitude de censure et celle "
    "d’affranchissement se rencontrant finalement dans le même type de "
    "présupposé : le sexe serait cause de tous les phénomènes "
    "de notre vie comme il commanderait l’ensemble de l’existence sociale.»"
    "—Mot de l’Éditeur"
)

FULL_BODY_REPLACEMENTS = {
    "5SLZ42LZ": FRENCH_HISTOIRE,
    "76NRP8VB": FRENCH_HISTOIRE,
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
    # French translation of English WorldCat description
    "T5GHCJFI": (
        "Le Petit Prince découvre les secrets de l'amitié au fil de ses voyages "
        "à travers l'univers"
    ),
    # French translations of English WorldCat descriptions
    "97DFM3L6": (
        "Dans ce roman, Mauriac s'attache principalement aux «restes de la noblesse provinciale, "
        "appauvris et presque ossifiés par l'inefficacité et l'orgueil», et à l'instituteur "
        "radical du village qui tente de les sauver d'eux-mêmes"
    ),
    "QYDXX6PL": (
        "Un homme, sa femme et leur bande de dix-neuf enfants adoptés, baveux et arriérés, "
        "traversent l'Allemagne dévastée à la fin de la Seconde Guerre mondiale jusqu'à ce "
        "qu'ils soient secourus par la Croix-Rouge"
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
