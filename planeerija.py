"""Töö: loengutevahelise aja planeerija.
Tegijad: Ats Põtter ja Richard Anmann.

Käivitamine: ava projekti kaustas terminal ja sisesta python gui.py.
Tekstiliidese käivitamiseks sisesta python planeerija.py.
Vaja on Python 3.9 või uuemat koos Tkinteri (Tcl/Tk) toega.
Hoia gui.py, planeerija.py, andmed.py ja naidis.json samas kaustas.
Sisestused salvestatakse automaatselt faili kasutaja_andmed.json.

Allikad: aine projekti juhend ja autorite projektiidee.
"""

import json
from pathlib import Path

def minutiteks(kellaaeg):
    """Teisenda HH:MM kujul kellaaeg minutiteks päeva algusest."""
    osad = kellaaeg.strip().split(":")
    if len(osad) != 2:
        raise ValueError("Kasuta kuju HH:MM, näiteks 09:15.")
    tunnid, minutid = map(int, osad)
    if not (0 <= tunnid <= 23 and 0 <= minutid <= 59):
        raise ValueError("Kellaaeg peab jääma vahemikku 00:00–23:59.")
    return tunnid * 60 + minutid

def kellaajaks(minutid):
    """Vorminda minutites antud kellaaeg kujule HH:MM."""
    return f"{minutid // 60:02d}:{minutid % 60:02d}"

def kusi_tekst(kusimus):
    """Küsi mittetühi tekst ja korda küsimust tühja vastuse korral."""
    while True:
        vastus = input(kusimus).strip()
        if vastus:
            return vastus
        print("Sisesta vähemalt üks märk.")

def kusi_arv(kusimus, miinimum=0):
    """Küsi täisarv, mis on vähemalt etteantud miinimum."""
    while True:
        try:
            arv = int(input(kusimus))
            if arv >= miinimum:
                return arv
        except ValueError:
            pass
        print(f"Sisesta täisarv, mis on vähemalt {miinimum}.")

def kusi_kellaaeg(kusimus):
    """Küsi kellaaeg, kuni kasutaja sisestab sobiva väärtuse."""
    while True:
        try:
            return minutiteks(input(kusimus))
        except ValueError as viga:
            print(viga)

def vahendite_hulk(tekst):
    """Eralda komadega loetletud vahendid ning ühtlusta kirjapilt."""
    return {osa.strip().casefold() for osa in tekst.split(",") if osa.strip()}

def kusi_andmed():
    """Kogu tekstiliideses ühe päeva loengud, tegevused ja liikumisajad."""
    loengud = []
    print("\nSisesta ühe päeva loengud. Kasuta asukohtade puhul samu nimesid.")
    for number in range(kusi_arv("Loengute arv (vähemalt 2): ", 2)):
        print(f"\nLoeng {number + 1}")
        nimi = kusi_tekst("Nimi: ")
        while True:
            algus = kusi_kellaaeg("Algus (HH:MM): ")
            lopp = kusi_kellaaeg("Lõpp (HH:MM): ")
            if lopp <= algus:
                print("Lõpp peab olema algusest hilisem.")
            elif any(algus < l["lopp"] and lopp > l["algus"] for l in loengud):
                print("See loeng kattub varem sisestatud loenguga.")
            else:
                break
        loengud.append({"nimi": nimi, "algus": algus, "lopp": lopp,
                        "asukoht": kusi_tekst("Asukoht: ").casefold()})

    olemas = vahendite_hulk(input("\nKaasas olevad vahendid (komadega, võib tühjaks jätta): "))
    tegevused = []
    for number in range(kusi_arv("Tegevuste arv: ")):
        print(f"\nTegevus {number + 1}")
        tegevused.append({
            "nimi": kusi_tekst("Nimi: "),
            "kestus": kusi_arv("Kestus minutites: ", 1),
            "asukoht": kusi_tekst("Asukoht: ").casefold(),
            "vahendid": sorted(vahendite_hulk(input("Vajalikud vahendid (komadega): "))),
        })

    asukohad = sorted({r["asukoht"] for r in loengud + tegevused})
    liikumisajad = {}
    print("\nSisesta liikumisajad. Alfaversioonis on mõlemas suunas sama aeg.")
    for indeks, lahtekoht in enumerate(asukohad):
        for sihtkoht in asukohad[indeks + 1:]:
            aeg = kusi_arv(f"{lahtekoht} <-> {sihtkoht} (min): ")
            liikumisajad[f"{lahtekoht}|{sihtkoht}"] = aeg
    return loengud, tegevused, olemas, liikumisajad

def liikumisaeg(lahtekoht, sihtkoht, liikumisajad):
    """Leia kahe asukoha vaheline aeg; samas kohas on see null."""
    if lahtekoht == sihtkoht:
        return 0
    voti = "|".join(sorted([lahtekoht, sihtkoht]))
    return liikumisajad[voti]

def leia_soovitused(loengud, tegevused, olemas, liikumisajad):
    """Leia igasse loenguvahesse sobivad tegevused eraldi alternatiividena."""
    jarjestatud = sorted(loengud, key=lambda loeng: loeng["algus"])
    tulemused = []
    # Kõrvutiste loengute lõpu ja alguse vahele jääb võimalik vaba aeg.
    for eelmine, jargmine in zip(jarjestatud, jarjestatud[1:]):
        algus, lopp = eelmine["lopp"], jargmine["algus"]
        if lopp <= algus:
            continue
        sobivad = []
        for tegevus in tegevused:
            if not set(tegevus["vahendid"]).issubset(olemas):
                continue
            minek = liikumisaeg(eelmine["asukoht"], tegevus["asukoht"], liikumisajad)
            tagasitee = liikumisaeg(tegevus["asukoht"], jargmine["asukoht"], liikumisajad)
            # Arvesse läheb ka teekond tegevuseni ja sealt järgmisse loengusse.
            vajalik_aeg = minek + tegevus["kestus"] + tagasitee
            if vajalik_aeg <= lopp - algus:
                sobivad.append({"tegevus": tegevus, "algus": algus + minek,
                                "lopp": algus + minek + tegevus["kestus"],
                                "minek": minek, "tagasitee": tagasitee,
                                "varu": lopp - algus - vajalik_aeg})
        tulemused.append({"eelmine": eelmine, "jargmine": jargmine,
                          "algus": algus, "lopp": lopp, "sobivad": sobivad})
    return tulemused

def kuva_soovitused(tulemused):
    """Väljasta tegevuste ajad, liikumisajad ja alles jääv vaba aeg."""
    print("\n--- SOOVITUSED ---")
    print("Iga loetletud tegevus on eraldi valik, mitte ühine päevaplaan.")
    if not tulemused:
        print("Loengute vahel pole vaba aega.")
    for vahe in tulemused:
        print(f"\n{kellaajaks(vahe['algus'])}–{kellaajaks(vahe['lopp'])} "
              f"({vahe['lopp'] - vahe['algus']} min): "
              f"{vahe['eelmine']['nimi']} -> {vahe['jargmine']['nimi']}")
        if not vahe["sobivad"]:
            print("  Ükski tegevus ei sobi aja, liikumise ja vahendite poolest.")
        for soovitus in vahe["sobivad"]:
            tegevus = soovitus["tegevus"]
            print(f"  - {tegevus['nimi']} ({tegevus['asukoht']}): "
                  f"{kellaajaks(soovitus['algus'])}–{kellaajaks(soovitus['lopp'])}")
            print(f"    Liikumine enne {soovitus['minek']} min, "
                  f"pärast {soovitus['tagasitee']} min; "
                  f"vaba aega jääb {soovitus['varu']} min.")

def main():
    """Käivita tekstiliides oma andmete või näidisandmetega."""
    print("LOENGUTEVAHELISE AJA PLANEERIJA")
    print("1 – sisesta oma andmed\n2 – vaata näidet")
    while True:
        valik = input("Valik: ").strip()
        if valik in {"1", "2"}:
            break
        print("Vali 1 või 2.")
    if valik == "2":
        fail = Path(__file__).with_name("naidis.json")
        andmed = json.loads(fail.read_text(encoding="utf-8"))
        loengud = andmed["loengud"]
        tegevused = andmed["tegevused"]
        olemas = set(andmed["olemas"])
        liikumisajad = andmed["liikumisajad"]
    else:
        loengud, tegevused, olemas, liikumisajad = kusi_andmed()
    kuva_soovitused(leia_soovitused(loengud, tegevused, olemas, liikumisajad))

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgramm lõpetatud.")
