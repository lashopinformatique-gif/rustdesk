# Serveur SupportDirect — installation

Le serveur est le point de rendez-vous entre vos clients et vous. Il ne voit
pas l'écran (tout est chiffré de bout en bout) : il met en relation et, si la
connexion directe est impossible, relaie le flux chiffré.

## Prérequis

- Un petit VPS Linux (1 vCPU, 1 Go de RAM suffisent, ~5 €/mois chez OVH,
  Hetzner, Scaleway…) avec une **IP publique fixe**.
- De préférence un sous-domaine qui pointe dessus, ex. `supportdirect.votre-domaine.fr`
  (enregistrement DNS de type A). Ça évite de recompiler le client si vous
  changez de serveur un jour.

## Installation (5 minutes)

```bash
# 1. Docker
curl -fsSL https://get.docker.com | sh

# 2. Fichiers du serveur
mkdir -p /opt/supportdirect && cd /opt/supportdirect
#    -> copiez ici docker-compose.yml et .env.example
cp .env.example .env
nano .env                      # SUPPORTDIRECT_HOST=supportdirect.votre-domaine.fr

# 3. Démarrage
docker compose up -d

# 4. Clé publique à mettre dans le client
cat data/id_ed25519.pub
```

La clé publique ressemble à `aB3dEf…=` (44 caractères). Copiez-la dans
`supportdirect-kit/supportdirect.toml`, champ `server.key`, avec `server.host` = votre domaine.

## Pare-feu

| Port  | Proto | Rôle                                   |
|-------|-------|----------------------------------------|
| 21115 | TCP   | test NAT                               |
| 21116 | TCP + UDP | annuaire / heartbeat (hbbs)        |
| 21117 | TCP   | relais (hbbr)                          |

```bash
ufw allow 21115:21117/tcp
ufw allow 21116/udp
```

Pensez aussi au pare-feu de l'hébergeur (groupe de sécurité OVH/Hetzner…).

## Vérifications

```bash
docker compose ps            # les deux conteneurs "running"
docker compose logs -f hbbs  # on doit voir "Key: ..." au démarrage
```

Depuis un client RustDesk standard (en attendant SupportDirect) : Paramètres →
Réseau → Serveur ID = votre domaine, Clé = la clé publique. Si l'ID s'affiche
en vert "Prêt", le serveur fonctionne.

## Sauvegarde

Le dossier `data/` contient la paire de clés. **Sauvegardez-le** : si vous la
perdez, tous les clients SupportDirect déjà installés chez vos clients refuseront le
nouveau serveur et il faudra recompiler.

## Mise à jour

```bash
cd /opt/supportdirect && docker compose pull && docker compose up -d
```
