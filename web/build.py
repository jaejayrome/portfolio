import yaml
import re
import markdown
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def summarize_bullet(bullet):
    """
    Takes a verbose PDF bullet and makes it web-friendly.
    Extracts the first <strong> block as a title, and takes the first sentence.
    """
    match = re.search(r"<strong>(.*?)</strong>(.*)", bullet)
    if match:
        title = match.group(1).replace(":", "").strip()
        # Strip remaining HTML tags from the rest of the text
        rest_clean = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        # Truncate to the first sentence
        short_desc = rest_clean.split(".")[0] + "."
        return {"title": title, "desc": short_desc}

    # Fallback
    clean_text = re.sub(r"<[^>]+>", "", bullet).strip()
    return {"title": "Highlight", "desc": clean_text.split(".")[0] + "."}


def build_static_site():
    web_dir = Path(__file__).parent
    base_dir = web_dir.parent
    output_dir = web_dir / "output"

    # Setup Jinja environment
    env = Environment(loader=FileSystemLoader(web_dir / "templates"))

    # 1. Load and process Resume Data
    with open(base_dir / "data" / "resume.yaml", "r") as f:
        resume_data = yaml.safe_load(f)

    # Inject shortened bullets into the dictionary for the web
    for exp in resume_data.get("experience", []):
        exp["short_bullets"] = [summarize_bullet(b) for b in exp.get("bullets", [])]

    # 2. Render Index (Home) Page
    output_dir.mkdir(parents=True, exist_ok=True)
    index_template = env.get_template("index.html.j2")
    with open(output_dir / "index.html", "w") as f:
        f.write(index_template.render(resume=resume_data))

    # 3. Process Blogs
    blogs_dir = base_dir / "data" / "blogs"
    blog_output_dir = output_dir / "blog"
    blog_output_dir.mkdir(exist_ok=True)

    blog_posts = []
    if blogs_dir.exists():
        md = markdown.Markdown(
            extensions=["meta"]
        )  # Parses markdown with metadata headers
        for filepath in blogs_dir.glob("*.md"):
            with open(filepath, "r") as f:
                html_content = md.convert(f.read())
                # Extract metadata (e.g., Title, Date) from the top of the markdown file
                meta = {k: v[0] for k, v in md.Meta.items()} if md.Meta else {}

                post_data = {
                    "slug": filepath.stem,
                    "title": meta.get("title", "Untitled"),
                    "date": meta.get("date", ""),
                    "content": html_content,
                }
                blog_posts.append(post_data)

                # Render individual blog post page
                post_template = env.get_template("blog_post.html.j2")
                post_dir = blog_output_dir / post_data["slug"]
                post_dir.mkdir(exist_ok=True)
                with open(post_dir / "index.html", "w") as out_f:
                    out_f.write(
                        post_template.render(resume=resume_data, post=post_data)
                    )

    # 4. Render Blog Index Page
    # Sort posts by date descending
    blog_posts.sort(key=lambda x: x["date"], reverse=True)
    blog_index_template = env.get_template("blog_index.html.j2")
    with open(blog_output_dir / "index.html", "w") as f:
        f.write(blog_index_template.render(resume=resume_data, blogs=blog_posts))

    print("🚀 Multi-page static site successfully built!")


if __name__ == "__main__":
    build_static_site()

