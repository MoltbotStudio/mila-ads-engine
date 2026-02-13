#!/bin/bash
# Install script for Mila Ads Engine

set -e

echo "🚀 Installing Mila Ads Engine V2..."

# Check Python version
python3 --version || {
    echo "❌ Python 3 is required but not installed."
    exit 1
}

# Install dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Create .env from template if it doesn't exist
if [ ! -f .env.local ]; then
    echo "🔐 Creating .env.local from template..."
    cp .env .env.local
    echo "⚠️  Please edit .env.local with your API keys!"
fi

# Make CLI executable
chmod +x studio_cli.py

# Test CLI
echo "🧪 Testing CLI..."
python3 studio_cli.py --help > /dev/null || {
    echo "❌ CLI test failed"
    exit 1
}

# Create example briefing
echo "📄 Generating example briefing..."
python3 studio_cli.py briefing > /dev/null

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env.local with your API keys"
echo "2. Run: python3 studio_cli.py briefing"
echo "3. Run: python3 studio_cli.py generate-hooks --style problem --count 3"
echo "4. Run: python3 studio_cli.py list-actors"
echo ""
echo "📚 Documentation: README.md"
echo "🆘 Help: python3 studio_cli.py --help"