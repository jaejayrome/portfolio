import os
import yaml
import pytest
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Define paths
ROOT_DIR = Path(__file__).parent.parent
DATA_PATH = ROOT_DIR / "data" / "resume.yaml"
WEB_DIR = ROOT_DIR / "web"
WEB_OUTPUT = WEB_DIR / "output" / "index.html"
PDF_DIR = ROOT_DIR / "pdf"


def test_yaml_is_valid():
    """Ensure the resume.yaml is valid and contains required keys."""
    assert DATA_PATH.exists(), "resume.yaml file is missing!"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "YAML should parse as a dictionary"
    assert "name" in data, "Resume must have a 'name' field"
    assert "experience" in data, "Resume must have an 'experience' section"


def test_jinja_templates_syntax():
    """Parse all .j2 templates to ensure there are no syntax errors."""
    env = Environment(loader=FileSystemLoader(WEB_DIR / "templates"))

    # Iterate through all templates and parse them (throws exception on bad syntax)
    for root, _, files in os.walk(WEB_DIR / "templates"):
        for file in files:
            if file.endswith(".j2"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    source = f.read()
                    env.parse(source)  # Validates syntax without needing context


def test_web_build_script():
    """Run the web build script and check if index.html is generated correctly."""
    # Run the script
    result = subprocess.run(
        ["python3", "build.py"], cwd=WEB_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, f"Web build failed: {result.stderr}"

    # Verify output file exists
    assert WEB_OUTPUT.exists(), "index.html was not generated"

    # Verify basic HTML structure
    with open(WEB_OUTPUT, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<!DOCTYPE html>" in content, "Missing DOCTYPE declaration"
    assert '<html lang="en">' in content, "Missing HTML tag"
    assert "Jerome Goh" in content, "Resume data was not injected into HTML"


def test_pdf_build_script():
    """Run the PDF build script to ensure LaTeX compiles successfully."""
    # Requires LaTeX installed on the system running the test
    result = subprocess.run(
        ["python3", "build.py"], cwd=PDF_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, f"PDF build failed: {result.stderr}"
