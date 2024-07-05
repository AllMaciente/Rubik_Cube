import os
import shutil
import subprocess
from pathlib import Path

import markdown
import pdfkit

# Prefix components for tree structure:
space = "    "
branch = "    "
tee = "  - "
last = "   - "


def tree(dir_path: Path, prefix: str = "", page_map: dict = None):
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """
    if page_map is None:
        page_map = {}

    contents = sorted(
        p
        for p in dir_path.iterdir()
        if not (
            p.name.startswith(".") or p.name.endswith(".py") or p.name.endswith(".pdf")
        )
    )
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        display_name = path.name  # Keep the file extension
        link = f"{display_name}"  # Link to the file with .md extension
        page_map[display_name] = link  # Add entry to page_map
        yield f'{prefix}{pointer}<a href="{link}">{display_name}</a>'
        if path.is_dir():  # Extend the prefix and recurse:
            extension = branch if pointer == tee else space
            yield from tree(path, prefix=prefix + extension, page_map=page_map)


def read_markdown_files(file_paths):
    """Read markdown files and return their content"""
    content = ""
    for file_path in file_paths:
        with file_path.open("r", encoding="utf-8") as file:
            content += (
                f'<div style="page-break-before: always;"></div>\n<h1 id="{file_path.stem}">{file_path.stem}</h1>\n\n'
                + file.read()
                + "\n\n"
            )
    return content


def convert_markdown_to_pdf(md_content, output_file, wkhtmltopdf_path=None):
    """Convert markdown content to PDF"""
    html_content = markdown.markdown(md_content)
    html_content = f'<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>{html_content}</body></html>'

    config = (
        pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path) if wkhtmltopdf_path else None
    )
    options = {
        "encoding": "UTF-8",
        "footer-right": "[page]",
        "footer-font-size": "10",
        "no-outline": None,
    }

    pdfkit.from_string(html_content, output_file, configuration=config, options=options)


def create_summary_as_tree(file_map):
    """Create a summary section in tree format with links"""
    summary = "<h1>Sumário</h1>\n"
    for line in file_map.values():
        summary += f"{line}\n"
    return summary


def update_readme_with_tree(file_map):
    """Update README.md with tree structure of files"""
    if not readme_file.exists():
        print(f"{readme_file} does not exist.")
        return

    with readme_file.open("r", encoding="utf-8") as file:
        readme_content = file.read()

    summary_position = readme_content.find("# Sumário")
    if summary_position != -1:
        summary_position_end = readme_content.find("\n", summary_position)
        if summary_position_end != -1:
            next_section_position = readme_content.find("#", summary_position_end + 1)
            if next_section_position == -1:
                next_section_position = len(readme_content)
            readme_content = (
                readme_content[:summary_position]
                + readme_content[next_section_position:]
            )

    summary_content = create_summary_as_tree(file_map)
    updated_content = readme_content + "\n\n" + summary_content

    with readme_file.open("w", encoding="utf-8") as file:
        file.write(updated_content)


# Generate the list of markdown files following the tree structure
markdown_files = [p for p in Path(".").rglob("*.md") if not p.name.startswith(".")]

# Ensure README.md is the first file
readme_file = Path("README.md")
if readme_file in markdown_files:
    markdown_files.remove(readme_file)
    markdown_files.insert(0, readme_file)

if not markdown_files:
    print("No markdown files found.")
else:
    readme_content = ""
    if readme_file in markdown_files:
        with readme_file.open("r", encoding="utf-8") as file:
            readme_content = file.read()
        markdown_files.remove(readme_file)

    page_map = {}
    file_tree = "\n".join(tree(Path("."), page_map=page_map))

    update_readme_with_tree(page_map)

    combined_content = (
        readme_content
        + "\n<div style='page-break-before: always;'></div>\n"
        + read_markdown_files(markdown_files)
    )

    wkhtmltopdf_path = shutil.which("wkhtmltopdf")
    if wkhtmltopdf_path is None:
        raise FileNotFoundError(
            "wkhtmltopdf executable not found. Please install wkhtmltopdf."
        )

    output_pdf = "RubikCube.pdf"
    convert_markdown_to_pdf(combined_content, output_pdf, wkhtmltopdf_path)

    print(f"PDF created successfully: {output_pdf}")
    print(f"README.md updated successfully.")

    try:
        subprocess.run(["git", "add", "*"], check=True)
        subprocess.run(["git", "commit", "-m", "Add"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running git commands: {e}")
