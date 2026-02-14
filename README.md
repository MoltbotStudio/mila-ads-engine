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

# Pour TTS ElevenLabs (optionnel)
ELEVENLABS_API_KEY=your_elevenlabs_key

# Pour génération vidéo fal.ai (requis pour Phase 2)
FAL_KEY=your_fal_ai_key

# Pour Claude API (optionnel - utilise mock sinon)
ANTHROPIC_API_KEY=your_anthropic_key
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

## Nouveautés Phase 2 & 3 ✅

### 6. Génération audio (TTS)
```bash
# Audio avec Chatterbox (gratuit)
python studio_cli.py generate-audio outputs/scripts/script_*.json

# Audio avec ElevenLabs (premium)
python studio_cli.py generate-audio outputs/scripts/script_*.json --engine elevenlabs
```

### 7. Génération vidéo lip-sync
```bash
# Vidéo avec Seedance 2.0 via fal.ai
python studio_cli.py generate-video outputs/audio/audio_*.wav sophie --format vertical

# Test rapide d'un acteur
python studio_cli.py test-actor sophie
```

### 8. Assemblage final (FFmpeg)
```bash
# Assemblage avec sous-titres, musique et logo
python studio_cli.py assemble outputs/video_raw/video_*.mp4 outputs/scripts/script_*.json

# Assemblage sans sous-titres
python studio_cli.py assemble outputs/video_raw/video_*.mp4 --no-subtitles
```

### 9. Pipeline complet automatisé
```bash
# Pipeline complet avec confirmation
python studio_cli.py full-pipeline "19h. Frigo vide." --actor sophie --confirm

# Test en mode dry-run (sans coûts)
python studio_cli.py full-pipeline "Test hook" --actor alex --dry-run
```

### 10. Validation setup
```bash
# Tester la configuration complète
python studio_cli.py test-setup
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
│   ├── audio/             # Fichiers audio TTS ✅ 
│   ├── video_raw/         # Vidéos lip-sync brutes ✅
│   ├── video_final/       # Vidéos finales ✅
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

### Phase 2 (Implémenté) ✅
- `generate-audio` - TTS via Chatterbox (mock) / ElevenLabs
- `generate-video` - Lip-sync via Seedance 2.0 (fal.ai)
- `test-actor` - Vidéos test 5s
- `test-setup` - Validation setup complet

### Phase 3 (Implémenté) ✅
- `assemble` - Post-production FFmpeg (subtitles + music + logo)
- `post-prod` - Alias pour assemble
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
- [x] **Phase 2** : Audio TTS + Vidéo lip-sync via fal.ai
- [x] **Phase 3** : Post-production FFmpeg + Pipeline complet
- [ ] **Phase 4** : Claude API intégration + vrais hooks/scripts
- [ ] **Phase 5** : Interface web + API REST
- [ ] **Phase 6** : ML pour optimisation automatique

## Notes Phase 2 Implementation

### TTS - Chatterbox vs ElevenLabs
- **Chatterbox** : Implémentation avec fallback mock (dependencies complexes)
- **ElevenLabs** : Implémentation complète avec API key
- **Usage** : Chatterbox par défaut (gratuit), ElevenLabs en premium

### Video - Seedance 2.0
- **API** : fal.ai client (fal-client package)
- **Features** : Lip-sync natif multilingue, 15-20s max
- **Input** : Portrait actor + audio TTS
- **Cost** : ~$0.12/seconde

### Post-production - FFmpeg
- **Features** : Sous-titres, logo overlay, background music
- **Templates** : talking_head, split_screen, problem_solution
- **Formats** : vertical (9:16), square (1:1), horizontal (16:9)

## Support

Pour questions ou bugs, créer un issue dans le repo Mission Control avec le tag `ads-engine`.