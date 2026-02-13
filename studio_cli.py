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
DNA_FILE = BASE_DIR.parent / "dna.json" 
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

@app.command()
def briefing(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path")
) -> None:
    """Generate marketing brief from dna.json"""
    
    if not DNA_FILE.exists():
        console.print(f"❌ DNA file not found: {DNA_FILE}", style="red")
        raise typer.Exit(1)
    
    # Load DNA
    with open(DNA_FILE) as f:
        dna = json.load(f)
    
    # Generate briefing
    brief = {
        "id": generate_file_id(),
        "timestamp": datetime.now().isoformat(),
        "app": dna.get("app", {}),
        "persona": dna.get("persona", {}),
        "target_problems": dna.get("target_problems", []),
        "differentiators": dna.get("differentiators", []),
        "target_audience": dna.get("app", {}).get("target_audience", ""),
        "marketing_angles": {
            "problem": [p for p in dna.get("target_problems", [])],
            "solution": dna.get("differentiators", []),
            "persona": {
                "name": dna.get("persona", {}).get("name", ""),
                "personality": dna.get("persona", {}).get("personality", ""),
                "expertise": dna.get("persona", {}).get("expertise", [])
            }
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
    table.add_row("Target", brief["target_audience"])
    table.add_row("Key Problems", str(len(brief["target_problems"])))
    table.add_row("Differentiators", str(len(brief["differentiators"])))
    
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
                    "text": f"[SIMULATED] Hook #{i} for {style} style targeting {brief['target_audience']}",
                    "style": style,
                    "estimated_duration": 30,
                    "call_to_action": "Télécharge Mila maintenant!"
                } for i in range(1, count + 1)
            ]
        }
    else:
        # TODO: Implement actual Claude API call
        console.print("⚠️  Claude API integration not implemented yet. Using mock data.", style="yellow")
        hooks = {
            "id": generate_file_id(),
            "timestamp": datetime.now().isoformat(),
            "style": style,
            "count": count,
            "hooks": [
                {
                    "id": f"hook_{i:03d}",
                    "text": f"Mock hook #{i} - {brief['app']['name']} résout vos problèmes de productivité en quelques clics!",
                    "style": style,
                    "estimated_duration": 30,
                    "call_to_action": "Découvre Mila dès maintenant!"
                } for i in range(1, count + 1)
            ]
        }
        
        # Add to budget (estimated)
        estimated_cost = count * 0.02  # Rough estimate
        get_budget().add_expense("claude", estimated_cost, f"Generated {count} hooks")
    
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
    hook_file: Path = typer.Argument(..., help="Hook JSON file"),
    actor: Optional[str] = typer.Option(None, "--actor", "-a", help="Actor ID (auto-select if not specified)"),
    duration: int = typer.Option(30, "--duration", "-d", help="Script duration in seconds (15|30|60)"),
    fillers: bool = typer.Option(True, "--fillers/--no-fillers", help="Add natural fillers"),
    lang: str = typer.Option("fr", "--lang", "-l", help="Language (fr|en|es)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output script file")
) -> None:
    """Generate complete script from hook"""
    
    # Validate inputs
    if not hook_file.exists():
        console.print(f"❌ Hook file not found: {hook_file}", style="red")
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
    
    # Generate script content based on duration
    if duration == 15:
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
    console.print("🚧 Audio generation not implemented yet (Phase 2)", style="yellow")

@app.command()
def generate_video(
    audio_file: Path = typer.Argument(..., help="Audio file"),
    engine: str = typer.Option("seedance", "--engine", "-e", help="Video engine: seedance|kling"),
    format: str = typer.Option("vertical", "--format", "-f", help="Format: vertical|square|horizontal"),
    motion: float = typer.Option(0.3, "--motion", "-m", help="Motion level (0.0-1.0)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output video file")
) -> None:
    """Generate video with lip-sync"""
    console.print("🚧 Video generation not implemented yet (Phase 2)", style="yellow")

@app.command()
def post_prod(
    video_file: Path = typer.Argument(..., help="Raw video file"),
    template: str = typer.Option("talking_head", "--template", "-t", help="Template: talking_head|split_screen|problem_solution"),
    no_subtitles: bool = typer.Option(False, "--no-subtitles", help="Disable subtitles"),
    no_music: bool = typer.Option(False, "--no-music", help="Disable background music"),
    no_logo: bool = typer.Option(False, "--no-logo", help="Disable logo"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Final video output")
) -> None:
    """Post-production with FFmpeg"""
    console.print("🚧 Post-production not implemented yet (Phase 3)", style="yellow")

@app.command()
def full_pipeline(
    hook_style: str = typer.Option("problem", "--hook-style", help="Hook style for generation"),
    actor: Optional[str] = typer.Option(None, "--actor", help="Actor ID"),
    duration: int = typer.Option(30, "--duration", help="Video duration in seconds"),
    format: str = typer.Option("vertical", "--format", help="Video format"),
    template: str = typer.Option("talking_head", "--template", help="Post-production template"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate entire pipeline")
) -> None:
    """Full automated pipeline"""
    console.print("🚧 Full pipeline not implemented yet (Phase 3)", style="yellow")

@app.command()
def test_actor(
    actor_id: str = typer.Argument(..., help="Actor ID to test"),
    format: str = typer.Option("vertical", "--format", "-f", help="Video format"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without API calls")
) -> None:
    """Generate 5s test video for actor"""
    console.print("🚧 Actor testing not implemented yet (Phase 2)", style="yellow")

if __name__ == "__main__":
    # Ensure output directories exist
    OUTPUTS_DIR.mkdir(exist_ok=True)
    for subdir in ["hooks", "scripts", "audio", "video_raw", "video_final", "logs"]:
        (OUTPUTS_DIR / subdir).mkdir(exist_ok=True)
    
    app()