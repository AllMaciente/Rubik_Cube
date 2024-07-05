import os
import shutil
import subprocess
from pathlib import Path

import markdown
import pdfkit

# prefix components:
space = "    "
branch = "    "
# pointers:
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
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        display_name = path.name  # Keep the file extension
        link = f"{display_name}"  # Create the link for the file with .md
        page_map[display_name] = link  # Add entry to page_map
        yield f'{prefix}{pointer}<a href="{link}">{display_name}</a>'
        if path.is_dir():  # Extend the prefix and recurse:
            extension = branch if pointer == tee else space
            # i.e., space because last, └── , above so no more |
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
    # Ensure HTML content is properly encoded in UTF-8
    html_content = f'<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>{html_content}</body></html>'

    # Create pdfkit configuration
    config = (
        pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path) if wkhtmltopdf_path else None
    )

    # Add footer with page numbers
    options = {
        "encoding": "UTF-8",
        "footer-right": "[page]",
        "footer-font-size": "10",
        "no-outline": None,  # Disable outlines for links
    }

    # Convert the HTML content to PDF
    pdfkit.from_string(html_content, output_file, configuration=config, options=options)


def create_summary_without_pages(file_map):
    """Create a summary section without page numbers"""
    summary = "<h1>Sumário</h1>\n"
    for file_name, link in file_map.items():
        summary += f'<p><a href="{link}">{file_name}</a></p>\n'
    return summary


def update_readme_with_links(file_map, file_tree):
    """Update README.md with links to the PDF pages"""
    readme_content = ""
    if readme_file.exists():
        with readme_file.open("r", encoding="utf-8") as file:
            readme_content = file.read()

    summary_content = create_summary_without_pages(file_map)

    # Find the position of "# Sumário" and replace the old file tree with the new one
    summary_position = readme_content.find("# Sumário")
    if summary_position != -1:
        summary_position_end = readme_content.find("\n", summary_position)
        if summary_position_end != -1:
            next_section_position = readme_content.find("#", summary_position_end + 1)
            if next_section_position == -1:
                next_section_position = len(readme_content)
            readme_content = (
                readme_content[: summary_position_end + 1]
                + "\n\n"
                + summary_content
                + "\n\n"
                + file_tree
                + "\n\n"
                + readme_content[next_section_position:]
            )

    # Save the updated README.md
    with readme_file.open("w", encoding="utf-8") as file:
        file.write(readme_content)


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
    # Read the content of README.md
    readme_content = ""
    if readme_file in markdown_files:
        with readme_file.open("r", encoding="utf-8") as file:
            readme_content = file.read()
        markdown_files.remove(readme_file)

    # Generate file tree with page mapping
    page_map = {}
    file_tree = "\n".join(tree(Path("."), page_map=page_map))

    # Update README.md with links
    update_readme_with_links(page_map, file_tree)

    # Read the content of all other markdown files
    combined_content = (
        readme_content
        + "\n<div style='page-break-before: always;'></div>\n"
        + read_markdown_files(markdown_files)
    )

    # Path to the wkhtmltopdf executable
    wkhtmltopdf_path = shutil.which("wkhtmltopdf")
    if wkhtmltopdf_path is None:
        raise FileNotFoundError(
            "wkhtmltopdf executable not found. Please install wkhtmltopdf."
        )

    # Convert combined markdown content to PDF
    output_pdf = "RubikCube.pdf"
    convert_markdown_to_pdf(combined_content, output_pdf, wkhtmltopdf_path)

    print(f"PDF created successfully: {output_pdf}")
    print(f"README.md updated successfully.")

    # Git commands to add, commit, and push changes
    try:
        subprocess.run(["git", "add", "*"], check=True)
        subprocess.run(["git", "commit", "-m", "Add"], check=True)
        # Note: Update the remote repository URL and branch name accordingly
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running git commands: {e}")
