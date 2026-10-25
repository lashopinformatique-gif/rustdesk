#!/usr/bin/env python3
"""
rebrand.py - Applique la personnalisation SupportDirect sur une copie des sources RustDesk.

Usage :
    python3 rebrand.py --config supportdirect.toml --repo /chemin/vers/rustdesk

Le script est idempotent : on peut le relancer sans danger.
Il modifie :
  - libs/hbb_common/src/config.rs      (nom interne, serveur et clé par défaut)
  - src/lang/*.rs                      (textes affichés "RustDesk" -> nom affiché)
  - flutter/lib/desktop/widgets/tabbar_widget.dart (titre de la barre)
  - flutter/windows/runner/Runner.rc   (propriétés du .exe)
  - flutter/pubspec.yaml               (description)
  - icônes : res/*.png, res/icon.ico, res/tray-icon.ico,
             flutter/windows/runner/resources/app_icon.ico,
             flutter/assets/icon.png, flutter/assets/logo*.png
"""
import argparse
import re
import sys
import shutil
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

try:
    from PIL import Image
except ImportError:
    print("Pillow manquant : pip install pillow", file=sys.stderr)
    sys.exit(1)


def die(msg: str) -> None:
    print(f"ERREUR : {msg}", file=sys.stderr)
    sys.exit(1)


def sub_once(text: str, pattern: str, repl: str, label: str, flags=re.M) -> str:
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n == 0:
        die(f"motif introuvable pour {label} - le code source RustDesk a peut-être changé")
    return new


# ---------------------------------------------------------------- config.rs
def patch_config_rs(repo: Path, cfg: dict) -> None:
    p = repo / "libs/hbb_common/src/config.rs"
    if not p.exists():
        die(f"{p} introuvable : le sous-module hbb_common n'est pas initialisé "
            "(git submodule update --init --recursive)")
    t = p.read_text(encoding="utf-8")
    t = sub_once(t,
                 r'(pub static ref APP_NAME: RwLock<String> = RwLock::new\(")[^"]*("\.to_owned\(\)\);)',
                 rf'\g<1>{cfg["app"]["name"]}\g<2>', "APP_NAME")
    t = sub_once(t,
                 r'(pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[)[^\]]*(\];)',
                 rf'\g<1>"{cfg["server"]["host"]}"\g<2>', "RENDEZVOUS_SERVERS")
    t = sub_once(t,
                 r'(pub const RS_PUB_KEY: &str = ")[^"]*(";)',
                 rf'\g<1>{cfg["server"]["key"]}\g<2>', "RS_PUB_KEY")
    p.write_text(t, encoding="utf-8")
    print("  config.rs            OK  (APP_NAME, serveur, clé)")


# ---------------------------------------------------------------- src/lang/*.rs
_LANG_LINE = re.compile(r'^(\s*\(")((?:[^"\\]|\\.)*)(",\s*")((?:[^"\\]|\\.)*)("\),?\s*)$')


def patch_lang_files(repo: Path, cfg: dict) -> None:
    display = cfg["app"]["display_name"]
    n_files = n_lines = 0
    for p in sorted((repo / "src/lang").glob("*.rs")):
        is_en = p.name == "en.rs"
        out, changed = [], False
        for line in p.read_text(encoding="utf-8").splitlines(keepends=True):
            m = _LANG_LINE.match(line.rstrip("\n"))
            if m:
                pre, key, mid, val, post = m.groups()
                new_val = val
                if "RustDesk" in val:
                    new_val = val.replace("RustDesk", display)
                elif is_en and val == "" and "RustDesk" in key:
                    # en.rs : valeur vide = la clé est affichée telle quelle
                    new_val = key.replace("RustDesk", display)
                if new_val != val:
                    line = f"{pre}{key}{mid}{new_val}{post}\n"
                    changed = True
                    n_lines += 1
            out.append(line)
        if changed:
            p.write_text("".join(out), encoding="utf-8")
            n_files += 1
    print(f"  src/lang/*.rs        OK  ({n_lines} textes dans {n_files} fichiers)")


# ---------------------------------------------------------------- Flutter
def patch_flutter(repo: Path, cfg: dict) -> None:
    display = cfg["app"]["display_name"]
    p = repo / "flutter/lib/desktop/widgets/tabbar_widget.dart"
    t = p.read_text(encoding="utf-8")
    t2 = re.sub(r'(const Text\(\s*)"RustDesk"', rf'\g<1>"{display}"', t, count=1)
    if t2 == t and f'"{display}"' not in t:
        print("  tabbar_widget.dart   !!  titre non trouvé (non bloquant)")
    else:
        p.write_text(t2, encoding="utf-8")
        print("  tabbar_widget.dart   OK")

    p = repo / "flutter/pubspec.yaml"
    t = p.read_text(encoding="utf-8")
    t = sub_once(t, r'^description: .*$', f'description: {cfg["app"]["description"]}', "pubspec description")
    p.write_text(t, encoding="utf-8")
    print("  pubspec.yaml         OK")


# ---------------------------------------------------------------- Runner.rc
def patch_runner_rc(repo: Path, cfg: dict) -> None:
    p = repo / "flutter/windows/runner/Runner.rc"
    t = p.read_text(encoding="utf-8", errors="replace")
    a = cfg["app"]
    repl = {
        "CompanyName": a["company"],
        "FileDescription": a["description"],
        "ProductName": a["display_name"],
        "LegalCopyright": f"Copyright © {a['company']}. Logiciel dérivé de RustDesk (AGPL-3.0).",
        # Le workflow renomme le binaire compilé en <name>.exe avant l'empaquetage.
        "OriginalFilename": f"{a['name']}.exe",
    }
    for k, v in repl.items():
        v = v.replace('"', "'")
        t = sub_once(t, rf'(VALUE "{k}", )"[^"]*"( "\\0")', rf'\g<1>"{v}"\g<2>', f"Runner.rc {k}")
    p.write_text(t, encoding="utf-8")
    print("  Runner.rc            OK  (propriétés du .exe)")

    # Enveloppe auto-extractible (installeur) : mêmes propriétés
    p = repo / "libs/portable/Cargo.toml"
    t = p.read_text(encoding="utf-8")
    for k, v in (("LegalCopyright", repl["LegalCopyright"]),
                 ("ProductName", repl["ProductName"]),
                 ("FileDescription", repl["FileDescription"]),
                 ("OriginalFilename", repl["OriginalFilename"])):
        v = v.replace('"', "'")
        t = sub_once(t, rf'^{k} = ".*"$', f'{k} = "{v}"', f"portable {k}")
    p.write_text(t, encoding="utf-8")
    print("  portable/Cargo.toml  OK  (propriétés de l'installeur)")


# ---------------------------------------------------------------- icônes
def _square(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    if w == h:
        return img
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas


def _resize(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def patch_icons(repo: Path, cfg: dict, kit_dir: Path) -> None:
    b = cfg["branding"]
    icon_path = kit_dir / b["icon"]
    if not icon_path.exists():
        die(f"icône introuvable : {icon_path}")
    src = _square(Image.open(icon_path))
    if src.size[0] < 256:
        print(f"  !! icône de {src.size[0]}px : 1024px recommandé pour un rendu net")

    res = repo / "res"
    targets = {
        "icon.png": 1024, "32x32.png": 32, "64x64.png": 64,
        "128x128.png": 128, "128x128@2x.png": 256, "mac-icon.png": 1024,
    }
    for name, size in targets.items():
        _resize(src, size).save(res / name)

    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_frames = [_resize(src, s) for s in ico_sizes]
    for ico in (res / "icon.ico", res / "tray-icon.ico",
                repo / "flutter/windows/runner/resources/app_icon.ico"):
        ico.parent.mkdir(parents=True, exist_ok=True)
        ico_frames[-1].save(ico, format="ICO", sizes=[(s, s) for s in ico_sizes],
                            append_images=ico_frames[:-1])

    assets = repo / "flutter/assets"
    _resize(src, 512).save(assets / "icon.png")
    # icon.svg : on le remplace par une version SVG embarquant le PNG,
    # pour que le repli SVG affiche aussi votre icône.
    import base64, io
    buf = io.BytesIO(); _resize(src, 256).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    (assets / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 256 256" width="256" height="256">'
        f'<image width="256" height="256" xlink:href="data:image/png;base64,{b64}"/></svg>\n',
        encoding="utf-8")
    print("  icônes               OK  (res/*.png, *.ico, assets/icon.png, icon.svg)")

    for key, fname in (("logo", "logo.png"), ("logo_light", "logo_light.png"),
                       ("logo_dark", "logo_dark.png")):
        rel = b.get(key, "")
        if not rel:
            continue
        lp = kit_dir / rel
        if not lp.exists():
            die(f"logo introuvable : {lp}")
        img = Image.open(lp).convert("RGBA")
        w, h = img.size
        scale = min(300 / w, 60 / h, 4.0)  # tenir dans 300x60 (x2 pour écrans HiDPI)
        img = img.resize((max(1, int(w * scale * 2)), max(1, int(h * scale * 2))), Image.LANCZOS)
        img.save(assets / fname)
        print(f"  assets/{fname:<14} OK  (logo écran d'accueil)")


# ---------------------------------------------------------------- page "À propos"
_LEGAL_MARK = "// SUPPORTDIRECT-LEGAL"


def _dart_str(s: str) -> str:
    """Chaîne Dart simple-quote, sûre (échappe \\ ' $ et retours à la ligne)."""
    s = s.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")
    return "'" + s.replace("\r\n", "\n").replace("\n", "\\n") + "'"


def patch_about(repo: Path, cfg: dict, kit_dir: Path) -> None:
    legal = cfg.get("legal")
    if not legal:
        return
    p = repo / "flutter/lib/desktop/pages/desktop_setting_page.dart"
    t = p.read_text(encoding="utf-8")

    # logo de l'entreprise -> assets/company_logo.png
    logo_rel = cfg["branding"].get("company_logo", "")
    has_logo = False
    if logo_rel:
        lp = kit_dir / logo_rel
        if not lp.exists():
            die(f"logo d'entreprise introuvable : {lp}")
        img = Image.open(lp).convert("RGBA")
        if max(img.size) > 512:
            img.thumbnail((512, 512), Image.LANCZOS)
        img.save(repo / "flutter/assets/company_logo.png")
        has_logo = True

    copyright_ = legal["copyright"].replace("{year}", "${DateTime.now().year}")
    # "{year}" doit rester une interpolation Dart : on l'échappe après coup
    copyright_dart = _dart_str(copyright_).replace("\\${DateTime.now().year}", "${DateTime.now().year}")
    notice = _dart_str(legal.get("notice", "").strip())
    third = _dart_str(legal.get("third_party", "").strip())
    source_url = legal.get("source_url", "").strip()

    logo_widget = (
        "Image.asset('assets/company_logo.png', width: 96, height: 96, fit: BoxFit.contain,\n"
        "                        errorBuilder: (c, e, s) => const SizedBox.shrink())\n"
        "                    .marginOnly(right: 16),"
        if has_logo else ""
    )
    source_widget = (
        f"                          InkWell(\n"
        f"                              onTap: () => launchUrlString({_dart_str(source_url)}),\n"
        f"                              child: Text('Code source : {source_url}',\n"
        f"                                  style: const TextStyle(fontSize: 12, decoration: TextDecoration.underline))\n"
        f"                              .marginOnly(top: 6)),\n"
        if source_url else ""
    )
    block = f"""              {_LEGAL_MARK}
              Container(
                padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
                child: SelectionArea(
                    child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    {logo_widget}
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text({copyright_dart},
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text({notice},
                              style: const TextStyle(fontSize: 12)).marginOnly(top: 8),
                          Text({third},
                              style: const TextStyle(fontSize: 12)).marginOnly(top: 8),
{source_widget}                        ],
                      ),
                    ),
                  ],
                )),
              ).marginSymmetric(vertical: 4.0),
              // SUPPORTDIRECT-LEGAL-END
"""
    anchor = "              Container(\n                decoration: const BoxDecoration(color: Color(0xFF2c8cff)),"
    if _LEGAL_MARK in t:  # relance : on remplace le bloc existant
        t = re.sub(rf"              {re.escape(_LEGAL_MARK)}\n.*?// SUPPORTDIRECT-LEGAL-END\n", block, t, count=1, flags=re.S)
    else:
        if anchor not in t:
            die("page À propos : point d'insertion introuvable")
        t = t.replace(anchor, block + anchor, 1)

    website = legal.get("website", "").strip()
    if website:
        t = t.replace("launchUrlString('https://rustdesk.com');", f"launchUrlString({_dart_str(website)});", 1)
    p.write_text(t, encoding="utf-8")
    print("  À propos             OK  (mentions légales" + (" + logo" if has_logo else "") + ")")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="supportdirect.toml")
    ap.add_argument("--repo", required=True, help="dossier des sources RustDesk")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    kit_dir = cfg_path.parent
    repo = Path(args.repo).resolve()
    if not (repo / "Cargo.toml").exists():
        die(f"{repo} ne ressemble pas aux sources RustDesk (Cargo.toml absent)")

    name = cfg["app"]["name"]
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", name):
        die(f'app.name "{name}" invalide : lettres, chiffres, - et _ uniquement (pas d\'accent)')
    if cfg["server"]["key"].startswith("COLLEZ"):
        print("  !! server.key n'est pas renseignée : les clients demanderont la clé manuellement")

    print(f"Personnalisation « {cfg['app']['display_name']} » -> {repo}")
    patch_config_rs(repo, cfg)
    patch_lang_files(repo, cfg)
    patch_flutter(repo, cfg)
    patch_runner_rc(repo, cfg)
    patch_icons(repo, cfg, kit_dir)
    patch_about(repo, cfg, kit_dir)
    print("Terminé.")


if __name__ == "__main__":
    main()
