#!/bin/bash
# Fix the entry point script to include the project path in sys.path

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"
ENTRY_POINT="$VENV_DIR/bin/ledgerscope"

if [ ! -f "$ENTRY_POINT" ]; then
    echo "Error: Entry point script not found at $ENTRY_POINT"
    echo "Run 'pip install -e .' first"
    exit 1
fi

echo "Fixing entry point script at $ENTRY_POINT"

# Create a backup
cp "$ENTRY_POINT" "$ENTRY_POINT.bak"

# Get the shebang line
SHEBANG=$(head -n 1 "$ENTRY_POINT")

# Create the new script
cat > "$ENTRY_POINT" << EOF
$SHEBANG
import sys
import os

# Add the package directory to sys.path for editable install
package_dir = '$SCRIPT_DIR'
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from ledgerscope.cli import main

if __name__ == '__main__':
    if sys.argv[0].endswith('.exe'):
        sys.argv[0] = sys.argv[0][:-4]
    sys.exit(main())
EOF

chmod +x "$ENTRY_POINT"

echo "Entry point fixed! Test with: .venv/bin/ledgerscope --version"
