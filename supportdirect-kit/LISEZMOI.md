# SupportDirect : fabrication et publication

SupportDirect est RustDesk (AGPL-3.0) renommé et mis à la marque de
La Shop Informatique. Ce dossier contient la personnalisation :

- `supportdirect.toml` : nom, textes légaux, adresse et clé publique du serveur ;
- `branding/` : icône (bouée) et logos ;
- `rebrand.py` : applique tout ça aux sources avant la compilation.

La compilation se fait sur GitHub, par `.github/workflows/supportdirect-windows.yml`.

## Publier une nouvelle version

1. **Augmenter la version** : ligne `VERSION:` en haut du workflow (ex. `1.5.3` → `1.5.4`).
2. **Envoyer le correctif sur `master`.** La fabrication démarre toute seule
   (environ 45 minutes). Un envoi plus récent annule la fabrication en cours.
3. **Tester le brouillon** : page *Releases* du dépôt, version marquée *Draft*.
   Elle est invisible pour les clients.
4. **Publier** : bouton *Edit* du brouillon, puis *Publish release*. GitHub crée
   l'étiquette `supportdirect-<version>`, et le lien « toujours la dernière version »
   pointe vers ces fichiers. Rien n'est recompilé : le fichier publié est celui
   qui a été testé.

Si `VERSION` n'a pas été augmentée et que cette version est déjà publiée, la
fabrication réussit, mais aucun brouillon n'est créé et la version publiée n'est
pas touchée. Les fichiers restent disponibles dans les artefacts de l'exécution.

Liens permanents pour les clients :
- dernière version : https://github.com/lashopinformatique-gif/rustdesk/releases/latest
- une version précise : `https://github.com/lashopinformatique-gif/rustdesk/releases/download/supportdirect-<version>/SupportDirect-<version>-x86_64.exe`

## Le nom de l'exécutable doit être `SupportDirect.exe`

Flutter compile toujours le programme sous le nom `rustdesk.exe`. Or tout le code
d'installation de RustDesk (raccourcis, service Windows, registre, pare-feu,
désinstallation) et la détection « déjà installé » utilisent `<name>.exe`, où
`name` vient de `supportdirect.toml`. Le workflow renomme donc le programme avant
de fabriquer l'installeur et le MSI (étape « Rename executable to the app name »).

Sans ce renommage (versions 1.5.2 et antérieures), le raccourci du bureau pointe
vers un fichier inexistant et l'application reste en mode portable. Installer la
1.5.3 ou une version plus récente par-dessus répare un poste touché : l'installation
retire d'abord l'ancienne.

## Serveur

Le serveur SupportDirect (annuaire `hbbs` et relais `hbbr`) tourne sur le VPS de
Gestion d'atelier, dans `/opt/supportdirect`. Si sa clé change, il faut mettre la
nouvelle clé publique dans `supportdirect.toml` (`[server] key`) et republier
le client.
