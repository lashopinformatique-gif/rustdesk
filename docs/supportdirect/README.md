# SupportDirect — kit de création de votre logiciel d'assistance à distance

SupportDirect est un client RustDesk (open source, AGPL-3.0) compilé à votre marque :
votre nom, votre logo, et votre serveur déjà configuré. Vos clients
téléchargent **SupportDirect-1.5.1-x86_64.exe**, l'ouvrent, vous lisent leur
identifiant et vous prenez la main. Aucun réglage de leur côté.

```
supportdirect/
├── README.md                      ← ce guide
├── server/                        ← serveur à installer sur un VPS (étape 1)
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
├── supportdirect-kit/                     ← personnalisation (étape 2)
│   ├── supportdirect.toml                 ← nom, société, serveur, clé
│   ├── branding/icon.png          ← VOTRE icône carrée (1024x1024)
│   ├── branding/logo.png          ← VOTRE logo horizontal (max 300x60)
│   ├── branding/company_logo.png  ← logo La Shop Informatique (page À propos)
│   └── rebrand.py                 ← applique tout ça aux sources
└── .github/workflows/
    └── supportdirect-windows.yml          ← compilation Windows sur GitHub (étape 3)
```

Le script a été testé sur RustDesk **1.5.1** (commit du 12 oct. 2026).

---

## Étape 1 — Le serveur (≈ 5 min)

Suivez `server/README.md`. À la fin vous avez :
- une adresse, ex. `supportdirect.votre-domaine.fr`
- une clé publique, ex. `aB3dEf…=`

## Étape 2 — Votre identité visuelle (≈ 10 min)

1. Remplacez `supportdirect-kit/branding/icon.png` par votre logo **carré** en PNG,
   fond transparent, 1024×1024 px. (Votre logo est déjà en place.)
2. Remplacez `supportdirect-kit/branding/logo.png` par votre logo **horizontal**
   (déjà en place, avec une variante claire et sombre). Optionnel : mettez
   `logo = ""` pour ne rien afficher.
3. Ouvrez `supportdirect-kit/supportdirect.toml` et renseignez :

   | Champ          | Exemple                           | Note |
   |----------------|-----------------------------------|------|
   | `name`         | `SupportDirect`                           | **sans accent** : sert de nom technique (service Windows, registre, dossier `C:\Program Files\SupportDirect`) |
   | `display_name` | `SupportDirect`                           | ce que voient les utilisateurs |
   | `company`      | `Dupont Informatique SARL`            | propriétés du .exe |
   | `host`         | `supportdirect.votre-domaine.fr`          | étape 1 |
   | `key`          | `aB3dEf…=`                        | étape 1 |

### Mentions légales (page « À propos »)

La section `[legal]` de `supportdirect.toml` contient le texte affiché dans
Paramètres → À propos, avec le logo La Shop Informatique à sa gauche :
copyright (l'année se met à jour seule), avis de propriété, composants tiers
et lien vers le code source. **Remplacez `source_url` par l'adresse de votre
fork GitHub** : c'est l'obligation principale de la licence AGPL. `website`
permet de faire pointer le lien « Site web » vers votre site.

Note : le texte diffère volontairement de celui de Forge. Forge est 100 %
votre code, vous pouvez en interdire la copie. SupportDirect est dérivé de
RustDesk (AGPL) : vous ne pouvez pas interdire la copie du *code*, mais vos
marques, votre logo, votre identité visuelle et l'accès à votre serveur
restent pleinement protégés, et c'est ce que dit le texte.

## Étape 3 — Compilation sur GitHub (≈ 1 h de machine, 0 € sur un dépôt public)

Compiler RustDesk demande Visual Studio, Rust, Flutter, vcpkg et ~1 h de
calcul. Plutôt que d'installer tout ça, on laisse GitHub le faire sur ses
machines Windows.

1. Créez un compte GitHub si besoin, puis **forkez** `rustdesk/rustdesk`
   (bouton "Fork" en haut à droite de https://github.com/rustdesk/rustdesk).
   Laissez le dépôt **public** : la compilation Windows est alors gratuite,
   et la licence AGPL vous impose de toute façon de publier vos sources.
2. Dans votre fork, ajoutez les fichiers du kit à la racine :
   - le dossier `supportdirect-kit/` complet
   - le fichier `.github/workflows/supportdirect-windows.yml`

   (Via l'interface web : "Add file → Upload files", ou avec git :
   `git clone <votre fork>`, copier, `git add . && git commit && git push`.)
3. Onglet **Actions** du fork → activez les workflows si demandé →
   **SupportDirect Windows** → **Run workflow**.
4. ~60 min plus tard, en bas de la page du run, section *Artifacts* :
   `SupportDirect-windows-x64.zip` contenant :
   - `SupportDirect-1.5.1-x86_64.exe` — l'installeur à donner à vos clients
   - `SupportDirect-1.5.1-x86_64.msi` — pour déploiement silencieux (`msiexec /i … /qn`)

Pour publier une version téléchargeable : créez un tag `supportdirect-1.5.1-1` sur
le fork, le workflow attache les fichiers à une *Release* GitHub.

### Si la compilation échoue

Le workflow est une copie allégée du workflow officiel de RustDesk 1.5.1 ;
GitHub, Flutter ou vcpkg évoluent, et un premier run peut buter sur un
détail. Dans ce cas ouvrez le job en rouge, copiez les 50 dernières lignes
du log et renvoyez-les-moi : c'est généralement un numéro de version à
ajuster. Vous pouvez aussi comparer avec le job `build-for-windows-flutter`
dans `.github/workflows/flutter-build.yml` du dépôt officiel.

---

## Utilisation au quotidien

- **Côté client** : il lance SupportDirect, vous dicte l'ID (9 chiffres) et le mot
  de passe affiché. Vous pouvez aussi l'installer (bouton "Installer") pour
  un accès permanent avec mot de passe fixe — pratique pour les clients
  réguliers.
- **Côté technicien** : vous utilisez le même SupportDirect (ou un RustDesk standard
  configuré sur votre serveur), onglet "Contrôler". Le carnet d'adresses
  local permet de garder vos clients.
- Fonctions incluses : contrôle total, transfert de fichiers, chat, TCP
  tunnel, redémarrage distant, écran noir côté client, multi-écrans,
  imprimante distante, affichage virtuel si le PC n'a pas d'écran.

## Mettre à jour SupportDirect plus tard

1. Dans votre fork, bouton **Sync fork** pour récupérer la nouvelle version
   RustDesk.
2. Mettez `VERSION` à jour dans `.github/workflows/supportdirect-windows.yml`
   (même valeur que `version =` dans `Cargo.toml`).
3. Relancez le workflow. Si `rebrand.py` signale "motif introuvable", le
   code a changé : envoyez-moi le message.

Les clients installés chez vos clients se mettent à jour en relançant le
nouvel installeur (ou via le MSI).

## Licence — à lire

RustDesk est sous **AGPL-3.0**. En distribuant SupportDirect vous devez :
- conserver la mention de licence et les crédits RustDesk dans "À propos"
  (le kit ne les retire pas) ;
- rendre vos sources modifiées accessibles — votre fork GitHub public
  suffit ;
- ne pas prétendre que SupportDirect est un logiciel propriétaire.

En revanche vous pouvez librement le distribuer sous votre nom, votre logo,
et facturer votre service d'assistance. Le nom "SupportDirect" et votre logo restent
votre propriété (marque), seul le code est AGPL.

## Ce que le kit ne fait pas (encore)

- **Signature de code Windows** : sans certificat, SmartScreen affichera
  "Éditeur inconnu" au premier lancement (clic "Informations
  complémentaires → Exécuter quand même"). Un certificat EV/OV (~200-400
  €/an) supprime l'avertissement ; je peux ajouter l'étape de signature au
  workflow quand vous en aurez un.
- **Mac / Linux / Android** : le workflow ne compile que Windows x64 comme
  demandé. Les autres plateformes se rajoutent sur le même modèle.
- **Console web / carnet d'adresses partagé / 2FA serveur** : réservés à
  RustDesk Server Pro (payant). Le serveur OSS suffit pour un atelier.
