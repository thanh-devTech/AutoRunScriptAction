#!/bin/bash
# Script setup version history cho changelog script
# Chạy một lần khi tạo repo mới

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "🚀 Setting up version history for changelog..."

# Kiểm tra xem có git repo không
if [ ! -d .git ]; then
    echo "❌ Not a git repository. Run 'git init' first."
    exit 1
fi

# Kiểm tra có commit nào không
if git rev-parse HEAD >/dev/null 2>&1; then
    echo "ℹ️ Repository already has commits. Skipping initial setup."
    echo "📝 Current plug.php version:"
    grep "^Version:" plug.php || echo "No version found"
else
    echo "📝 This appears to be a new repository. Create your first commit:"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 0
fi

# Tạo CHANGELOG nếu chưa có
if [ ! -f log.txt ]; then
    echo "📄 Creating initial log.txt..."
    python3 run_scripts/generate_changelog.py || true
fi

# Tạo version tag nếu có version trong plug.php
if grep -q "^Version:" plug.php; then
    VERSION=$(grep "^Version:" plug.php | head -1 | sed 's/.*Version:\s*//;s/\s*$//')
    TAG_NAME="v${VERSION}"
    
    if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
        echo "🏷️  Creating tag: $TAG_NAME"
        git tag -a "$TAG_NAME" -m "Release version $VERSION"
        echo "✅ Tag created!"
    else
        echo "ℹ️  Tag $TAG_NAME already exists"
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Make version changes to plug.php (edit Version: line)"
echo "2. Commit: git commit -am 'bump: version X.Y.Z'"
echo "3. Tag: git tag -a v<version> -m 'Release v<version>'"
echo "4. Push: git push origin dev --tags"
echo "5. This will trigger the changelog generator"
