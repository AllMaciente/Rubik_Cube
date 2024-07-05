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


def tree(dir_path: Path, prefix: str = ""):
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """
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
        display_name = path.stem  # Remove the file extension
        yield prefix + pointer + display_name
        if path.is_dir():  # extend the prefix and recurse:
            extension = branch if pointer == tee else space
            # i.e. space because last, └── , above so no more |
            yield from tree(path, prefix=prefix + extension)


def read_markdown_files(file_paths):
    """Read markdown files and return their content"""
    content = ""
    for file_path in file_paths:
        with file_path.open("r", encoding="utf-8") as file:
            content += (
                f'<div style="page-break-before: always;"></div>\n# {file_path.stem}\n\n'
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

    # Convert the HTML content to PDF
    pdfkit.from_string(
        html_content, output_file, configuration=config, options={"encoding": "UTF-8"}
    )


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

    # Generate file tree
    file_tree = "\n".join(tree(Path(".")))

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
                + file_tree
                + "\n\n"
                + readme_content[next_section_position:]
            )

    # Save the updated README.md
    with readme_file.open("w", encoding="utf-8") as file:
        file.write(readme_content)

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
