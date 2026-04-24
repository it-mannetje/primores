"""
Vult een lege database met de initiële Primores-evenementen.
Wordt automatisch aangeroepen bij de eerste start via app.py.
"""
import sqlite3


PRIMORES_EVENTS = [
    (1993, 12, 'Kerstdiner 1993 — Ochenburg',
     'Kerstdiner bij Restaurant Ochenburg.\nGlenn: HHS Den Haag | Eric: HHS Den Haag'),
    (1994, 12, 'Kerstdiner 1994 — Overalthen',
     'Kerstdiner bij Overalthen.\nLutze: Hotel Den Haag | Eric: HHS | Glenn: Hotel Apollo Amsterdam | Paul: UvA Amsterdam'),
    (1995, 12, 'Kerstdiner 1995 — De Portugees',
     'Kerstdiner bij De Portugees.\nGlenn: Hotel Apollo Amsterdam | Eric: München | Lutze: idem | Paul: idem'),
    (1996, 12, 'Kerstdiner 1996 — ½ ½ (twee locaties)',
     'Een bijzondere editie: het Kerstdiner werd gesplitst over twee locaties (½ ½). De namen van beide locaties zijn niet meer bekend.\nPaul: Arena / India | Lutze: Stedelijk Museum | Glenn: Hotel Apollo'),
    (1997, 12, 'Kerstdiner 1997 — Regles',
     'Kerstdiner bij Regles.\nGlenn: Hotel Victoria Amsterdam | Lutze: NEMO Amsterdam'),
    (1998, 12, 'Kerstdiner 1998 — Regles',
     'Kerstdiner bij Regles (tweede keer op rij).\nPaul: MCI WorldCom'),
    (1999, 12, 'Kerstdiner 1999 — Regles',
     'Kerstdiner bij Regles (derde keer op rij — een favoriet!).\nGlenn: CPC | Eric: VSB | Lutze: Randstad NL | Paul: idem'),
    (2000, 12, 'Kerstdiner 2000 — Millenniumjaar',
     'Kerstdiner in het bijzondere millenniumjaar.\nPaul: net terug uit New York | Glenn: idem | Eric: VSB | Lutze: Randstad'),
    (2001, 12, 'Kerstdiner 2001 — Antwerpen',
     'Kerstdiner in Antwerpen — over de grens!\nGlenn: idem | Paul: New York | Eric: Recagyweb | Lutze: VTL'),
    (2002, 12, 'Kerstdiner 2002 — Den Haag, Javastraat',
     'Kerstdiner aan de Javastraat in Den Haag.\nGlenn: idem | Paul: idem | Eric: idem | Lutze: VTL'),
    (2003, 12, 'Kerstdiner 2003 — Huisoma (bij Jeroen)',
     'Kerstdiner bij Jeroen thuis. Glenn, Lutze, Paul: idem.\nEric: Reshlab'),
    (2004, 12, 'Kerstdiner 2004 — Kookstudio Haarlem',
     'Kerstdiner in de Kookstudio in Haarlem — zelf koken!'),
    (2005, 12, 'Kerstdiner 2005 — De Bosch',
     'Kerstdiner bij De Bosch.\nPaul: Huisharen | Eric: Délifrance | Glenn: idem'),
    (2006, 12, 'Kerstdiner 2006 — Hoogholten',
     'Kerstdiner bij Hoogholten. Na het diner werd de avond vrolijk voortgezet met nachtkloten.\nPaul: Huiskamer | Glenn: idem | Lutze: idem'),
    (2007, 12, 'Kerstdiner 2007 — Zeeland (Rockanje)',
     'Kerstdiner in Zeeland bij Rockanje — een weekendje weg!\nGlenn, Lutze, Eric: idem | Paul: zelfstandig'),
    (2008, 12, 'Kerstdiner 2008 — Oosterbeek',
     'Kerstdiner in Oosterbeek. Bart speelde piano.\nGlenn: idem | Eric: Ticketservice Nederland | Lutze: VTL | Paul: idem'),
    (2009, 12, 'Kerstdiner 2009 — Noordarheide (dropping)',
     'Kerstdiner op de Noordarheide met een dropping als activiteit.\nGlenn: idem | Eric: Ticketservice | Paul: idem'),
    (2010, 12, 'Kerstdiner 2010',
     'Kerstdiner. Paul, Lutze, Glenn: idem.\nEric: Getronics'),
    (2011, 12, 'Kerstdiner 2011 — Noordarheide (Skihut & parcours)',
     'Kerstdiner op de Noordarheide — skihut en parcours als activiteit.\nEric: Eventum | Glenn: Corniche | Paul & Lutze: idem'),
    (2012, 12, 'Kerstdiner 2012 — Scheveningen',
     'Kerstdiner in Scheveningen.\nGlenn: Corniche | Paul: idem | Lutze: idem'),
    (2013, 12, 'Kerstdiner 2013 — Noordarheide (jachthut)',
     'Kerstdiner op de Noordarheide in de jachthut.\nGlenn: Corniche | Eric: idem'),
    (2014, 12, 'Kerstdiner 2014 — Leiden (bij Lutze)',
     'Kerstdiner in Leiden, georganiseerd door Lutze.\nGlenn: Klushero & Corniche'),
    (2015, 12, 'Kerstdiner 2015 — Keti Rotterdam (bij Bart & Barbara)',
     'Kerstdiner bij Restaurant Keti in Rotterdam, georganiseerd door Bart & Barbara. Borrel na afloop.\nGlenn: idem | Paul: idem'),
    (2016, 12, 'Kerstdiner 2016 — Amsterdam (bij Jeroen)',
     'Kerstdiner in Amsterdam, georganiseerd door Jeroen.\nGlenn: idem'),
    (2017, 12, 'Kerstdiner 2017 — Baambrugge (bij Robin)',
     'Kerstdiner in Baambrugge, georganiseerd door Robin.\nGlenn: idem'),
    (2018, 12, 'Kerstdiner 2018 — Geannuleerd',
     'Geen Kerstdiner in 2018.'),
    (2019, 1,  'Nieuwjaarsborrel 2019 — Den Haag',
     'Nieuwjaarsborrel in januari in Den Haag.\nEric: Den Haag | Glenn: idem'),
    (2019, 12, 'Kerstdiner 2019 — Haarlem (bij Gert thuis)',
     'Kerstdiner bij Gert thuis in Haarlem.\nGlenn: idem'),
    (2020, 12, 'Kerstdiner 2020 — Geannuleerd (Corona)',
     'Vanwege de coronapandemie kon het jaarlijkse Kerstdiner geen doorgang vinden. '
     'Voor het eerst in de geschiedenis van de Primores geen fysiek samenzijn met kerst.\nGlenn: idem'),
]


# (year, month) → (city label, lat, lng)
LOCATION_DATA = {
    (1993, 12): ('Ockenburgh, Den Haag',  52.045, 4.222),
    (1994, 12): ('Den Haag',              52.070, 4.300),
    (1995, 12): ('Den Haag',              52.070, 4.300),
    (1997, 12): ('Den Haag',              52.070, 4.300),
    (1998, 12): ('Den Haag',              52.070, 4.300),
    (1999, 12): ('Den Haag',              52.070, 4.300),
    (2000, 12): ('Den Haag',              52.070, 4.300),
    (2001, 12): ('Antwerpen',             51.219, 4.402),
    (2002, 12): ('Den Haag',              52.074, 4.302),
    (2004, 12): ('Haarlem',               52.387, 4.646),
    (2006, 12): ('Holten',                52.280, 6.424),
    (2007, 12): ('Rockanje',              51.872, 4.058),
    (2008, 12): ('Oosterbeek',            51.987, 5.840),
    (2009, 12): ('Noordarheide',          52.248, 5.226),
    (2011, 12): ('Noordarheide',          52.248, 5.226),
    (2012, 12): ('Scheveningen',          52.111, 4.274),
    (2013, 12): ('Noordarheide',          52.248, 5.226),
    (2014, 12): ('Leiden',                52.160, 4.497),
    (2015, 12): ('Rotterdam',             51.922, 4.479),
    (2016, 12): ('Amsterdam',             52.368, 4.904),
    (2017, 12): ('Baambrugge',            52.213, 4.988),
    (2019, 1):  ('Den Haag',              52.070, 4.300),
    (2019, 12): ('Haarlem',               52.387, 4.646),
}


def seed_locations(db_path):
    """Fill in lat/lng for known Primores events. Safe to run on every startup."""
    conn = sqlite3.connect(db_path)
    for (year, month), (name, lat, lng) in LOCATION_DATA.items():
        conn.execute(
            'UPDATE events SET location_name=?, location_lat=?, location_lng=? '
            'WHERE is_primores=1 AND date_year=? AND date_month=? '
            '  AND (location_lat IS NULL OR location_lat="")',
            (name, lat, lng, year, month)
        )
    conn.commit()
    conn.close()


def seed(db_path):
    conn = sqlite3.connect(db_path)
    count = conn.execute('SELECT COUNT(*) FROM events WHERE is_primores=1').fetchone()[0]
    if count == 0:
        for year, month, title, desc in PRIMORES_EVENTS:
            conn.execute(
                'INSERT INTO events (person_name, date_year, date_month, date_day, title, description, '
                'photo_filename, approved, is_primores) VALUES (NULL,?,?,NULL,?,?,NULL,1,1)',
                (year, month, title, desc)
            )
        conn.commit()
        print(f'Seed: {len(PRIMORES_EVENTS)} Primores-evenementen ingevoerd.')
    conn.close()
