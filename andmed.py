import json
from pathlib import Path

PAEVAD = ("Esmaspäev", "Teisipäev", "Kolmapäev", "Neljapäev", "Reede")
ANDMEFAIL = Path(__file__).with_name("kasutaja_andmed.json")

def uus_nadal():
    return {"paev": PAEVAD[0], "paevad": {
        paev: {"loengud": [], "tegevused": [], "vahendid": "",
               "ajad": {}, "mustandid": {}} for paev in PAEVAD}}

def laadi(fail=ANDMEFAIL):
    if not fail.exists():
        return uus_nadal()
    andmed = json.loads(fail.read_text(encoding="utf-8"))
    try:
        assert andmed["paev"] in PAEVAD
        for paev in PAEVAD:
            rida = andmed["paevad"][paev]
            assert isinstance(rida["vahendid"], str)
            assert isinstance(rida["ajad"], dict)
            assert all(isinstance(k, str) and isinstance(v, str) for k, v in rida["ajad"].items())
            assert isinstance(rida["mustandid"], dict)
            for liik, valjad in rida["mustandid"].items():
                assert liik in ("loengud", "tegevused")
                assert isinstance(valjad, list) and len(valjad) == 4
                assert all(isinstance(v, str) for v in valjad)
            for liik in ("loengud", "tegevused"):
                assert isinstance(rida[liik], list)
                for kirje in rida[liik]:
                    assert isinstance(kirje["nimi"], str)
                    assert isinstance(kirje["asukoht"], str)
                    if liik == "loengud":
                        assert 0 <= kirje["algus"] < kirje["lopp"] < 1440
                    else:
                        assert isinstance(kirje["kestus"], int) and kirje["kestus"] > 0
                        assert isinstance(kirje["vahendid"], list)
                        assert all(isinstance(v, str) for v in kirje["vahendid"])
    except (KeyError, TypeError, AssertionError) as viga:
        raise ValueError("Salvestatud andmefaili struktuur on vigane.") from viga
    return andmed

def salvesta(andmed, fail=ANDMEFAIL):
    ajutine = fail.with_suffix(".tmp")
    ajutine.write_text(json.dumps(andmed, ensure_ascii=False, indent=2), encoding="utf-8")
    ajutine.replace(fail)
