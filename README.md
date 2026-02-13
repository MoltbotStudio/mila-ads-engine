# Mila Ads Engine V2

Pipeline automatisé de création de vidéos publicitaires IA pour l'application Mila.

## Installation

1. **Cloner le projet**
```bash
cd ~/.openclaw/workspace/apps/mila/ads-engine/
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Configuration des API keys**
Copier `.env` et ajouter vos clés API :
```bash
cp .env .env.local
# Éditer .env.local avec vos vraies clés
```

4. **Tester l'installation**
```bash
python studio_cli.py --help
```

## Utilisation rapide

### 1. Génération d'un briefing marketing
```bash
python studio_cli.py briefing
```

### 2. Création de hooks marketing
```bash
python studio_cli.py generate-hooks --style problem --count 5
```

### 3. Génération d'un script complet
```bash
python studio_cli.py generate-script outputs/hooks/hooks_*.json --actor alex --duration 30
```

### 4. Liste des acteurs disponibles
```bash
python studio_cli.py list-actors
```

### 5. Suivi du budget
```bash
python studio_cli.py budget show
```

## Pipeline complet (Phase 3)

```bash
# Pipeline automatique complet
python studio_cli.py full-pipeline \
  --hook-style problem \
  --actor sophie \
  --duration 30 \
  --format vertical \
  --template talking_head
```

## Structure du projet

```
apps/mila/ads-engine/
├── studio_cli.py          # CLI principal ✅
├── config.json            # Configuration acteurs/engines ✅
├── requirements.txt       # Dépendances Python ✅
├── .env                   # Template API keys ✅
├── README.md              # Documentation ✅
├── assets/
│   ├── actors/            # Portraits et profils acteurs ✅
│   ├── logo.png           # Logo Mila (TODO)
│   ├── backgrounds/       # Arrière-plans vidéo (TODO)
│   └── music/             # Musiques de fond (TODO)
├── outputs/
│   ├── hooks/             # Hooks marketing générés ✅
│   ├── scripts/           # Scripts complets ✅
│   ├── audio/             # Fichiers audio TTS (Phase 2)
│   ├── video_raw/         # Vidéos lip-sync brutes (Phase 2)
│   ├── video_final/       # Vidéos finales (Phase 3)
│   └── logs/              # Logs d'exécution ✅
└── templates/
    ├── talking_head.json      # Template simple ✅
    ├── split_screen.json      # Template split-screen ✅
    └── problem_solution.json  # Template transition ✅
```

## Commandes disponibles

### Phase 1 (Implémenté) ✅
- `briefing` - Analyse app depuis dna.json
- `generate-hooks` - Hooks marketing via Claude (simulé)
- `generate-script` - Scripts complets depuis hooks
- `list-actors` - Bibliothèque acteurs
- `budget` - Gestion budget et suivi coûts

### Phase 2 (À implémenter) 🚧
- `generate-audio` - TTS via Chatterbox/ElevenLabs
- `generate-video` - Lip-sync via Seedance 2.0/Kling
- `test-actor` - Vidéos test 5s

### Phase 3 (À implémenter) 🚧
- `post-prod` - Post-production FFmpeg
- `full-pipeline` - Pipeline automatique complet

## Configuration des acteurs

Chaque acteur possède :
- **Portrait** : Photo de base 512x512px
- **Profil JSON** : Métadonnées (âge, style, langues)
- **Échantillon vocal** : Pour clonage/matching TTS

Voir `assets/actors/alex/profile.json` pour un exemple complet.

## Formats supportés

- **Vertical (9:16)** : TikTok, Instagram Stories, YouTube Shorts
- **Carré (1:1)** : Instagram Feed, Facebook
- **Horizontal (16:9)** : YouTube, Facebook Video

## Naming convention

Format : `{app}_{hook-id}_{actor}_{lang}_{format}_v{n}.{ext}`

Exemples :
- `mila_001_alex_fr_vertical_v1.mp4`
- `mila_002_sophie_en_square_v2.mp4`

## Budget et coûts

Le système track automatiquement les coûts par service :
- **Claude** : ~$0.02 par hook
- **ElevenLabs** : ~$0.24/1000 caractères  
- **Seedance 2.0** : ~$0.12/seconde vidéo
- **Kling** : ~$0.08/seconde vidéo

Utilisez `--dry-run` sur toutes les commandes payantes pour tester.

## Développement

### Ajouter un nouvel acteur

1. Créer le dossier : `assets/actors/{actor_id}/`
2. Ajouter le portrait : `portrait.jpg` (512x512)
3. Créer le profil : `profile.json`
4. Mettre à jour `config.json`

### Ajouter un template FFmpeg

1. Créer le fichier : `templates/{template_name}.json`
2. Définir la commande FFmpeg et assets requis
3. Tester avec différents formats (vertical/carré/horizontal)

## Roadmap

- [x] **Phase 1** : CLI de base + génération hooks/scripts
- [ ] **Phase 2** : Audio TTS + Vidéo lip-sync  
- [ ] **Phase 3** : Post-production + Pipeline complet
- [ ] **Phase 4** : Interface web + API REST
- [ ] **Phase 5** : ML pour optimisation automatique

## Support

Pour questions ou bugs, créer un issue dans le repo Mission Control avec le tag `ads-engine`.