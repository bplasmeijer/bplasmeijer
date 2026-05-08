#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import mimetypes
import pathlib
import re
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0 Safari/537.36"


def strip_markdown_links(text: str) -> str:
    text = text.replace(")[(", ") [(")
    text = re.sub(r"\)\[", ") [", text)
    return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)


def clean_text(text: str) -> str:
    text = strip_markdown_links(text)
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"#", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:72].strip("-") or "linkedin-post"


def extract_published_date(raw_text: str) -> str:
    match = re.search(r"^Published Time:\s*(\d{4}-\d{2}-\d{2})", raw_text, re.MULTILINE)
    if match:
        return match.group(1)
    return dt.date.today().isoformat()


def extract_title(raw_text: str, body: str) -> str:
    # Try to extract from "Title:" field first (new format)
    match = re.search(r"^Title:\s*(.+?)$", raw_text, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        if title and len(title) > 5:
            return title[:120].rstrip()
    
    # Fallback to first sentence of body
    sentence = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0].strip()
    if sentence:
        return sentence[:120].rstrip()
    return "LinkedIn Post"


def extract_post_section(raw_text: str) -> list[str]:
    lines = raw_text.splitlines()
    start_index = None

    # Try to find "Markdown Content:" section first (new format)
    for index, line in enumerate(lines):
        if "Markdown Content:" in line:
            start_index = index + 1
            break
    
    # Fallback to old format with "Report this post"
    if start_index is None:
        for index, line in enumerate(lines):
            if "Report this post" in line:
                start_index = index + 1
                break

    if start_index is None:
        raise ValueError("Could not find LinkedIn post body anchor in mirrored content")

    section_lines: list[str] = []
    stop_prefixes = (
        "[Like]",
        "Share",
        "To view or add a comment",
        "## More from this author",
        "## More Relevant Posts",
        "## Explore content categories",
    )

    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith(stop_prefixes):
            break
        section_lines.append(line)

    return section_lines


def should_skip_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if "![Image" in stripped:
        return True
    skip_prefixes = (
        "Title:",
        "URL Source:",
        "Published Time:",
        "Markdown Content:",
        "## ",
        "# ",
        "Agree & Join LinkedIn",
        "By clicking Continue",
        "[](https://",
        "![Image",
        "*   [",
        "[Like]",
        "[Comment]",
        "Share",
        "To view or add a comment",
        "[View Profile]",
        "[Follow]",
        "## More from this author",
        "## More Relevant Posts",
        "## Explore content categories",
    )
    if stripped in {"22h", "1d", "2d", "3d", "4d", "5d", "6d", "1w"}:
        return True
    if stripped.endswith("followers"):
        return True
    if stripped.endswith("Posts]") or stripped.endswith("Article]"):
        return True
    # Skip lines that are just links
    if stripped.startswith("[](https://"):
        return True
    return stripped.startswith(skip_prefixes)


def extract_body(raw_text: str) -> str:
    lines = extract_post_section(raw_text)
    body_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if should_skip_line(stripped):
            continue

        candidate = clean_text(stripped)
        if candidate and len(candidate) > 20:
            body_lines.append(candidate)

    body = "\n\n".join(body_lines).strip()
    if not body:
        raise ValueError("Could not extract LinkedIn post body from mirrored content")
    return body


def extract_tags(body: str) -> list[str]:
    tags = []
    seen: set[str] = set()
    for tag in re.findall(r"#([A-Za-z0-9][A-Za-z0-9_-]*)", body):
        normalized = tag.lower()
        if normalized not in seen:
            tags.append(normalized)
            seen.add(normalized)
    return tags


def extract_image_urls(raw_text: str) -> list[str]:
    image_urls: list[str] = []
    seen: set[str] = set()

    for line in extract_post_section(raw_text):
        for url in re.findall(r"!\[[^\]]*\]\((https://[^)]+)\)", line):
            if "media.licdn.com" not in url:
                continue
            if url not in seen:
                image_urls.append(url)
                seen.add(url)

    return image_urls


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def infer_source_url(post_url: str) -> str:
    parsed = urlparse(post_url)
    if parsed.scheme and parsed.netloc:
        return post_url
    raise ValueError("post_url must be an absolute URL")


def infer_image_extension(content_type: str | None, image_url: str) -> str:
    extension = ""
    if content_type:
        extension = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
    if not extension:
        extension = pathlib.Path(urlparse(image_url).path).suffix
    if extension == ".jpe":
        extension = ".jpg"
    return extension or ".jpg"


def download_image(image_url: str) -> tuple[bytes, str] | tuple[None, None]:
    try:
        request = Request(image_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=30) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "")
        return content, content_type
    except Exception as e:
        print(f"Warning: Failed to download image {image_url}: {e}", file=sys.stderr)
        return None, None


def write_images(image_urls: list[str], image_dir: pathlib.Path, slug: str) -> list[str]:
    image_dir.mkdir(parents=True, exist_ok=True)
    relative_paths: list[str] = []

    for index, image_url in enumerate(image_urls, start=1):
        content, content_type = download_image(image_url)
        if content is None:
            # Skip images that fail to download
            continue
        extension = infer_image_extension(content_type, image_url)
        file_name = f"{slug}-{index}{extension}"
        file_path = image_dir / file_name
        file_path.write_bytes(content)
        relative_paths.append(f"/images/linkedin/{file_name}")

    return relative_paths


def build_front_matter(title: str, date_value: str, tags: list[str], post_url: str) -> str:
    lines = [
        "+++",
        f'title = "{escape_toml_string(title)}"',
        f'date = "{date_value}"',
        "draft = true",
        "type = \"post\"",
        f'linkedin_url = "{escape_toml_string(post_url)}"',
    ]
    if tags:
        rendered_tags = ", ".join(f'"{escape_toml_string(tag)}"' for tag in tags)
        lines.append(f"tags = [{rendered_tags}]")
    lines.append("+++")
    return "\n".join(lines)


def write_post(output_dir: pathlib.Path, image_dir: pathlib.Path, title: str, date_value: str, body: str, post_url: str, image_urls: list[str], slug_override: str | None, overwrite: bool) -> pathlib.Path:
    slug = slug_override or slugify(title)
    file_path = output_dir / f"{date_value}-{slug}.md"
    if file_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing post: {file_path}")

    tags = extract_tags(body)
    front_matter = build_front_matter(title, date_value, tags, post_url)
    image_paths = write_images(image_urls, image_dir, slug) if image_urls else []
    image_block = ""
    if image_paths:
        image_block = "\n\n" + "\n\n".join(f"![LinkedIn image {index}]({path})" for index, path in enumerate(image_paths, start=1))
    content = f"{front_matter}\n\n{body}{image_block}\n\nSource: [LinkedIn]({post_url})\n"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert mirrored LinkedIn post content into a Hugo markdown draft")
    parser.add_argument("--input", required=True, help="Path to the mirrored LinkedIn markdown text")
    parser.add_argument("--output-dir", required=True, help="Directory to write the Hugo post into")
    parser.add_argument("--image-dir", default="static/images/linkedin", help="Directory to write downloaded LinkedIn post images into")
    parser.add_argument("--post-url", required=True, help="Original LinkedIn post URL")
    parser.add_argument("--slug", default="", help="Optional slug override")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing generated post with the same date and slug")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output_dir)
    image_dir = pathlib.Path(args.image_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    raw_text = input_path.read_text(encoding="utf-8")
    body = extract_body(raw_text)
    image_urls = extract_image_urls(raw_text)
    title = extract_title(raw_text, body)
    date_value = extract_published_date(raw_text)
    post_url = infer_source_url(args.post_url)
    output_path = write_post(output_dir, image_dir, title, date_value, body, post_url, image_urls, args.slug.strip() or None, args.overwrite)

    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())