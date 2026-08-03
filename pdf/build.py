import sys
import yaml
import subprocess
import re
import shutil
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


def build_contact_parts(profile):
    """
    Builds the list of header contact items (already valid LaTeX) for a
    profile. LinkedIn/GitHub are only included when the profile defines them,
    so profiles that omit a contact channel (e.g. no LinkedIn) don't render
    an empty/broken link. Each template joins/separates these as it likes.
    """
    parts = [
        rf"\href{{mailto:{profile['email']}}}{{ {tex_escape(profile['email'])} }}",
        tex_escape(profile["mobile"]),
    ]
    if profile.get("linkedin"):
        parts.append(rf"\href{{https://{profile['linkedin']}}}{{LinkedIn}}")
    if profile.get("github"):
        parts.append(rf"\href{{https://{profile['github']}}}{{GitHub}}")
    parts.append(tex_escape(profile["location"]))
    return parts


def build_header_blocks(profile):
    """
    Splits a profile's contact info into two blocks for two-column header
    layouts: a contact block (email/mobile/location) and a links block
    (LinkedIn/GitHub, only the ones the profile actually defines). If a
    profile has neither, links_block is empty and the template should skip
    that column entirely rather than render a blank one.
    """
    contact_block = [
        rf"\href{{mailto:{profile['email']}}}{{ {tex_escape(profile['email'])} }}",
        tex_escape(profile["mobile"]),
        tex_escape(profile["location"]),
    ]
    links_block = []
    if profile.get("linkedin"):
        links_block.append(rf"\href{{https://{profile['linkedin']}}}{{{tex_escape(profile['linkedin'])}}}")
    if profile.get("github"):
        links_block.append(rf"\href{{https://{profile['github']}}}{{{tex_escape(profile['github'])}}}")
    return contact_block, links_block


# --- MAIN EXECUTION ---

# Numeric shortcuts for the CLI: `uv run build.py <format> <profile>`
FORMAT_ALIASES = {
    "1": "resume",
    "2": "resume_compact",
    "3": "resume_elegant",
    "4": "resume_sidebar",
    "5": "resume_minimal",
    "6": "resume_professional",
}

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
profiles = data.pop("profiles")

# Numeric shortcuts for profiles, e.g. 1=primary, 2=secondary, following
# the order they're declared in resume.yaml.
PROFILE_ALIASES = {str(i + 1): key for i, key in enumerate(profiles.keys())}

if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "list"):
    print("Formats:")
    for num, name in FORMAT_ALIASES.items():
        print(f"  {num} = {name}")
    print("Profiles:")
    for num, name in PROFILE_ALIASES.items():
        print(f"  {num} = {name}")
    print('\nUsage: uv run build.py [format] [profile]  (or "all" for either)')
    sys.exit(0)

# Select template: `uv run build.py <format>` renders templates/<name>.tex.j2
# (default "resume"). <format> can be a number (see FORMAT_ALIASES), a
# template name, or "all" to render every resume_*.tex.j2 layout.
template_arg = sys.argv[1] if len(sys.argv) > 1 else "resume"
template_arg = FORMAT_ALIASES.get(template_arg, template_arg)
if template_arg == "all":
    template_names = ["resume"] + sorted(
        p.stem.removesuffix(".tex") for p in (root / "templates").glob("resume_*.tex.j2")
    )
else:
    template_names = [template_arg]

# Select profile (contact info): `uv run build.py <format> <profile>`
# (default "primary"). <profile> can be a number (see PROFILE_ALIASES), a
# profile name, or "all" to render every profile.
profile_arg = sys.argv[2] if len(sys.argv) > 2 else "primary"
profile_arg = PROFILE_ALIASES.get(profile_arg, profile_arg)
if profile_arg == "all":
    profile_names = list(profiles.keys())
else:
    profile_names = [profile_arg]

output_dir = root / "output"
output_dir.mkdir(exist_ok=True)

# Only suffix the output filename with the profile name when there's a choice
# to disambiguate, so the default invocation keeps producing "resume.pdf".
suffix_profile = len(profile_names) > 1 or profile_names[0] != "primary"

for template_name in template_names:
    template = env.get_template(f"{template_name}.tex.j2")

    for profile_name in profile_names:
        profile = profiles[profile_name]
        contact_block, links_block = build_header_blocks(profile)
        context = {
            **data,
            **profile,
            "contact_parts": build_contact_parts(profile),
            "contact_block": contact_block,
            "links_block": links_block,
        }
        tex = template.render(**context)

        output_name = f"{template_name}_{profile_name}" if suffix_profile else template_name
        tex_path = output_dir / f"{output_name}.tex"
        tex_path.write_text(tex)

        # Compile PDF
        try:
            print(f"Compiling {output_name}...")
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

            # Package: move the compiled PDF into its own <format>_<profile>
            # subdirectory under a fixed filename, so every combo produces a
            # ready-to-submit "jerome_goh_resume.pdf" regardless of format/profile.
            package_dir = output_dir / f"{template_name}_{profile_name}"
            package_dir.mkdir(exist_ok=True)
            final_pdf = package_dir / "jerome_goh_resume.pdf"
            shutil.move(str(output_dir / f"{output_name}.pdf"), str(final_pdf))
            print(f"Success! Ready to submit: {final_pdf}")
        except subprocess.CalledProcessError:
            print(f"Error: pdflatex failed for {output_name}. Check the log file in the output directory.")
