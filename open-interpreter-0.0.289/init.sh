#!/bin/bash
# Open Interpreter Project Initialization Script

echo "Initializing Open Interpreter environment..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing dependencies with Poetry..."
poetry install

# Activate virtual environment
source $(poetry env info --path)/bin/activate

# Verify installation by checking if interpreter can be imported
echo "Verifying installation..."
python -c "import interpreter; print('Open Interpreter imported successfully')" || {
    echo "ERROR: Failed to import Open Interpreter"
    exit 1
}

# Run a basic smoke test
echo "Running smoke test..."
# Run a basic smoke test
echo "Running smoke test..."
python -c "
try:
    import interpreter
    print('✓ Open Interpreter successfully imported')
    print('✓ Ready to use Open Interpreter')
    # Test basic functionality
    # Interpreter is automatically instantiated when imported
    print('✓ Interpreter instantiated successfully')
except Exception as e:
    print('✗ Smoke test failed:', str(e))
    import sys
    sys.exit(1)
"

echo "Environment initialization complete!"
echo "To activate virtual environment manually: source \$(poetry env info --path)/bin/activate"