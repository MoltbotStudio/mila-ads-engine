#!/usr/bin/env python3
"""
Studio CLI - Mila Ads Engine V2
Pipeline automatisé de création de vidéos publicitaires IA
"""

import os
import json
import uuid
import typer
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests

# Anthropic SDK for Claude API
import anthropic

# Load .env file explicitly for API keys
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                if key not in os.environ:  # Don't override existing env vars
                    os.environ[key] = value.strip('"\'')

anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
ANTHROPIC_AVAILABLE = True
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print as rprint

# Initialize
app = typer.Typer(help="Mila Ads Engine - Studio CLI V2")
console = Console()

# Constants
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
# Try multiple locations for dna.json
DNA_FILES = [
    Path("/Users/moltbotstudio/.openclaw/workspace/apps/mila/dna.json"),
    BASE_DIR.parent / "dna.json",
    BASE_DIR / "dna.json"
]

def get_dna_file():
    """Find dna.json file in possible locations"""
    for dna_path in DNA_FILES:
        if dna_path.exists():
            return dna_path
    return None 
OUTPUTS_DIR = BASE_DIR / "outputs"
ASSETS_DIR = BASE_DIR / "assets"
ENV_FILE = BASE_DIR / ".env"

class StudioConfig:
    """Configuration manager"""
    
    def __init__(self):
        self.config = self._load_config()
        self.env = self._load_env()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        if not CONFIG_FILE.exists():
            console.print(f"❌ Configuration file not found: {CONFIG_FILE}", style="red")
            raise typer.Exit(1)
        
        with open(CONFIG_FILE) as f:
            return json.load(f)
    
    def _load_env(self) -> Dict[str, str]:
        """Load environment variables from .env"""
        env = {}
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env[key] = value.strip('"\'')
        return env
    
    def get_actor(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get actor configuration"""
        return self.config.get("actors", {}).get(actor_id)
    
    def list_actors(self) -> Dict[str, Dict[str, Any]]:
        """List all actors"""
        return self.config.get("actors", {})

class BudgetTracker:
    """Budget and expense tracking"""
    
    def __init__(self):
        self.expenses_file = OUTPUTS_DIR / "expenses.json"
        self.expenses = self._load_expenses()
    
    def _load_expenses(self) -> Dict[str, Any]:
        """Load expense history"""
        if self.expenses_file.exists():
            with open(self.expenses_file) as f:
                return json.load(f)
        return {
            "total_spent": 0.0,
            "monthly_spent": 0.0,
            "transactions": []
        }
    
    def add_expense(self, service: str, cost: float, description: str = ""):
        """Add an expense"""
        transaction = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "cost": cost,
            "description": description
        }
        
        self.expenses["transactions"].append(transaction)
        self.expenses["total_spent"] += cost
        self.expenses["monthly_spent"] += cost  # Simplified - should track by month
        
        self._save_expenses()
        
        # Check budget limits
        config = get_config().config
        monthly_limit = config.get("budget", {}).get("monthly_limit", 100.0)
        if self.expenses["monthly_spent"] > monthly_limit:
            console.print(f"⚠️  Monthly budget exceeded! Spent: ${self.expenses['monthly_spent']:.2f} / ${monthly_limit:.2f}", style="yellow")
    
    def _save_expenses(self):
        """Save expenses to file"""
        OUTPUTS_DIR.mkdir(exist_ok=True)
        with open(self.expenses_file, 'w') as f:
            json.dump(self.expenses, f, indent=2)

# Initialize global instances  
config = None
budget_tracker = None

def get_config():
    global config
    if config is None:
        config = StudioConfig()
    return config

def get_budget():
    global budget_tracker
    if budget_tracker is None:
        budget_tracker = BudgetTracker()
    return budget_tracker

def generate_file_id() -> str:
    """Generate unique file ID"""
    return f"{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}"

def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
    """Call Claude API with error handling"""
    if not ANTHROPIC_AVAILABLE:
        raise Exception("Anthropic SDK not installed. Run: pip3 install anthropic")
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not found in environment")
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
    except anthropic.RateLimitError as e:
        raise Exception(f"Claude API rate limit exceeded: {e}")
    except anthropic.AuthenticationError as e:
        raise Exception(f"Claude API authentication failed: {e}")
    except Exception as e:
        raise Exception(f"Claude API error: {e}")

@app.command()
def briefing(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path")
) -> None:
    """Generate marketing brief from dna.json"""
    
    dna_file = get_dna_file()
    if dna_file is None:
        console.print(f"❌ DNA file not found. Searched in:", style="red")
        for path in DNA_FILES:
            console.print(f"  - {path}", style="red")
        raise typer.Exit(1)
    
    console.print(f"📖 Loading DNA from: {dna_file}", style="blue")
    
    # Load DNA
    with open(dna_file) as f:
        dna = json.load(f)
    
    # Generate briefing
    brief = {
        "id": generate_file_id(),
        "timestamp": datetime.now().isoformat(),
        "app": dna.get("app", {}),
        "problem": dna.get("problem", {}),
        "solution": dna.get("solution", {}),
        "target": dna.get("target", {}),
        "tone": dna.get("tone", {}),
        "proof": dna.get("proof", {}),
        "cta": dna.get("cta", {}),
        "marketing_angles": {
            "problem": dna.get("problem", {}).get("emotional_triggers", []),
            "solution": dna.get("solution", {}).get("differentiators", []),
            "target_audience": dna.get("target", {}).get("primary", ""),
            "tone": dna.get("tone", {}).get("voice", "")
        }
    }
    
    # Output
    if output is None:
        output = OUTPUTS_DIR / "briefing.json"
    
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    
    console.print(f"✅ Briefing generated: {output}", style="green")
    
    # Display summary
    table = Table(title="Marketing Brief Summary")
    table.add_column("Element", style="cyan")
    table.add_column("Content", style="white")
    
    table.add_row("App", brief["app"].get("name", ""))
    table.add_row("Tagline", brief["app"].get("tagline", ""))
    table.add_row("Target", brief["target"].get("primary", ""))
    table.add_row("Key Problems", str(len(brief["problem"].get("emotional_triggers", []))))
    table.add_row("Differentiators", str(len(brief["solution"].get("differentiators", []))))
    
    console.print(table)

@app.command()
def generate_hooks(
    count: int = typer.Option(3, "--count", "-c", help="Number of hooks to generate (1-10)", min=1, max=10),
    style: str = typer.Option("problem", "--style", "-s", help="Hook style: problem, solution, curiosity, all"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save hooks to outputs/hooks/"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Specific output file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls")
) -> None:
    """Generate marketing hooks using Claude AI"""
    
    # Validate style
    valid_styles = ["problem", "solution", "curiosity", "all"]
    if style not in valid_styles:
        console.print(f"❌ Invalid style. Choose from: {', '.join(valid_styles)}", style="red")
        raise typer.Exit(1)
    
    # Load briefing
    briefing_file = OUTPUTS_DIR / "briefing.json"
    if not briefing_file.exists():
        console.print("❌ No briefing found. Run 'briefing' command first.", style="red")
        raise typer.Exit(1)
    
    with open(briefing_file) as f:
        brief = json.load(f)
    
    if dry_run:
        console.print("🔍 [DRY RUN] Simulating hook generation...", style="blue")
        hooks = {
            "id": generate_file_id(),
            "timestamp": datetime.now().isoformat(),
            "style": style,
            "count": count,
            "hooks": [
                {
                    "id": f"hook_{i:03d}",
                    "text": f"[SIMULATED] Hook #{i} for {style} style targeting {brief.get('target', {}).get('primary', 'parents')}",
                    "style": style,
                    "estimated_duration": 30,
                    "call_to_action": "Télécharge Mila maintenant!"
                } for i in range(1, count + 1)
            ]
        }
    else:
        # Call Claude API for real hook generation
        console.print("🤖 Generating hooks with Claude AI...", style="blue")
        
        system_prompt = """Tu es un copywriter expert marketing. Génère des hooks accrocheurs pour une app de meal planning IA appelée Mila.

Règles:
- Les hooks doivent être courts (5-15 mots idéalement, max 20 mots)
- Style authentique, comme une amie qui partage une solution
- Évite les superlatifs ("révolutionnaire", "magique", "incroyable")
- Préfère les mots simples: "Simple", "Concret", "Vrai", "Enfin", "Libérée"
- Cible: parents actifs avec enfants à la maison (28-45 ans, principalement mamans)
- Ton: bienveillant, pragmatique, un peu imparfait, honnête

Retourne UNIQUEMENT un JSON valide avec ce format exact:
{
  "hooks": [
    {"id": "hook_001", "text": "...", "estimated_duration": 5, "call_to_action": "Essaie gratuitement", "style": "problem"},
    ...
  ]
}"""
        
        user_prompt = f"""Génère {count} hooks de style '{style}' pour Mila.

Style '{style}' signifie:
""" + {
            "problem": "Accroche sur la douleur/problème (ex: 'Marre de jeter de la nourriture ?')",
            "solution": "Met en avant la solution/bénéfice (ex: '2 minutes pour planifier tes repas')",
            "curiosity": "Créer de la curiosité/intrigue (ex: 'Ce que les parents organisés font différemment')",
            "all": "Un mix de problème, solution et curiosité"
        }.get(style, "problem") + f"""

Contexte Mila:
- Tagline: "{brief['app'].get('tagline', 'Tes repas de la semaine en 2 minutes')}"
- Problème principal: {brief['problem'].get('main', 'Le stress des repas')}
- Public cible: {brief['target'].get('primary', 'Parents actifs')}
- Ton: {brief['tone'].get('voice', 'Une amie maman bienveillante')}

Génère {count} hooks, tous différents, en français."""
        
        try:
            claude_response = call_claude(system_prompt, user_prompt, max_tokens=2000)
            
            # Parse JSON from Claude response
            import re
            json_match = re.search(r'\{.*\}', claude_response, re.DOTALL)
            if json_match:
                claude_hooks = json.loads(json_match.group(0))
            else:
                claude_hooks = json.loads(claude_response)
            
            hooks = {
                "id": generate_file_id(),
                "timestamp": datetime.now().isoformat(),
                "style": style,
                "count": count,
                "hooks": claude_hooks.get("hooks", [])
            }
            
            # Ensure all hooks have required fields
            for i, hook in enumerate(hooks["hooks"], 1):
                hook.setdefault("id", f"hook_{i:03d}")
                hook.setdefault("style", style)
                hook.setdefault("estimated_duration", 5)
                hook.setdefault("call_to_action", brief['cta'].get('primary', 'Essaie gratuitement'))
            
            console.print(f"✅ Generated {len(hooks['hooks'])} hooks using Claude", style="green")
            
            # Track expense (~$0.005 per hook)
            estimated_cost = 0.005 + (count * 0.002)
            get_budget().add_expense("claude", estimated_cost, f"Generated {count} hooks")
            
        except Exception as e:
            console.print(f"❌ Claude API failed: {e}", style="red")
            raise typer.Exit(1)
    
    # Save hooks
    if save or output:
        if output is None:
            hooks_dir = OUTPUTS_DIR / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            output = hooks_dir / f"hooks_{hooks['id']}.json"
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(hooks, f, indent=2, ensure_ascii=False)
        
        console.print(f"✅ Hooks saved: {output}", style="green")
    
    # Display hooks
    table = Table(title=f"Generated Hooks ({style} style)")
    table.add_column("ID", style="cyan")
    table.add_column("Hook Text", style="white", max_width=60)
    table.add_column("CTA", style="green", max_width=25)
    
    for hook in hooks["hooks"]:
        table.add_row(
            hook["id"],
            hook["text"],
            hook["call_to_action"]
        )
    
    console.print(table)

@app.command()
def generate_script(
    hook_file: Optional[Path] = typer.Argument(None, help="Hook JSON file (optional if using --hook-id)"),
    hook_id: Optional[str] = typer.Option(None, "--hook-id", "-h", help="Hook ID to look up from recent hooks"),
    actor: Optional[str] = typer.Option(None, "--actor", "-a", help="Actor ID (auto-select if not specified)"),
    duration: int = typer.Option(30, "--duration", "-d", help="Script duration in seconds (15|30|60)"),
    fillers: bool = typer.Option(True, "--fillers/--no-fillers", help="Add natural fillers"),
    lang: str = typer.Option("fr", "--lang", "-l", help="Language (fr|en|es)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output script file"),
    use_claude: bool = typer.Option(True, "--claude/--no-claude", help="Use Claude AI for script generation")
) -> None:
    """Generate complete script from hook"""
    
    # Find hook - either from file or by ID
    hook_data = None
    
    if hook_file and hook_file.exists():
        with open(hook_file, encoding='utf-8') as f:
            hook_data = json.load(f)
    elif hook_id:
        # Look up hook by ID from hooks directory
        hooks_dir = OUTPUTS_DIR / "hooks"
        if hooks_dir.exists():
            for hooks_file in hooks_dir.glob("hooks_*.json"):
                with open(hooks_file, encoding='utf-8') as f:
                    data = json.load(f)
                    for hook in data.get("hooks", []):
                        if hook.get("id") == hook_id:
                            hook_data = {"hooks": [hook]}
                            hook_file = hooks_file
                            console.print(f"✅ Found hook {hook_id} in {hooks_file.name}", style="green")
                            break
                    if hook_data:
                        break
        
        if not hook_data:
            console.print(f"❌ Hook ID not found: {hook_id}", style="red")
            raise typer.Exit(1)
    else:
        console.print("❌ Please provide either a hook file or --hook-id", style="red")
        raise typer.Exit(1)
    
    if duration not in [15, 30, 60]:
        console.print("❌ Duration must be 15, 30, or 60 seconds", style="red")
        raise typer.Exit(1)
    
    if lang not in ["fr", "en", "es"]:
        console.print("❌ Language must be fr, en, or es", style="red")
        raise typer.Exit(1)
    
    # Load hook
    with open(hook_file, encoding='utf-8') as f:
        hook_data = json.load(f)
    
    # Auto-select actor if not specified
    if actor is None:
        # Simple heuristic based on hook style and language
        actors = list(get_config().list_actors().keys())
        actor = actors[0] if actors else "alex"  # Default fallback
        console.print(f"🎭 Auto-selected actor: {actor}", style="blue")
    
    # Validate actor
    actor_config = get_config().get_actor(actor)
    if actor_config is None:
        console.print(f"❌ Actor '{actor}' not found", style="red")
        raise typer.Exit(1)
    
    # Check if actor supports language
    if lang not in actor_config.get("languages", ["fr"]):
        console.print(f"⚠️  Actor '{actor}' doesn't support '{lang}', using default", style="yellow")
        lang = actor_config.get("default_language", "fr")
    
    # Select hook (use first one if multiple)
    if "hooks" in hook_data:
        selected_hook = hook_data["hooks"][0]  # Take first hook
    else:
        selected_hook = hook_data  # Single hook format
    
    # Generate script structure
    script = {
        "id": generate_file_id(),
        "timestamp": datetime.now().isoformat(),
        "hook_id": selected_hook.get("id", "unknown"),
        "hook_text": selected_hook.get("text", ""),
        "actor": actor,
        "actor_config": actor_config,
        "language": lang,
        "duration": duration,
        "script_sections": []
    }
    
    # Load DNA for context
    dna_file = get_dna_file()
    dna = {}
    if dna_file:
        with open(dna_file) as f:
            dna = json.load(f)
    
    if use_claude:
        console.print("🤖 Generating script with Claude AI...", style="blue")
        
        system_prompt = """Tu es un copywriter expert en scripts vidéo publicitaires. Tu crées des scripts engageants pour des vidéos de 15, 30 ou 60 secondes.

Règles:
- Style conversationnel, naturel, comme parler à une amie
- Ton: bienveillant, pragmatique, un peu imparfait, honnête
- Évite les superlatifs ("magique", "incroyable", "révolutionnaire")
- Utilise les mots simples: "Simple", "Concret", "Vrai", "Enfin", "Libérée"
- Chaque section doit avoir un timing réaliste en secondes
- La CTA finale doit être claire et actionnable

Retourne UNIQUEMENT un JSON valide avec ce format:
{
  "script_sections": [
    {"section": "hook", "text": "...", "duration": 5, "tone": "engaging"},
    {"section": "problem", "text": "...", "duration": 7, "tone": "relatable"},
    {"section": "solution", "text": "...", "duration": 10, "tone": "confident"},
    {"section": "cta", "text": "...", "duration": 5, "tone": "urgent"}
  ]
}

Les sections possibles selon la durée:
- 15s: hook + cta
- 30s: hook + problem + solution + cta
- 60s: hook + problem_intro + problem_detail + solution + benefits + cta

Les tons valides: engaging, relatable, confident, urgent, thoughtful, excited"""

        user_prompt = f"""Génère un script publicitaire de {duration} secondes.

Hook de départ: "{selected_hook.get('text', '')}"

Contexte Mila:
- App: {dna.get('app', {}).get('name', 'Mila')} - {dna.get('app', {}).get('tagline', 'Tes repas de la semaine en 2 minutes')}
- Problème principal: {dna.get('problem', {}).get('main', 'Le stress des repas')}
- Problèmes secondaires: {', '.join(dna.get('problem', {}).get('secondary', [])[:2])}
- Solutions clés: {', '.join([f['name'] for f in dna.get('solution', {}).get('key_features', [])[:2]])}
- Bénéfices: {dna.get('solution', {}).get('core_value', 'Libérer de la charge mentale')}
- CTA: {selected_hook.get('call_to_action', 'Essaie gratuitement')}

Acteur "{actor}": {actor_config.get('name', 'Sophie')}, âge {actor_config.get('age_range', '30-35')}, persona: {actor_config.get('persona', 'Maman bienveillante')}
Langue: {lang}

Timing total exact: {duration} secondes. Distribue les timings entre les sections pour atte exactement {duration}s."""
        
        try:
            claude_response = call_claude(system_prompt, user_prompt, max_tokens=2000)
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', claude_response, re.DOTALL)
            if json_match:
                claude_script = json.loads(json_match.group(0))
            else:
                claude_script = json.loads(claude_response)
            
            script["script_sections"] = claude_script.get("script_sections", [])
            
            # Validate timing
            total_duration = sum(s.get("duration", 0) for s in script["script_sections"])
            if total_duration != duration:
                console.print(f"⚠️  Timing adjusted: {total_duration}s → {duration}s", style="yellow")
                # Simple adjustment - scale to target duration
                if total_duration > 0:
                    ratio = duration / total_duration
                    for section in script["script_sections"]:
                        section["duration"] = round(section.get("duration", 5) * ratio)
            
            console.print(f"✅ Script generated with Claude ({len(script['script_sections'])} sections)", style="green")
            
            # Track expense
            get_budget().add_expense("claude", 0.01, f"Script generation for {duration}s")
            
        except Exception as e:
            console.print(f"❌ Claude API failed: {e}", style="red")
            raise typer.Exit(1)
    
    if not use_claude:
        # Fallback template-based generation
        console.print("📝 Using template script generation...", style="blue")
        
    # Generate script content based on duration (fallback or if Claude skipped)
    if not script["script_sections"]:
        # Short format: Hook + CTA
        script["script_sections"] = [
            {
                "section": "hook",
                "text": selected_hook.get("text", ""),
                "duration": 10,
                "tone": "engaging"
            },
            {
                "section": "cta", 
                "text": selected_hook.get("call_to_action", "Télécharge Mila maintenant!"),
                "duration": 5,
                "tone": "urgent"
            }
        ]
    elif duration == 30:
        # Medium format: Hook + Problem + Solution + CTA
        script["script_sections"] = [
            {
                "section": "hook",
                "text": selected_hook.get("text", ""),
                "duration": 8,
                "tone": "engaging"
            },
            {
                "section": "problem",
                "text": f"Tu connais ce moment où tu perds du temps sur des tâches répétitives?",
                "duration": 7,
                "tone": "relatable"
            },
            {
                "section": "solution", 
                "text": f"Avec Mila, ton assistant IA personnel, fini la perte de temps!",
                "duration": 10,
                "tone": "confident"
            },
            {
                "section": "cta",
                "text": selected_hook.get("call_to_action", "Télécharge Mila maintenant!"),
                "duration": 5,
                "tone": "urgent"
            }
        ]
    else:  # 60 seconds
        # Long format: Full story arc
        script["script_sections"] = [
            {
                "section": "hook",
                "text": selected_hook.get("text", ""),
                "duration": 10,
                "tone": "engaging"
            },
            {
                "section": "problem_intro",
                "text": "Chaque jour, nous perdons des heures sur des tâches qui pourraient être automatisées.",
                "duration": 12,
                "tone": "thoughtful"
            },
            {
                "section": "problem_detail",
                "text": "Emails, planification, recherches... Ces petites tâches s'accumulent et nous épuisent.",
                "duration": 13,
                "tone": "relatable"
            },
            {
                "section": "solution",
                "text": "C'est exactement pourquoi nous avons créé Mila - ton assistant IA qui comprend tes besoins.",
                "duration": 15,
                "tone": "confident"
            },
            {
                "section": "benefits",
                "text": "Plus intelligent, plus rapide, et surtout... il apprend de toi pour devenir encore plus utile.",
                "duration": 7,
                "tone": "excited"
            },
            {
                "section": "cta",
                "text": selected_hook.get("call_to_action", "Télécharge Mila maintenant et reprends le contrôle de ton temps!"),
                "duration": 3,
                "tone": "urgent"
            }
        ]
    
    # Add natural fillers if requested
    if fillers:
        for section in script["script_sections"]:
            if section["tone"] in ["engaging", "relatable"]:
                section["fillers"] = ["euh", "tu vois", "en fait"]
            elif section["tone"] == "thoughtful":
                section["fillers"] = ["alors", "effectivement", "donc"]
    
    # Calculate total script text
    full_text = " ".join([section["text"] for section in script["script_sections"]])
    script["full_text"] = full_text
    script["word_count"] = len(full_text.split())
    script["estimated_speech_duration"] = len(full_text.split()) / 2.5  # ~150 words/minute
    
    # Save script
    if output is None:
        scripts_dir = OUTPUTS_DIR / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        output = scripts_dir / f"script_{script['id']}.json"
    
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
    
    console.print(f"✅ Script generated: {output}", style="green")
    
    # Display script summary
    table = Table(title=f"Script Summary ({duration}s)")
    table.add_column("Section", style="cyan")
    table.add_column("Text", style="white", max_width=50)
    table.add_column("Duration", style="green")
    table.add_column("Tone", style="yellow")
    
    for section in script["script_sections"]:
        table.add_row(
            section["section"],
            section["text"][:50] + "..." if len(section["text"]) > 50 else section["text"],
            f"{section['duration']}s",
            section["tone"]
        )
    
    console.print(table)
    console.print(f"📊 Total: {script['word_count']} words, ~{script['estimated_speech_duration']:.1f}s speech", style="blue")

@app.command()
def list_actors(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table|json")
) -> None:
    """List available actors"""
    
    actors = get_config().list_actors()
    
    if format == "json":
        print(json.dumps(actors, indent=2))
    else:
        table = Table(title="Available Actors")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Age", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("Languages", style="blue")
        table.add_column("Persona", style="magenta", max_width=30)
        
        for actor_id, actor in actors.items():
            table.add_row(
                actor_id,
                actor["name"],
                actor["age_range"],
                actor["category"],
                ", ".join(actor["languages"]),
                actor["persona"]
            )
        
        console.print(table)

@app.command()
def budget(
    action: str = typer.Argument("show", help="Action: show|set|reset|export"),
    amount: Optional[float] = typer.Argument(None, help="Amount for 'set' action"),
    export_file: Optional[Path] = typer.Option(None, "--file", "-f", help="Export file for 'export' action")
) -> None:
    """Manage budget and track expenses"""
    
    if action == "show":
        # Show current budget status
        config_budget = get_config().config.get("budget", {})
        monthly_limit = config_budget.get("monthly_limit", 100.0)
        budget = get_budget()
        
        table = Table(title="Budget Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Status", style="green")
        
        table.add_row(
            "Monthly Limit",
            f"${monthly_limit:.2f}",
            "✅"
        )
        table.add_row(
            "Current Spent",
            f"${budget.expenses['monthly_spent']:.2f}",
            "⚠️" if budget.expenses['monthly_spent'] > monthly_limit else "✅"
        )
        table.add_row(
            "Remaining",
            f"${monthly_limit - budget.expenses['monthly_spent']:.2f}",
            "❌" if budget.expenses['monthly_spent'] > monthly_limit else "✅"
        )
        table.add_row(
            "Total Transactions",
            str(len(budget.expenses['transactions'])),
            "📊"
        )
        
        console.print(table)
        
        # Show recent transactions
        if budget.expenses['transactions']:
            recent = budget.expenses['transactions'][-5:]  # Last 5
            trans_table = Table(title="Recent Transactions")
            trans_table.add_column("Date", style="cyan")
            trans_table.add_column("Service", style="white")
            trans_table.add_column("Cost", style="green")
            trans_table.add_column("Description", style="yellow")
            
            for trans in recent:
                date = datetime.fromisoformat(trans['timestamp']).strftime("%Y-%m-%d %H:%M")
                trans_table.add_row(
                    date,
                    trans['service'],
                    f"${trans['cost']:.3f}",
                    trans['description'][:30] + "..." if len(trans['description']) > 30 else trans['description']
                )
            
            console.print(trans_table)
    
    elif action == "set":
        if amount is None:
            console.print("❌ Amount required for 'set' action", style="red")
            raise typer.Exit(1)
        
        # Update config file
        with open(CONFIG_FILE) as f:
            config_data = json.load(f)
        
        config_data.setdefault("budget", {})["monthly_limit"] = amount
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        console.print(f"✅ Monthly budget limit set to ${amount:.2f}", style="green")
    
    elif action == "reset":
        # Reset monthly spending (keep history)
        budget = get_budget()
        budget.expenses["monthly_spent"] = 0.0
        budget._save_expenses()
        console.print("✅ Monthly spending reset to $0.00", style="green")
    
    elif action == "export":
        if export_file is None:
            export_file = OUTPUTS_DIR / f"expenses_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Export to CSV
        import csv
        budget = get_budget()
        with open(export_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Service", "Cost", "Description", "Transaction ID"])
            
            for trans in budget.expenses['transactions']:
                writer.writerow([
                    trans['timestamp'],
                    trans['service'],
                    trans['cost'],
                    trans['description'],
                    trans['id']
                ])
        
        console.print(f"✅ Expenses exported to: {export_file}", style="green")
    
    else:
        console.print(f"❌ Unknown action: {action}. Use: show|set|reset|export", style="red")
        raise typer.Exit(1)

# Placeholder commands for Phase 2 & 3
@app.command()
def generate_audio(
    script_file: Path = typer.Argument(..., help="Script JSON file"),
    engine: str = typer.Option("chatterbox", "--engine", "-e", help="TTS engine: chatterbox|elevenlabs"),
    stability: float = typer.Option(0.5, "--stability", "-s", help="Voice stability (0.0-1.0)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output audio file")
) -> None:
    """Generate audio from script (TTS)"""
    
    # Validate inputs
    if not script_file.exists():
        console.print(f"❌ Script file not found: {script_file}", style="red")
        raise typer.Exit(1)
    
    if engine not in ["chatterbox", "elevenlabs"]:
        console.print("❌ Engine must be 'chatterbox' or 'elevenlabs'", style="red")
        raise typer.Exit(1)
    
    if not 0.0 <= stability <= 1.0:
        console.print("❌ Stability must be between 0.0 and 1.0", style="red")
        raise typer.Exit(1)
    
    # Load script
    with open(script_file, encoding='utf-8') as f:
        script = json.load(f)
    
    # Get actor config
    actor_id = script.get("actor", "sophie")
    actor_config = get_config().get_actor(actor_id)
    if actor_config is None:
        console.print(f"❌ Actor '{actor_id}' not found", style="red")
        raise typer.Exit(1)
    
    # Get text to speak
    script_text = script.get("full_text", "")
    if not script_text:
        console.print("❌ No text found in script", style="red")
        raise typer.Exit(1)
    
    # Calculate cost estimate
    text_length = len(script_text)
    config_data = get_config().config
    engine_config = config_data.get("engines", {}).get("tts", {}).get(engine, {})
    cost_per_char = engine_config.get("cost_per_char", 0.0)
    estimated_cost = text_length * cost_per_char
    
    console.print(f"🎙️  TTS Generation Summary", style="blue")
    console.print(f"Engine: {engine}")
    console.print(f"Actor: {actor_id} ({actor_config['name']})")
    console.print(f"Text length: {text_length} characters")
    console.print(f"Estimated cost: ${estimated_cost:.4f}")
    
    if dry_run:
        console.print("🔍 [DRY RUN] Audio generation simulated", style="blue")
        return
    
    # Create output path
    if output is None:
        audio_dir = OUTPUTS_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        output = audio_dir / f"audio_{script['id']}.wav"
    
    try:
        if engine == "chatterbox":
            # Use Chatterbox TTS
            audio_data = _generate_chatterbox_audio(
                text=script_text,
                actor_config=actor_config,
                stability=stability
            )
        elif engine == "elevenlabs":
            # Use ElevenLabs (existing functionality)
            audio_data = _generate_elevenlabs_audio(
                text=script_text,
                actor_config=actor_config,
                stability=stability
            )
        
        # Save audio file
        with open(output, 'wb') as f:
            f.write(audio_data)
        
        console.print(f"✅ Audio generated: {output}", style="green")
        
        # Track expense
        get_budget().add_expense(engine, estimated_cost, f"TTS for script {script['id']}")
        
    except Exception as e:
        console.print(f"❌ Audio generation failed: {str(e)}", style="red")
        raise typer.Exit(1)

def _generate_chatterbox_audio(text: str, actor_config: Dict, stability: float) -> bytes:
    """Generate audio using Chatterbox TTS (or fallback to mock for testing)"""
    try:
        # Import Chatterbox
        from chatterbox import ChatterboxTTS
        
        # Initialize TTS
        tts = ChatterboxTTS()
        
        # Configure voice based on actor
        voice_style = actor_config.get("voice_style", "neutral")
        gender = actor_config.get("gender", "female")
        
        # Map actor properties to Chatterbox parameters
        voice_params = {
            "speed": 1.0,
            "pitch": 0.0,
            "energy": stability,
            "style": voice_style
        }
        
        # Adjust for gender
        if gender == "male":
            voice_params["pitch"] = -0.2
        else:
            voice_params["pitch"] = 0.1
            
        console.print(f"🗣️  Using Chatterbox TTS with {gender} voice, style: {voice_style}", style="blue")
        
        # Generate audio
        audio_data = tts.generate(
            text=text,
            **voice_params
        )
        
        return audio_data
        
    except ImportError:
        console.print("⚠️  Chatterbox TTS not available, creating mock audio file", style="yellow")
        # Create a mock WAV file for testing (minimal WAV header)
        import struct
        
        # Minimal WAV file header for 5 seconds of silence at 22050Hz
        sample_rate = 22050
        duration = 5.0  # seconds
        num_samples = int(sample_rate * duration)
        
        wav_header = struct.pack('<4sI4s', b'RIFF', 36 + num_samples * 2, b'WAVE')
        fmt_chunk = struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, 1, sample_rate, 
                               sample_rate * 2, 2, 16)
        data_header = struct.pack('<4sI', b'data', num_samples * 2)
        
        # Silent audio data
        audio_data = b'\x00' * (num_samples * 2)
        
        mock_wav = wav_header + fmt_chunk + data_header + audio_data
        
        console.print(f"📝 Generated {len(mock_wav)} byte mock WAV file", style="blue")
        return mock_wav
        
    except Exception as e:
        console.print(f"❌ Chatterbox generation failed: {str(e)}", style="red")
        raise

def _generate_elevenlabs_audio(text: str, actor_config: Dict, stability: float) -> bytes:
    """Generate audio using ElevenLabs TTS"""
    try:
        # Import ElevenLabs
        from elevenlabs import generate, set_api_key
        
        # Get API key from env
        env_config = get_config().env
        api_key = env_config.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise Exception("ELEVENLABS_API_KEY not found in .env file")
        
        set_api_key(api_key)
        
        # Use default voice (since we don't have custom voices set up)
        voice = "Rachel"  # High-quality English voice
        
        console.print(f"🎙️  Using ElevenLabs voice: {voice}", style="blue")
        
        # Generate audio
        audio = generate(
            text=text,
            voice=voice,
            model="eleven_monolingual_v1",
            stability=stability
        )
        
        return audio
        
    except ImportError:
        console.print("❌ ElevenLabs not available", style="red")
        raise Exception("ElevenLabs not available")
    except Exception as e:
        console.print(f"❌ ElevenLabs generation failed: {str(e)}", style="red")
        raise

@app.command()
def generate_video(
    audio_file: Path = typer.Argument(..., help="Audio file"),
    actor: str = typer.Argument(..., help="Actor ID"),
    engine: str = typer.Option("seedance", "--engine", "-e", help="Video engine: seedance|kling"),
    format: str = typer.Option("vertical", "--format", "-f", help="Format: vertical|square|horizontal"),
    motion: float = typer.Option(0.3, "--motion", "-m", help="Motion level (0.0-1.0)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output video file")
) -> None:
    """Generate video with lip-sync using Seedance 2.0"""
    
    # Validate inputs
    if not audio_file.exists():
        console.print(f"❌ Audio file not found: {audio_file}", style="red")
        raise typer.Exit(1)
    
    if engine not in ["seedance", "kling"]:
        console.print("❌ Engine must be 'seedance' or 'kling'", style="red")
        raise typer.Exit(1)
    
    if format not in ["vertical", "square", "horizontal"]:
        console.print("❌ Format must be 'vertical', 'square', or 'horizontal'", style="red")
        raise typer.Exit(1)
    
    if not 0.0 <= motion <= 1.0:
        console.print("❌ Motion must be between 0.0 and 1.0", style="red")
        raise typer.Exit(1)
    
    # Get actor config
    actor_config = get_config().get_actor(actor)
    if actor_config is None:
        console.print(f"❌ Actor '{actor}' not found", style="red")
        raise typer.Exit(1)
    
    # Check actor portrait exists
    portrait_path = Path(actor_config.get("portrait", ""))
    if not portrait_path.is_absolute():
        portrait_path = BASE_DIR / portrait_path
    
    if not portrait_path.exists():
        console.print(f"❌ Actor portrait not found: {portrait_path}", style="red")
        raise typer.Exit(1)
    
    # Get audio duration for cost calculation
    audio_duration = _get_audio_duration(audio_file)
    
    # Calculate cost estimate
    config_data = get_config().config
    engine_config = config_data.get("engines", {}).get("video", {}).get(engine, {})
    cost_per_second = engine_config.get("cost_per_second", 0.12)
    estimated_cost = audio_duration * cost_per_second
    
    # Get format config
    format_config = config_data.get("formats", {}).get(format, {})
    resolution = format_config.get("resolution", "1080x1920")
    
    console.print(f"🎬 Video Generation Summary", style="blue")
    console.print(f"Engine: {engine}")
    console.print(f"Actor: {actor} ({actor_config['name']})")
    console.print(f"Format: {format} ({resolution})")
    console.print(f"Audio duration: {audio_duration:.1f}s")
    console.print(f"Motion level: {motion}")
    console.print(f"Estimated cost: ${estimated_cost:.3f}")
    
    if dry_run:
        console.print("🔍 [DRY RUN] Video generation simulated", style="blue")
        return
    
    # Create output path
    if output is None:
        video_dir = OUTPUTS_DIR / "video_raw"
        video_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        output = video_dir / f"video_{actor}_{timestamp}.mp4"
    
    try:
        if engine == "seedance":
            # Use Seedance 2.0 via fal.ai
            video_url = _generate_seedance_video(
                audio_file=audio_file,
                portrait_path=portrait_path,
                format=format,
                motion=motion
            )
        elif engine == "kling":
            # Use Kling (placeholder for future implementation)
            console.print("⚠️  Kling engine not implemented yet", style="yellow")
            raise Exception("Kling engine not available")
        
        # Download video
        console.print("⬇️  Downloading generated video...", style="blue")
        _download_video(video_url, output)
        
        console.print(f"✅ Video generated: {output}", style="green")
        
        # Track expense
        get_budget().add_expense(engine, estimated_cost, f"Video generation for {actor}")
        
    except Exception as e:
        console.print(f"❌ Video generation failed: {str(e)}", style="red")
        raise typer.Exit(1)

def _get_audio_duration(audio_file: Path) -> float:
    """Get audio duration in seconds"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(audio_file))
        return len(audio) / 1000.0  # Convert from milliseconds
    except ImportError:
        console.print("⚠️  pydub not available, estimating duration", style="yellow")
        # Rough estimate based on file size (very approximate)
        file_size = audio_file.stat().st_size
        return max(10.0, file_size / 50000)  # Rough estimate
    except Exception:
        console.print("⚠️  Could not determine audio duration, using default", style="yellow")
        return 30.0  # Default fallback

def _generate_seedance_video(audio_file: Path, portrait_path: Path, format: str, motion: float) -> str:
    """Generate video using Seedance 2.0 via fal.ai"""
    try:
        # Import fal client
        import fal_client
        
        # Get API key from env
        env_config = get_config().env
        fal_key = env_config.get("FAL_KEY")
        if not fal_key:
            raise Exception("FAL_KEY not found in .env file")
        
        # Set up fal client
        import os
        os.environ["FAL_KEY"] = fal_key
        
        console.print("🎭 Uploading files to fal.ai...", style="blue")
        
        # Upload audio file
        audio_url = fal_client.upload_file(str(audio_file))
        console.print(f"  Audio uploaded: {audio_url[:50]}...")
        
        # Upload portrait
        portrait_url = fal_client.upload_file(str(portrait_path))
        console.print(f"  Portrait uploaded: {portrait_url[:50]}...")
        
        # Configure format
        format_config = get_config().config.get("formats", {}).get(format, {})
        width, height = format_config.get("resolution", "1080x1920").split("x")
        
        # Prepare request
        request_data = {
            "portrait_image_url": portrait_url,
            "audio_url": audio_url,
            "width": int(width),
            "height": int(height),
            "motion_level": motion,
            "enable_lipsync": True,  # Seedance 2.0's key feature
            "quality": "high"
        }
        
        console.print("🎬 Generating video with Seedance 2.0...", style="blue")
        
        # Submit to fal.ai (using seedance 2.0 endpoint)
        # Note: The exact endpoint name may vary - check fal.ai docs
        result = fal_client.subscribe(
            "fal-ai/seedance-2",  # This might be different - check fal.ai docs
            arguments=request_data
        )
        
        if "video_url" not in result:
            raise Exception(f"Unexpected response from fal.ai: {result}")
        
        video_url = result["video_url"]
        console.print(f"✅ Video generated successfully!", style="green")
        
        return video_url
        
    except ImportError:
        console.print("❌ fal-client not installed. Install with: pip install fal-client", style="red")
        raise Exception("fal-client not available")
    except Exception as e:
        console.print(f"❌ Seedance generation failed: {str(e)}", style="red")
        raise

def _download_video(video_url: str, output_path: Path):
    """Download video from URL"""
    try:
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
    except Exception as e:
        raise Exception(f"Failed to download video: {str(e)}")

@app.command()
def assemble(
    video_file: Path = typer.Argument(..., help="Raw video file"),
    script_file: Optional[Path] = typer.Argument(None, help="Script JSON for subtitles"),
    template: str = typer.Option("talking_head", "--template", "-t", help="Template: talking_head|split_screen|problem_solution"),
    no_subtitles: bool = typer.Option(False, "--no-subtitles", help="Disable subtitles"),
    no_music: bool = typer.Option(False, "--no-music", help="Disable background music"),
    no_logo: bool = typer.Option(False, "--no-logo", help="Disable logo"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Final video output")
) -> None:
    """Assemble final video with FFmpeg (subtitles, music, logo)"""
    
    # Validate inputs
    if not video_file.exists():
        console.print(f"❌ Video file not found: {video_file}", style="red")
        raise typer.Exit(1)
    
    if template not in ["talking_head", "split_screen", "problem_solution"]:
        console.print("❌ Template must be 'talking_head', 'split_screen', or 'problem_solution'", style="red")
        raise typer.Exit(1)
    
    # Check FFmpeg is available
    if not _check_ffmpeg():
        console.print("❌ FFmpeg not found. Install FFmpeg to use post-production", style="red")
        raise typer.Exit(1)
    
    # Load script for subtitles (optional)
    script_data = None
    if script_file and script_file.exists():
        with open(script_file, encoding='utf-8') as f:
            script_data = json.load(f)
    elif not no_subtitles:
        console.print("⚠️  No script file provided, subtitles will be disabled", style="yellow")
        no_subtitles = True
    
    # Create output path
    if output is None:
        final_dir = OUTPUTS_DIR / "video_final"
        final_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        output = final_dir / f"final_{template}_{timestamp}.mp4"
    
    console.print(f"🎬 Assembling video with template: {template}", style="blue")
    console.print(f"Input: {video_file}")
    console.print(f"Output: {output}")
    
    try:
        # Build FFmpeg command
        ffmpeg_cmd = _build_ffmpeg_command(
            input_video=video_file,
            output_video=output,
            template=template,
            script_data=script_data,
            no_subtitles=no_subtitles,
            no_music=no_music,
            no_logo=no_logo
        )
        
        # Execute FFmpeg
        console.print("⚡ Running FFmpeg...", style="blue")
        _run_ffmpeg_command(ffmpeg_cmd)
        
        console.print(f"✅ Video assembled: {output}", style="green")
        
        # Show file info
        file_size = output.stat().st_size / (1024 * 1024)  # MB
        console.print(f"📊 Final video: {file_size:.1f} MB", style="blue")
        
    except Exception as e:
        console.print(f"❌ Video assembly failed: {str(e)}", style="red")
        raise typer.Exit(1)

def _check_ffmpeg() -> bool:
    """Check if FFmpeg is available"""
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def _build_ffmpeg_command(
    input_video: Path,
    output_video: Path,
    template: str,
    script_data: Optional[Dict],
    no_subtitles: bool,
    no_music: bool,
    no_logo: bool
) -> List[str]:
    """Build FFmpeg command based on template and options"""
    
    cmd = ["ffmpeg", "-i", str(input_video)]
    filter_complex = []
    
    # Base video stream
    video_stream = "[0:v]"
    audio_stream = "[0:a]"
    
    # Add logo overlay if enabled
    if not no_logo:
        logo_path = ASSETS_DIR / "logo.png"
        if logo_path.exists():
            cmd.extend(["-i", str(logo_path)])
            # Position logo in bottom-right corner
            filter_complex.append(f"{video_stream}[1:v]overlay=W-w-20:H-h-20[logo]")
            video_stream = "[logo]"
        else:
            console.print("⚠️  Logo not found, skipping logo overlay", style="yellow")
    
    # Add subtitles if enabled and available
    if not no_subtitles and script_data:
        subtitles_filter = _create_subtitles_filter(script_data, template)
        if subtitles_filter:
            filter_complex.append(f"{video_stream}{subtitles_filter}[subtitled]")
            video_stream = "[subtitled]"
    
    # Add background music if enabled
    if not no_music:
        music_path = ASSETS_DIR / "music" / f"{template}_music.mp3"
        if music_path.exists():
            cmd.extend(["-i", str(music_path)])
            # Mix original audio with background music (lower volume)
            music_index = len([x for x in cmd if x == "-i"]) - 1
            filter_complex.append(f"{audio_stream}[{music_index}:a]amix=inputs=2:weights=1 0.2[audio_out]")
            audio_stream = "[audio_out]"
        else:
            console.print("⚠️  Background music not found, skipping", style="yellow")
    
    # Apply filter complex if any filters were added
    if filter_complex:
        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        cmd.extend(["-map", video_stream.strip("[]")])
        cmd.extend(["-map", audio_stream.strip("[]")])
    
    # Output settings
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",  # Overwrite output file
        str(output_video)
    ])
    
    return cmd

def _create_subtitles_filter(script_data: Dict, template: str) -> str:
    """Create subtitles filter for FFmpeg"""
    try:
        # Get script text and create simple subtitles
        script_text = script_data.get("full_text", "")
        if not script_text:
            return ""
        
        # For now, create a simple subtitle overlay
        # In a full implementation, you'd parse timing from script sections
        text = script_text.replace("'", "\\'").replace('"', '\\"')
        
        # Choose subtitle style based on template
        if template == "talking_head":
            # Bottom center, white text with black outline
            return f"drawtext=text='{text}':x=(w-text_w)/2:y=h-100:fontsize=32:fontcolor=white:bordercolor=black:borderw=2"
        elif template == "split_screen":
            # Top center for split screen
            return f"drawtext=text='{text}':x=(w-text_w)/2:y=50:fontsize=28:fontcolor=white:bordercolor=black:borderw=2"
        else:
            # Default bottom center
            return f"drawtext=text='{text}':x=(w-text_w)/2:y=h-80:fontsize=30:fontcolor=white:bordercolor=black:borderw=2"
            
    except Exception as e:
        console.print(f"⚠️  Subtitles creation failed: {str(e)}", style="yellow")
        return ""

def _run_ffmpeg_command(cmd: List[str]):
    """Execute FFmpeg command"""
    try:
        import subprocess
        
        # Show command for debugging (hide sensitive paths)
        safe_cmd = [c if not c.startswith('/') else Path(c).name for c in cmd]
        console.print(f"FFmpeg command: {' '.join(safe_cmd[:10])}...", style="dim")
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stderr:
            # FFmpeg writes normal output to stderr
            console.print("FFmpeg output:", style="dim")
            for line in result.stderr.split('\n')[-5:]:  # Show last 5 lines
                if line.strip():
                    console.print(f"  {line}", style="dim")
                    
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg failed: {e.stderr}")
    except Exception as e:
        raise Exception(f"Failed to run FFmpeg: {str(e)}")

# Keep post_prod as alias for backward compatibility
@app.command()
def post_prod(
    video_file: Path = typer.Argument(..., help="Raw video file"),
    template: str = typer.Option("talking_head", "--template", "-t", help="Template: talking_head|split_screen|problem_solution"),
    no_subtitles: bool = typer.Option(False, "--no-subtitles", help="Disable subtitles"),
    no_music: bool = typer.Option(False, "--no-music", help="Disable background music"),
    no_logo: bool = typer.Option(False, "--no-logo", help="Disable logo"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Final video output")
) -> None:
    """Post-production with FFmpeg (alias for assemble)"""
    
    # Call assemble command with same parameters
    # We need to reconstruct the call since we can't directly call assemble()
    import sys
    
    # Build new argv for assemble command
    args = ["assemble", str(video_file)]
    
    if template != "talking_head":
        args.extend(["--template", template])
    if no_subtitles:
        args.append("--no-subtitles")
    if no_music:
        args.append("--no-music")
    if no_logo:
        args.append("--no-logo")
    if output:
        args.extend(["--output", str(output)])
    
    # Replace current command
    original_argv = sys.argv.copy()
    try:
        sys.argv = [sys.argv[0]] + args
        # Note: This is a workaround - in a real implementation you'd refactor to share logic
        console.print("🔄 Redirecting to assemble command...", style="blue")
        assemble(video_file, None, template, no_subtitles, no_music, no_logo, output)
    finally:
        sys.argv = original_argv

@app.command()
def full_pipeline(
    hook_text: str = typer.Argument(..., help="Marketing hook text"),
    actor: str = typer.Option("sophie", "--actor", "-a", help="Actor ID"),
    duration: int = typer.Option(30, "--duration", "-d", help="Video duration in seconds"),
    format: str = typer.Option("vertical", "--format", "-f", help="Video format"),
    template: str = typer.Option("talking_head", "--template", "-t", help="Post-production template"),
    lang: str = typer.Option("fr", "--lang", "-l", help="Language"),
    tts_engine: str = typer.Option("chatterbox", "--tts-engine", help="TTS engine"),
    video_engine: str = typer.Option("seedance", "--video-engine", help="Video engine"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate entire pipeline"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmations")
) -> None:
    """Full automated pipeline: hook → script → audio → video → assembly"""
    
    console.print("🎬 Full Pipeline Starting", style="blue bold")
    console.print(f"Hook: {hook_text}")
    console.print(f"Actor: {actor}")
    console.print(f"Duration: {duration}s")
    console.print(f"Format: {format}")
    console.print(f"Template: {template}")
    
    # Estimate total cost
    total_cost = _estimate_pipeline_cost(duration, tts_engine, video_engine)
    console.print(f"💰 Estimated total cost: ${total_cost:.3f}", style="yellow")
    
    if not confirm and not dry_run:
        if not typer.confirm(f"Proceed with pipeline? (Cost: ${total_cost:.3f})"):
            console.print("❌ Pipeline cancelled", style="red")
            raise typer.Exit(0)
    
    try:
        pipeline_id = generate_file_id()
        console.print(f"🔧 Pipeline ID: {pipeline_id}", style="dim")
        
        # Step 1: Create hook structure
        console.print("\n📝 Step 1/5: Creating hook structure...", style="blue")
        hook_data = {
            "id": f"hook_{pipeline_id}",
            "timestamp": datetime.now().isoformat(),
            "hooks": [{
                "id": f"hook_001",
                "text": hook_text,
                "style": "custom",
                "estimated_duration": duration,
                "call_to_action": "Télécharge Mila maintenant!"
            }]
        }
        
        hooks_dir = OUTPUTS_DIR / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_file = hooks_dir / f"hook_{pipeline_id}.json"
        
        with open(hook_file, 'w', encoding='utf-8') as f:
            json.dump(hook_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"✅ Hook created: {hook_file.name}")
        
        # Step 2: Generate script
        console.print("\n📖 Step 2/5: Generating script...", style="blue")
        if not dry_run:
            # Call generate_script command
            import subprocess
            import sys
            
            cmd = [
                sys.executable, "studio_cli.py", "generate-script",
                str(hook_file),
                "--actor", actor,
                "--duration", str(duration),
                "--lang", lang
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            if result.returncode != 0:
                raise Exception(f"Script generation failed: {result.stderr}")
        
        # Find the generated script
        scripts_dir = OUTPUTS_DIR / "scripts"
        script_files = list(scripts_dir.glob(f"script_*.json"))
        if not script_files:
            raise Exception("No script file found after generation")
        
        script_file = sorted(script_files, key=lambda x: x.stat().st_mtime)[-1]  # Latest
        console.print(f"✅ Script generated: {script_file.name}")
        
        # Step 3: Generate audio
        console.print("\n🎙️  Step 3/5: Generating audio...", style="blue")
        if not dry_run:
            cmd = [
                sys.executable, "studio_cli.py", "generate-audio",
                str(script_file),
                "--engine", tts_engine
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            if result.returncode != 0:
                console.print(f"⚠️  Audio generation failed, using mock: {result.stderr}", style="yellow")
                # Create mock audio file for testing
                audio_dir = OUTPUTS_DIR / "audio"
                audio_dir.mkdir(parents=True, exist_ok=True)
                audio_file = audio_dir / f"audio_{pipeline_id}.wav"
                audio_file.write_text("# Mock audio file for testing")
            else:
                # Find generated audio
                audio_dir = OUTPUTS_DIR / "audio"
                audio_files = list(audio_dir.glob("audio_*.wav"))
                if audio_files:
                    audio_file = sorted(audio_files, key=lambda x: x.stat().st_mtime)[-1]
                else:
                    raise Exception("No audio file found after generation")
        else:
            # Mock for dry run
            audio_file = Path("mock_audio.wav")
        
        console.print(f"✅ Audio generated: {audio_file.name}")
        
        # Step 4: Generate video
        console.print("\n🎬 Step 4/5: Generating video...", style="blue")
        if not dry_run:
            cmd = [
                sys.executable, "studio_cli.py", "generate-video",
                str(audio_file), actor,
                "--engine", video_engine,
                "--format", format
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            if result.returncode != 0:
                console.print(f"⚠️  Video generation failed, using mock: {result.stderr}", style="yellow")
                # Create mock video file for testing
                video_dir = OUTPUTS_DIR / "video_raw"
                video_dir.mkdir(parents=True, exist_ok=True)
                video_file = video_dir / f"video_{pipeline_id}.mp4"
                video_file.write_text("# Mock video file for testing")
            else:
                # Find generated video
                video_dir = OUTPUTS_DIR / "video_raw"
                video_files = list(video_dir.glob("video_*.mp4"))
                if video_files:
                    video_file = sorted(video_files, key=lambda x: x.stat().st_mtime)[-1]
                else:
                    raise Exception("No video file found after generation")
        else:
            # Mock for dry run
            video_file = Path("mock_video.mp4")
        
        console.print(f"✅ Video generated: {video_file.name}")
        
        # Step 5: Assemble final video
        console.print("\n🔧 Step 5/5: Assembling final video...", style="blue")
        if not dry_run:
            cmd = [
                sys.executable, "studio_cli.py", "assemble",
                str(video_file), str(script_file),
                "--template", template
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR)
            if result.returncode != 0:
                console.print(f"⚠️  Assembly failed: {result.stderr}", style="yellow")
                final_video = video_file  # Use raw video as fallback
            else:
                # Find final video
                final_dir = OUTPUTS_DIR / "video_final"
                final_files = list(final_dir.glob("final_*.mp4"))
                if final_files:
                    final_video = sorted(final_files, key=lambda x: x.stat().st_mtime)[-1]
                else:
                    final_video = video_file
        else:
            final_video = Path("mock_final.mp4")
        
        console.print(f"✅ Final video: {final_video.name}")
        
        # Summary
        console.print("\n🎉 Pipeline Complete!", style="green bold")
        console.print(f"📁 Outputs generated:")
        console.print(f"  - Hook: {hook_file}")
        console.print(f"  - Script: {script_file}")
        console.print(f"  - Audio: {audio_file}")
        console.print(f"  - Video: {video_file}")
        console.print(f"  - Final: {final_video}")
        
        if not dry_run:
            # Track total expense
            get_budget().add_expense("pipeline", total_cost, f"Full pipeline {pipeline_id}")
        
    except Exception as e:
        console.print(f"❌ Pipeline failed: {str(e)}", style="red")
        raise typer.Exit(1)

def _estimate_pipeline_cost(duration: int, tts_engine: str, video_engine: str) -> float:
    """Estimate total pipeline cost"""
    config_data = get_config().config
    
    # TTS cost (roughly 150 words for 30s, ~2 chars per word = 300 chars)
    chars_per_second = 10  # Rough estimate
    tts_chars = duration * chars_per_second
    tts_cost_per_char = config_data.get("engines", {}).get("tts", {}).get(tts_engine, {}).get("cost_per_char", 0.0)
    tts_cost = tts_chars * tts_cost_per_char
    
    # Video cost
    video_cost_per_second = config_data.get("engines", {}).get("video", {}).get(video_engine, {}).get("cost_per_second", 0.12)
    video_cost = duration * video_cost_per_second
    
    # Claude cost (small, ~$0.01)
    claude_cost = 0.01
    
    return tts_cost + video_cost + claude_cost

@app.command()
def test_actor(
    actor_id: str = typer.Argument(..., help="Actor ID to test"),
    format: str = typer.Option("vertical", "--format", "-f", help="Video format"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls")
) -> None:
    """Generate 5s test video for actor"""
    
    # Validate actor
    actor_config = get_config().get_actor(actor_id)
    if actor_config is None:
        console.print(f"❌ Actor '{actor_id}' not found", style="red")
        raise typer.Exit(1)
    
    console.print(f"🎭 Testing actor: {actor_id} ({actor_config['name']})", style="blue")
    
    # Use a simple test hook
    test_hook = f"Bonjour ! Je suis {actor_config['name']}, et je teste l'engine vidéo de Mila."
    
    try:
        # Run mini pipeline with 5s duration
        full_pipeline(
            hook_text=test_hook,
            actor=actor_id,
            duration=5,
            format=format,
            template="talking_head",
            lang="fr",
            tts_engine="chatterbox",
            video_engine="seedance",
            dry_run=dry_run,
            confirm=True  # Auto-confirm for test
        )
        
        console.print(f"✅ Actor {actor_id} test completed", style="green")
        
    except Exception as e:
        console.print(f"❌ Actor test failed: {str(e)}", style="red")
        raise typer.Exit(1)

@app.command()
def test_setup(
) -> None:
    """Test the complete setup and configuration"""
    
    console.print("🔧 Testing Studio CLI Setup", style="blue bold")
    
    errors = []
    warnings = []
    
    # Test 1: DNA file
    console.print("\n1️⃣  Testing DNA file...", style="blue")
    dna_file = get_dna_file()
    if dna_file:
        console.print(f"  ✅ DNA file found: {dna_file}")
        try:
            with open(dna_file) as f:
                dna = json.load(f)
            console.print(f"  ✅ DNA parsed successfully")
        except Exception as e:
            errors.append(f"DNA file corrupted: {e}")
    else:
        errors.append("DNA file not found")
    
    # Test 2: Config file
    console.print("\n2️⃣  Testing config file...", style="blue")
    try:
        config_data = get_config().config
        console.print(f"  ✅ Config loaded: {len(config_data.get('actors', {}))} actors")
    except Exception as e:
        errors.append(f"Config loading failed: {e}")
    
    # Test 3: Actors and assets
    console.print("\n3️⃣  Testing actors and assets...", style="blue")
    actors = get_config().list_actors()
    for actor_id, actor_config in actors.items():
        portrait_path = Path(actor_config.get("portrait", ""))
        if not portrait_path.is_absolute():
            portrait_path = BASE_DIR / portrait_path
        
        if portrait_path.exists():
            console.print(f"  ✅ {actor_id}: portrait found")
        else:
            warnings.append(f"Actor {actor_id}: portrait missing ({portrait_path})")
    
    # Test 4: Output directories
    console.print("\n4️⃣  Testing output directories...", style="blue")
    required_dirs = ["hooks", "scripts", "audio", "video_raw", "video_final"]
    for dirname in required_dirs:
        dir_path = OUTPUTS_DIR / dirname
        if dir_path.exists():
            console.print(f"  ✅ {dirname}: {len(list(dir_path.glob('*')))} files")
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            console.print(f"  🔧 {dirname}: created")
    
    # Test 5: External dependencies
    console.print("\n5️⃣  Testing external dependencies...", style="blue")
    
    # Test FFmpeg
    if _check_ffmpeg():
        console.print("  ✅ FFmpeg: available")
    else:
        warnings.append("FFmpeg not found - post-production will not work")
    
    # Test Python packages
    packages = {
        "typer": "CLI framework",
        "rich": "Console output",
        "requests": "HTTP requests",
        "pydub": "Audio processing"
    }
    
    for package, desc in packages.items():
        try:
            __import__(package)
            console.print(f"  ✅ {package}: installed")
        except ImportError:
            warnings.append(f"{package} not installed - {desc}")
    
    # Test TTS engines
    console.print("\n6️⃣  Testing TTS engines...", style="blue")
    
    # Chatterbox
    try:
        import chatterbox
        console.print("  ✅ Chatterbox TTS: available")
    except ImportError:
        warnings.append("Chatterbox TTS not installed - run: pip install chatterbox-tts")
    
    # ElevenLabs
    try:
        import elevenlabs
        env_config = get_config().env
        if env_config.get("ELEVENLABS_API_KEY"):
            console.print("  ✅ ElevenLabs: API key found")
        else:
            console.print("  ⚠️  ElevenLabs: no API key (optional)")
    except ImportError:
        console.print("  ⚠️  ElevenLabs: not installed (optional)")
    
    # Test Video engines
    console.print("\n7️⃣  Testing video engines...", style="blue")
    
    try:
        import fal_client
        env_config = get_config().env
        if env_config.get("FAL_KEY"):
            console.print("  ✅ fal.ai: client and API key found")
        else:
            warnings.append("FAL_KEY not found in .env - video generation will not work")
    except ImportError:
        warnings.append("fal-client not installed - run: pip install fal-client")
    
    # Summary
    console.print("\n📊 Setup Test Summary", style="blue bold")
    
    if errors:
        console.print("❌ Critical errors found:", style="red")
        for error in errors:
            console.print(f"  • {error}", style="red")
    
    if warnings:
        console.print("⚠️  Warnings:", style="yellow")
        for warning in warnings:
            console.print(f"  • {warning}", style="yellow")
    
    if not errors and not warnings:
        console.print("🎉 All tests passed! Setup is complete.", style="green bold")
    elif not errors:
        console.print("✅ Core functionality working. Some features may be limited.", style="green")
    else:
        console.print("❌ Setup has critical issues. Please fix errors before using.", style="red")
        raise typer.Exit(1)

if __name__ == "__main__":
    # Ensure output directories exist
    OUTPUTS_DIR.mkdir(exist_ok=True)
    for subdir in ["hooks", "scripts", "audio", "video_raw", "video_final", "logs"]:
        (OUTPUTS_DIR / subdir).mkdir(exist_ok=True)
    
    app()