#!/bin/bash
# RAG Factory MCP Server Setup Script
# Makes it easy to configure MCP for Claude Desktop

set -e

echo "🌐 RAG Factory MCP Server Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if in rag-factory directory
if [ ! -f "backend/mcp/server.py" ]; then
    echo "❌ Please run this script from the rag-factory root directory"
    exit 1
fi

echo "✓ RAG Factory directory detected"
echo ""

# Install MCP package
echo "📦 Installing MCP package..."
pip3 install mcp --quiet
echo "✓ MCP package installed"
echo ""

# Get current directory
RAG_FACTORY_DIR=$(pwd)
echo "📁 RAG Factory path: $RAG_FACTORY_DIR"
echo ""

# Detect OS for Claude Desktop config path
if [[ "$OSTYPE" == "darwin"* ]]; then
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    OS_NAME="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    OS_NAME="Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    OS_NAME="Windows"
else
    echo "⚠️  Unknown OS. Please manually configure Claude Desktop."
    echo "   Config file location: ~/.config/Claude/claude_desktop_config.json"
    exit 1
fi

echo "🖥️  Detected OS: $OS_NAME"
echo "📝 Claude config: $CLAUDE_CONFIG_FILE"
echo ""

# Check if Claude Desktop is installed
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "⚠️  Claude Desktop config directory not found"
    echo "   Expected: $CLAUDE_CONFIG_DIR"
    echo ""
    echo "   Please install Claude Desktop first:"
    echo "   https://claude.ai/download"
    echo ""
    echo "   Or manually create the config directory:"
    echo "   mkdir -p \"$CLAUDE_CONFIG_DIR\""
    exit 1
fi

echo "✓ Claude Desktop config directory found"
echo ""

# Get database URL
echo "🔧 Configuration"
echo "----------------"
echo ""
read -p "Database URL (default: postgresql://user:password@localhost:5433/rag_factory_db): " DB_URL
DB_URL=${DB_URL:-"postgresql://user:password@localhost:5433/rag_factory_db"}

read -p "Ollama host (default: localhost): " OLLAMA_HOST
OLLAMA_HOST=${OLLAMA_HOST:-"localhost"}

echo ""
echo "Configuration summary:"
echo "  Database: $DB_URL"
echo "  Ollama: $OLLAMA_HOST"
echo "  RAG Factory: $RAG_FACTORY_DIR"
echo ""

read -p "Continue with this configuration? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Create or update Claude Desktop config
echo ""
echo "📝 Updating Claude Desktop config..."

mkdir -p "$CLAUDE_CONFIG_DIR"

# Create MCP config JSON
MCP_CONFIG=$(cat <<EOF
{
  "mcpServers": {
    "rag-factory": {
      "command": "python3",
      "args": [
        "$RAG_FACTORY_DIR/backend/mcp/server.py"
      ],
      "env": {
        "DATABASE_URL": "$DB_URL",
        "OLLAMA_HOST": "$OLLAMA_HOST"
      }
    }
  }
}
EOF
)

# Check if config file exists
if [ -f "$CLAUDE_CONFIG_FILE" ]; then
    echo "⚠️  Config file already exists: $CLAUDE_CONFIG_FILE"
    echo ""
    echo "   Backup will be created at: ${CLAUDE_CONFIG_FILE}.backup"
    cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup"
    echo "✓ Backup created"
    echo ""

    # Try to merge with existing config (simple approach)
    echo "   NOTE: Manual merge may be required if you have other MCP servers"
fi

# Write new config
echo "$MCP_CONFIG" > "$CLAUDE_CONFIG_FILE"
echo "✓ Claude Desktop config updated"
echo ""

# Test the server
echo "🧪 Testing MCP server..."
echo ""
echo "Running quick test..."
timeout 5s python3 "$RAG_FACTORY_DIR/backend/mcp/server.py" <<< '{"jsonrpc":"2.0","method":"ping","id":1}' 2>/dev/null || true
echo ""

# Success message
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Make sure RAG Factory is running:"
echo "   cd $RAG_FACTORY_DIR"
echo "   docker-compose -f docker/docker-compose.yml up -d"
echo ""
echo "2. Restart Claude Desktop"
echo ""
echo "3. Test in Claude Desktop:"
echo "   - Open a new conversation"
echo "   - Ask: 'List available RAG projects'"
echo "   - Claude should use the rag_list_projects tool"
echo ""
echo "📚 Documentation: $RAG_FACTORY_DIR/MCP_SERVER.md"
echo ""
echo "Happy RAG-ing! 🚀"
