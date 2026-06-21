import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def parse_html_content(html_content: str, url: str) -> dict:
    """
    Parses HTML content, extracting title, description, headings,
    structured JSON-LD data, and cleanses the main text into markdown.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract Structured Data (JSON-LD) BEFORE decomposing script tags
    structured_data = []
    for ld_json in soup.find_all("script", type="application/ld+json"):
        try:
            content = ld_json.get_text().strip()
            if content:
                data = json.loads(content)
                if isinstance(data, list):
                    structured_data.extend(data)
                else:
                    structured_data.append(data)
        except Exception:
            continue  # Ignore invalid json-ld
            
    # Remove script and style elements to avoid noise in content
    for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
        script_or_style.decompose()
        
    # Extract Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.h1:
        title = soup.h1.get_text().strip()
        
    # Extract Meta Description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag.get("content").strip()
        
    # Extract Headings (H1 to H4)
    headings = []
    for level in ["h1", "h2", "h3", "h4"]:
        for heading in soup.find_all(level):
            heading_text = heading.get_text().strip()
            if heading_text:
                headings.append({
                    "tag": level,
                    "text": heading_text
                })
            
    # Clean and extract main text content as basic markdown
    # Replace headers with markdown equivalent, format links slightly, extract lists
    body_text = []
    
    # We will traverse through paragraphs, bullet points, headers, etc.
    # To keep it simple and clean, extract text block by block
    for elem in soup.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
        elem_text = elem.get_text().strip()
        if not elem_text:
            continue
            
        if elem.name == "p":
            body_text.append(elem_text)
        elif elem.name in ["h1", "h2", "h3", "h4"]:
            level_marker = "#" * int(elem.name[1])
            body_text.append(f"\n{level_marker} {elem_text}\n")
        elif elem.name == "li":
            body_text.append(f"* {elem_text}")
            
    markdown_content = "\n".join(body_text)
    # Deduplicate successive newlines
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content).strip()
    
    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "markdown_content": markdown_content,
        "headings": headings,
        "structured_data": structured_data
    }
