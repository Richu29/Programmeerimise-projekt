import io
import json
import sys
import tkinter as tk
from contextlib import redirect_stdout
from itertools import combinations
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from andmed import PAEVAD, ANDMEFAIL, laadi, salvesta

from planeerija import (kellaajaks, kuva_soovitused, leia_soovitused,
                        minutiteks, vahendite_hulk)

class Planeerija:
    def __init__(self, aken):
        self.aken = aken
        self.nadal = laadi()
        self.paev = self.nadal["paev"]
        self.laadimine = True
        self.loengud = []
        self.tegevused = []
        self.ajad = {}
        aken.title("Loenguvahede planeerija")
        aken.geometry("980x720")
        aken.minsize(780, 600)
        stiil = ttk.Style()
        if "vista" in stiil.theme_names():
            stiil.theme_use("vista")
        stiil.configure("Treeview", rowheight=26)
        raam = ttk.Frame(aken, padding=10)
        raam.pack(fill="both", expand=True)

        raam.columnconfigure(0, weight=1)
        raam.rowconfigure(3, weight=1)
        ttk.Label(raam, text="Loenguvahede planeerija",
                  font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(raam, text="Lisa päevakava ja tegevused, määra liikumisajad ning leia sobivad valikud.",
                  ).grid(row=1, column=0, sticky="w", pady=(4, 10))
        riba = ttk.Frame(raam)
        riba.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self.paevavalik = ttk.Combobox(riba, values=PAEVAD, state="readonly", width=14)
        self.paevavalik.set(self.paev)
        self.paevavalik.pack(side="left", padx=(0, 10))
        self.paevavalik.bind("<<ComboboxSelected>>", self.vaheta_paev)
        ttk.Button(riba, text="Laadi näidis", command=self.laadi_naidis).pack(side="left")
        ttk.Label(riba, text="Kaasas olevad vahendid:").pack(side="left", padx=(20, 8))
        self.vahenditekst = tk.StringVar(aken)
        self.vahenditekst.trace_add("write", self.autosalvesta)
        self.vahendid = ttk.Entry(riba, textvariable=self.vahenditekst)
        self.vahendid.pack(side="left", fill="x", expand=True)
        self.lehed = ttk.Notebook(raam)
        self.lehed.grid(row=3, column=0, sticky="nsew")
        self.tabelid = {}
        for liik, pealkiri, veerud in [
                ("loengud", "Loengud", ("Nimi", "Algus", "Lõpp", "Asukoht")),
                ("tegevused", "Tegevused", ("Nimi", "Kestus (min)", "Asukoht", "Vahendid"))]:
            leht = ttk.Frame(self.lehed, padding=8)
            self.lehed.add(leht, text=pealkiri)
            nupud = ttk.Frame(leht)
            nupud.pack(fill="x", pady=(0, 10))
            ttk.Button(nupud, text="Lisa", command=lambda l=liik: self.lisa(l)).pack(side="left")
            ttk.Button(nupud, text="Kustuta valitud", command=lambda l=liik: self.kustuta(l)).pack(side="left", padx=8)
            tabel = ttk.Treeview(leht, columns=veerud, show="headings", selectmode="browse")
            for veerg in veerud:
                tabel.heading(veerg, text=veerg, anchor="w")
                tabel.column(veerg, width=150, minwidth=80)
            kerimine = ttk.Scrollbar(leht, command=tabel.yview)
            tabel.configure(yscrollcommand=kerimine.set)
            kerimine.pack(side="right", fill="y")
            tabel.pack(fill="both", expand=True)
            self.tabelid[liik] = tabel
        self.liikumise_leht = ttk.Frame(self.lehed, padding=8)
        self.lehed.add(self.liikumise_leht, text="Liikumisajad")
        ttk.Label(self.liikumise_leht, text="Aeg minutites, mõlemas suunas sama. Täida kõik paarid.").pack(anchor="w")

        kanvaa = tk.Canvas(self.liikumise_leht, highlightthickness=0, background=stiil.lookup("TFrame", "background"))
        kerimine = ttk.Scrollbar(self.liikumise_leht, command=kanvaa.yview)
        kanvaa.configure(yscrollcommand=kerimine.set)
        kerimine.pack(side="right", fill="y")
        kanvaa.pack(fill="both", expand=True, pady=10)
        self.marsruudid = ttk.Frame(kanvaa)
        kanvaa.create_window((0, 0), window=self.marsruudid, anchor="nw")
        self.marsruudid.bind("<Configure>", lambda e: kanvaa.configure(scrollregion=kanvaa.bbox("all")))
        self.tulemuste_leht = ttk.Frame(self.lehed, padding=8)
        self.lehed.add(self.tulemuste_leht, text="Soovitused")
        self.tulemus = ScrolledText(self.tulemuste_leht, wrap="word", font=("Segoe UI", 10),
                                   state="disabled", padx=8, pady=8)
        self.tulemus.pack(fill="both", expand=True)
        ttk.Button(raam, text="Leia sobivad tegevused",
                   command=self.arvuta).grid(row=4, column=0, sticky="e", pady=(8, 0))
        ttk.Label(raam, text="Kellaajad HH:MM • Vahendid eralda komadega • Soovitused on eraldi alternatiivid",
                  ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.salvestusolek = tk.StringVar(aken)
        ttk.Label(raam, textvariable=self.salvestusolek).grid(row=6, column=0, sticky="w", pady=(4, 0))
        self.ava_paev()
        aken.protocol("WM_DELETE_WINDOW", self.sulge)

    def aja_muutuja(self, tekst=""):
        muutuja = tk.StringVar(self.aken, value=tekst)
        muutuja.trace_add("write", self.autosalvesta)
        return muutuja

    def autosalvesta(self, *args):
        if self.laadimine:
            return True
        rida = self.nadal["paevad"][self.paev]
        rida.update(loengud=self.loengud, tegevused=self.tegevused,
                    vahendid=self.vahendid.get(),
                    ajad={k: v.get() for k, v in self.ajad.items()})
        self.nadal["paev"] = self.paev
        try:
            salvesta(self.nadal)
            self.salvestusolek.set("Salvestatud automaatselt: kasutaja_andmed.json")
            return True
        except OSError:
            self.salvestusolek.set("Salvestamine ebaõnnestus. Kontrolli kausta kirjutamisõigust ja vaba ruumi.")
            return False

    def ava_paev(self):
        self.laadimine = True
        rida = self.nadal["paevad"][self.paev]
        self.loengud = rida["loengud"]
        self.tegevused = rida["tegevused"]
        self.vahenditekst.set(rida["vahendid"])
        self.ajad = {k: self.aja_muutuja(v) for k, v in rida["ajad"].items()}
        self.uuenda()
        self.laadimine = False
        self.autosalvesta()

    def vaheta_paev(self, event=None):
        self.autosalvesta()
        self.paev = self.paevavalik.get()
        self.ava_paev()

    def sulge(self):
        if self.autosalvesta() or messagebox.askyesno(
                "Salvestamine ebaõnnestus", "Kas sulgeda ilma viimaseid muudatusi salvestamata?", parent=self.aken):
            self.aken.destroy()

    def uuenda(self):
        for liik, tabel in self.tabelid.items():
            tabel.delete(*tabel.get_children())
            for indeks, rida in enumerate(getattr(self, liik)):
                if liik == "loengud":
                    vaartused = (rida["nimi"], kellaajaks(rida["algus"]),
                                 kellaajaks(rida["lopp"]), rida["asukoht"])
                else:
                    vaartused = (rida["nimi"], rida["kestus"], rida["asukoht"], ", ".join(rida["vahendid"]))
                tabel.insert("", "end", iid=str(indeks), values=vaartused)
        for laps in self.marsruudid.winfo_children():
            laps.destroy()
        asukohad = sorted({r["asukoht"] for r in self.loengud + self.tegevused})
        for indeks, paar in enumerate(combinations(asukohad, 2)):
            voti = "|".join(paar)
            if voti not in self.ajad:
                self.ajad[voti] = self.aja_muutuja()
            ttk.Label(self.marsruudid, text=f"{paar[0]}  ↔  {paar[1]}").grid(row=indeks, column=0, sticky="w", padx=(0, 24), pady=6)
            ttk.Entry(self.marsruudid, textvariable=self.ajad[voti], width=10).grid(row=indeks, column=1)
        self.tulemus.configure(state="normal")
        self.tulemus.delete("1.0", "end")
        self.tulemus.insert("end", "Vajuta „Leia sobivad tegevused”, et arvutada soovitused.")
        self.tulemus.configure(state="disabled")
        self.autosalvesta()

    def lisa(self, liik):
        dialoog = tk.Toplevel(self.aken)
        dialoog.title("Lisa loeng" if liik == "loengud" else "Lisa tegevus")
        dialoog.transient(self.aken)
        dialoog.resizable(False, False)
        raam = ttk.Frame(dialoog, padding=20)
        raam.pack()
        valjad = (["Nimi", "Algus (HH:MM)", "Lõpp (HH:MM)", "Asukoht"]
                  if liik == "loengud" else ["Nimi", "Kestus (min)", "Asukoht", "Vahendid (komadega)"])
        sisendid = []
        mustandid = self.nadal["paevad"][self.paev]["mustandid"]
        muutujad = [tk.StringVar(dialoog, value=v) for v in mustandid.get(liik, [""] * 4)]

        def salvesta_mustand(*args):
            mustandid[liik] = [v.get() for v in muutujad]
            self.autosalvesta()

        for indeks, nimi in enumerate(valjad):
            ttk.Label(raam, text=nimi).grid(row=indeks, column=0, sticky="w", pady=6, padx=(0, 12))
            muutujad[indeks].trace_add("write", salvesta_mustand)
            sisend = ttk.Entry(raam, width=30, textvariable=muutujad[indeks])
            sisend.grid(row=indeks, column=1, pady=6)
            sisendid.append(sisend)

        def salvesta():
            try:
                tekstid = [s.get().strip() for s in sisendid]
                kohustuslikud = tekstid if liik == "loengud" else tekstid[:3]
                if not all(kohustuslikud):
                    raise ValueError("Täida kõik väljad; ainult vahendid võivad olla tühjad.")
                asukoht = tekstid[3 if liik == "loengud" else 2].casefold()
                if "|" in asukoht:
                    raise ValueError("Asukoht ei tohi sisaldada märki |.")
                rida = {"nimi": tekstid[0], "asukoht": asukoht}
                if liik == "loengud":
                    algus, lopp = minutiteks(tekstid[1]), minutiteks(tekstid[2])
                    if lopp <= algus:
                        raise ValueError("Lõpp peab olema algusest hilisem.")
                    if any(algus < l["lopp"] and lopp > l["algus"] for l in self.loengud):
                        raise ValueError("Loeng kattub olemasoleva loenguga.")
                    rida.update(algus=algus, lopp=lopp)
                else:
                    try:
                        kestus = int(tekstid[1])
                    except ValueError:
                        raise ValueError("Kestus peab olema positiivne täisarv.") from None
                    if kestus < 1:
                        raise ValueError("Kestus peab olema vähemalt 1 minut.")
                    rida.update(kestus=kestus, vahendid=sorted(vahendite_hulk(tekstid[3])))
                getattr(self, liik).append(rida)
                mustandid.pop(liik, None)
                self.uuenda()
                dialoog.destroy()
            except ValueError as viga:
                messagebox.showerror("Kontrolli sisestust", str(viga), parent=dialoog)

        ttk.Button(raam, text="Lisa", command=salvesta).grid(row=4, column=1, sticky="e", pady=(12, 0))
        dialoog.bind("<Return>", lambda e: salvesta())
        dialoog.bind("<Escape>", lambda e: dialoog.destroy())
        dialoog.grab_set()
        sisendid[0].focus_set()

    def kustuta(self, liik):
        valik = self.tabelid[liik].selection()
        if valik:
            getattr(self, liik).pop(int(valik[0]))
            self.uuenda()

    def laadi_naidis(self):
        if (self.loengud or self.tegevused or self.vahendid.get().strip()) and not messagebox.askyesno(
                "Laadi näidis", "Kas asendada valitud päeva andmed näidisandmetega?", parent=self.aken):
            return
        try:
            andmed = json.loads(Path(__file__).with_name("naidis.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as viga:
            messagebox.showerror("Näidise laadimine ebaõnnestus", str(viga), parent=self.aken)
            return
        self.laadimine = True
        self.loengud = andmed["loengud"]
        self.tegevused = andmed["tegevused"]
        self.vahendid.delete(0, "end")
        self.vahendid.insert(0, ", ".join(andmed["olemas"]))
        self.ajad = {k: self.aja_muutuja(str(v)) for k, v in andmed["liikumisajad"].items()}
        self.nadal["paevad"][self.paev]["mustandid"] = {}
        self.laadimine = False
        self.uuenda()

    def arvuta(self):
        try:
            if len(self.loengud) < 2:
                raise ValueError("Lisa vähemalt kaks loengut.")
            asukohad = sorted({r["asukoht"] for r in self.loengud + self.tegevused})
            ajad = {}
            for paar in combinations(asukohad, 2):
                voti = "|".join(paar)
                try:
                    aeg = int(self.ajad[voti].get())
                    if aeg < 0:
                        raise ValueError
                except ValueError:
                    self.lehed.select(self.liikumise_leht)
                    raise ValueError(f"Sisesta paari {paar[0]} / {paar[1]} liikumisaeg mittenegatiivse täisarvuna.") from None
                ajad[voti] = aeg
            tulemused = leia_soovitused(self.loengud, self.tegevused,
                                       vahendite_hulk(self.vahendid.get()), ajad)
            tekst = io.StringIO()
            with redirect_stdout(tekst):
                kuva_soovitused(tulemused)
            self.tulemus.configure(state="normal")
            self.tulemus.delete("1.0", "end")
            self.tulemus.insert("end", tekst.getvalue().strip())
            self.tulemus.configure(state="disabled")
            self.lehed.select(self.tulemuste_leht)
        except ValueError as viga:
            messagebox.showerror("Kontrolli andmeid", str(viga), parent=self.aken)

def main():
    if sys.platform == "win32":
        import ctypes

        try:
            maaratud = ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            maaratud = False
        if not maaratud:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                ctypes.windll.user32.SetProcessDPIAware()
    aken = tk.Tk()
    try:
        Planeerija(aken)
    except (OSError, ValueError) as viga:
        messagebox.showerror("Andmete laadimine ebaõnnestus",
                             f"{ANDMEFAIL}\n{viga}\nFaili ei kirjutatud üle.", parent=aken)
        aken.destroy()
        return
    aken.mainloop()

if __name__ == "__main__":
    main()
