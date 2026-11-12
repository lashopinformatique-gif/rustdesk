#!/usr/bin/env python3
"""
linux_deb.py - Transforme le paquet .deb fabriqué par build.py (nommé « rustdesk »)
en paquet à la marque configurée dans supportdirect.toml.

Usage :
    python3 linux_deb.py --config supportdirect.toml --deb rustdesk-1.5.1-x86_64.deb \
        --version 1.5.5 --out SupportDirect-1.5.5-x86_64.deb

Pourquoi : sous Linux, le programme retrouve tout par le nom de l'application en
minuscules (service systemd, fichier .desktop, liens <nom>://, processus). Le paquet
d'origine installe tout sous « rustdesk » : le service ne démarrerait pas depuis
l'interface et les liens ne s'ouvriraient pas. Ici, chaque chemin et chaque script
passe à <nom>, sans toucher aux fichiers de RustDesk dans le dépôt, et le paquet
peut cohabiter avec un RustDesk officiel installé sur le même poste.

Nécessite dpkg-deb (présent sur Debian/Ubuntu) et Pillow.
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from PIL import Image

OLD = "rustdesk"
ICON_SIZES = (32, 48, 64, 128, 256, 512)
# Seul fichier qui garde l'ancien nom : le programme le charge sous ce nom précis.
KEEP = ("lib/librustdesk.so",)


def die(msg: str) -> None:
    print(f"ERREUR : {msg}", file=sys.stderr)
    sys.exit(1)


def run(*cmd: str) -> None:
    subprocess.run(cmd, check=True)


def retext(path: Path, low: str, display: str, extra=()) -> None:
    t = path.read_text(encoding="utf-8")
    for a, b in extra:
        t = t.replace(a, b)
    t = t.replace("RustDesk", display).replace(OLD, low)
    path.write_text(t, encoding="utf-8")


def set_field(control: str, field: str, value: str) -> str:
    new, n = re.subn(rf"^{field}:.*$", f"{field}: {value}", control, count=1, flags=re.M)
    if n == 0:
        die(f"champ « {field} » absent du fichier control d'origine")
    return new


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="supportdirect.toml")
    ap.add_argument("--deb", required=True, help="paquet .deb produit par build.py")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--skip-brand-check", action="store_true",
                    help="essais seulement : ne vérifie pas que le serveur et la clé sont dans le programme")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    app = cfg["app"]
    name, display = app["name"], app["display_name"]
    low = name.lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", low):
        die(f'app.name "{name}" ne donne pas un nom de paquet Debian valide')
    if low == OLD:
        die("app.name vaut « rustdesk » : rien à transformer")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        run("dpkg-deb", "-R", args.deb, str(root))
        share = root / "usr/share"

        # --- programme et ses fichiers
        (share / OLD).rename(share / low)
        appdir = share / low
        (appdir / OLD).rename(appdir / low)
        svc = appdir / "files/systemd" / f"{OLD}.service"
        svc = svc.rename(svc.with_name(f"{low}.service"))
        retext(svc, low, display)

        # --- lanceurs (menu des applications et liens <nom>://)
        apps = share / "applications"
        for f in sorted(apps.glob(f"{OLD}*.desktop")):
            f = f.rename(f.with_name(f.name.replace(OLD, low, 1)))
            retext(f, low, display, extra=(
                ("Comment=Remote Desktop", f"Comment={app['description']}"),))

        # --- icônes : celles de RustDesk sortent, celle du kit entre
        icons = share / "icons/hicolor"
        for f in icons.rglob(f"{OLD}.*"):
            f.unlink()
        shutil.rmtree(icons / "scalable", ignore_errors=True)
        src = Image.open(cfg_path.parent / cfg["branding"]["icon"]).convert("RGBA")
        if src.size[0] != src.size[1]:
            die("l'icône du kit doit être carrée")
        for s in ICON_SIZES:
            d = icons / f"{s}x{s}/apps"
            d.mkdir(parents=True, exist_ok=True)
            src.resize((s, s), Image.LANCZOS).save(d / f"{low}.png")

        # --- scripts d'installation et fiche du paquet
        deb = root / "DEBIAN"
        for script in ("preinst", "postinst", "prerm", "postrm"):
            if (deb / script).exists():
                retext(deb / script, low, display)
        files = sorted(p for p in root.rglob("*")
                       if p.is_file() and not p.is_symlink() and deb not in p.parents)
        size_kib = (sum(p.stat().st_size for p in files) + 1023) // 1024
        c = (deb / "control").read_text(encoding="utf-8")
        c = set_field(c, "Package", low)
        c = set_field(c, "Version", args.version)
        c = set_field(c, "Maintainer", app["company"])
        homepage = cfg.get("legal", {}).get("source_url") or "https://rustdesk.com"
        c = set_field(c, "Homepage", homepage)
        c = set_field(c, "Description", app["description"])
        c = re.sub(r"^Installed-Size:.*\n", "", c, flags=re.M)
        c = c.rstrip("\n") + f"\nInstalled-Size: {size_kib}\n"
        (deb / "control").write_text(c, encoding="utf-8")
        (deb / "md5sums").write_text("".join(
            f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n"
            for p in files), encoding="utf-8")

        # --- contrôles : plus aucun « rustdesk » dans les noms ni dans les textes
        left = [p.relative_to(root).as_posix() for p in root.rglob("*")
                if OLD in p.name.lower() and not p.as_posix().endswith(KEEP)]
        for p in [*deb.iterdir(), *apps.glob("*.desktop"), svc]:
            if p.name != "md5sums" and OLD in p.read_text(encoding="utf-8").replace(homepage, "").lower():
                left.append(f"{p.relative_to(root).as_posix()} (contenu)")
        if left:
            die("il reste des références à « rustdesk » : " + ", ".join(left))
        if not args.skip_brand_check:
            lib = (appdir / KEEP[0]).read_bytes()
            for label, value in (("nom", name), ("serveur", cfg["server"]["host"]), ("clé", cfg["server"]["key"])):
                if value.encode() not in lib:
                    die(f"le programme compilé ne contient pas le {label} « {value} » : "
                        "rebrand.py n'a pas été appliqué avant la compilation")

        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        # xz : lisible par toutes les distributions (le zstd par défaut d'Ubuntu ne l'est pas sur Debian ancien).
        run("dpkg-deb", "-Zxz", "--root-owner-group", "-b", str(root), str(out))
    print(f"Paquet créé : {out}")


if __name__ == "__main__":
    main()
