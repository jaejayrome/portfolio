import yaml
import subprocess
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup, NavigableString

# --- CONFIGURATION: Add new tags here easily ---
TAG_MAP = {
    "strong": r"\textbf",
    "b": r"\textbf",
    "em": r"\textit",
    "i": r"\textit",
    "u": r"\underline",
    "code": r"\texttt",
}


def tex_escape(text):
    """
    Escapes characters that have special meaning in LaTeX.
    """
    if not isinstance(text, str):
        return text

    conv = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
        "<": r"\textless{}",
        ">": r"\textgreater{}",
    }

    # Simple regex to replace all special chars
    regex = re.compile("|".join(re.escape(k) for k in conv.keys()))
    return regex.sub(lambda m: conv[m.group()], text)


def parse_html_to_latex(soup_element):
    """
    Recursively traverses the HTML tree and converts to LaTeX.
    """
    result = []

    for child in soup_element.children:
        if isinstance(child, NavigableString):
            # If it's plain text, JUST escape it.
            result.append(tex_escape(str(child)))
        elif child.name in TAG_MAP:
            # If it's a known tag, wrap the inner content in the LaTeX command
            latex_cmd = TAG_MAP[child.name]
            inner_text = parse_html_to_latex(child)
            result.append(f"{latex_cmd}{{{inner_text}}}")
        else:
            # If unknown tag, just render the text inside
            result.append(parse_html_to_latex(child))

    return "".join(result)


def format_latex(text):
    """
    The main filter function called by Jinja2.
    """
    if not isinstance(text, str):
        return text

    soup = BeautifulSoup(f"<span>{text}</span>", "html.parser")
    return parse_html_to_latex(soup.find("span"))


# --- MAIN EXECUTION ---

root = Path(__file__).resolve().parent
data_path = root.parent / "data" / "resume.yaml"

env = Environment(
    loader=FileSystemLoader(searchpath="./templates"),
    block_start_string="{%",
    block_end_string="%}",
    variable_start_string="{{",
    variable_end_string="}}",
    comment_start_string="((#",
    comment_end_string="#))",
)

# Register the filters
env.filters["format_latex"] = format_latex
env.filters["tex_escape"] = tex_escape

# Load Data
data = yaml.safe_load(data_path.read_text())

# Render Template
template = env.get_template("resume.tex.j2")
tex = template.render(**data)

output_dir = root / "output"
output_dir.mkdir(exist_ok=True)
tex_path = output_dir / "resume.tex"
tex_path.write_text(tex)

# Compile PDF
try:
    print("Compiling PDF...")
    subprocess.run(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory",
            str(output_dir),
            str(tex_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print(f"Success! PDF generated at: {output_dir / 'resume.pdf'}")
except subprocess.CalledProcessError:
    print("Error: pdflatex failed. Check the log file in the output directory.")
