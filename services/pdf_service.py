import os
import io
import json
import logging
from PIL import Image
from flask import current_app

# Try importing dependencies and handle missing imports gracefully
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

logger = logging.getLogger(__name__)

def extract_pdf_content(filepath):
    """
    Extracts text, tables, headings, captions, footnotes, lists and counts images in a PDF.
    Caches the result to a JSON file to avoid parsing twice.
    
    Returns:
        dict: A dictionary containing 'text', 'pages_text', 'tables', 'headings', 'captions', 'footnotes', 'lists', and 'metadata'.
    """
    cache_path = filepath + ".json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                logger.info(f"Loading cached PDF content from {cache_path}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read cache file {cache_path}: {e}")

    result = {
        "text": "",
        "pages_text": [],
        "tables": [],
        "headings": [],
        "captions": [],
        "footnotes": [],
        "lists": [],
        "metadata": {
            "pages": 0,
            "images_count": 0,
            "tables_count": 0,
            "ocr_performed": False
        }
    }
    
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        result["text"] = "Error: PDF file path does not exist."
        return result

    # Setup pytesseract custom command if specified in configuration
    if pytesseract and current_app:
        tesseract_cmd = current_app.config.get('TESSERACT_CMD', '')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    raw_text_list = []
    tables_list = []
    headings_list = []
    captions_list = []
    footnotes_list = []
    lists_list = []
    images_count = 0
    pages_count = 0

    # 1. Parse using PyMuPDF (fitz) - fast, reliable, provides text layout blocks
    if fitz:
        try:
            doc = fitz.open(filepath)
            pages_count = len(doc)
            result["metadata"]["pages"] = pages_count
            
            for page_idx, page in enumerate(doc):
                page_text = page.get_text("text")
                raw_text_list.append(page_text)
                
                # Image count
                try:
                    images_count += len(page.get_images(full=True))
                except Exception:
                    pass
                
                # Extract structural layout elements (headings, captions, footnotes, lists)
                try:
                    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, "text", block_no, block_type)
                    page_height = page.rect.height
                    
                    for b in blocks:
                        if len(b) >= 5 and b[6] == 0:  # text block
                            block_text = b[4].strip()
                            if not block_text:
                                continue
                            
                            lines = [line.strip() for line in block_text.split("\n") if line.strip()]
                            for line in lines:
                                # Headings heuristics
                                if (3 < len(line) < 100 and 
                                    (line.isupper() or line.istitle() or line.startswith(("Chapter", "Section", "Part"))) and 
                                    not line.endswith((".", ",", ";", ":"))):
                                    headings_list.append(line)
                                    
                                # Captions heuristics
                                if (line.lower().startswith(("figure", "fig.", "table", "chart", "map", "image")) and 
                                    len(line) > 10):
                                    captions_list.append(line)
                                    
                                # Lists heuristics
                                if line.startswith(("•", "-", "*", "▪", "◦")) or (len(line) > 2 and line[0].isdigit() and line[1] in (".", ")")):
                                    lists_list.append(line)
                                    
                            # Footnotes heuristics
                            y0 = b[1]
                            if y0 > page_height * 0.85:
                                first_line = lines[0] if lines else ""
                                if first_line.startswith(("*", "†", "‡", "§", "[", "(")) or (len(first_line) > 0 and first_line[0].isdigit()):
                                    footnotes_list.append(block_text)
                except Exception as b_err:
                    logger.error(f"Error parsing layout blocks on page {page_idx}: {b_err}")
        except Exception as e:
            logger.error(f"PyMuPDF parsing failed: {str(e)}")

    # 2. Parse tables and backup text using pdfplumber
    if pdfplumber:
        try:
            with pdfplumber.open(filepath) as pdf:
                if pages_count == 0:
                    pages_count = len(pdf.pages)
                    result["metadata"]["pages"] = pages_count
                
                for idx, plumber_page in enumerate(pdf.pages):
                    # If PyMuPDF failed/not imported, use pdfplumber for text
                    if not fitz:
                        page_text = plumber_page.extract_text()
                        if page_text:
                            raw_text_list.append(page_text)
                    
                    # Extract Tables
                    try:
                        tables = plumber_page.extract_tables()
                        for table in tables:
                            if table:
                                cleaned_table = [[cell if cell is not None else "" for cell in row] for row in table]
                                tables_list.append(cleaned_table)
                    except Exception as t_err:
                        logger.error(f"Table extraction failed on page {idx}: {t_err}")
                    finally:
                        plumber_page.flush_cache()  # Free memory
        except Exception as e:
            logger.error(f"pdfplumber table extraction failed: {str(e)}")

    result["metadata"]["images_count"] = images_count
    result["metadata"]["tables_count"] = len(tables_list)
    result["tables"] = tables_list
    
    # De-duplicate elements
    def get_unique_elements(lst, limit):
        seen = set()
        unique = []
        for x in lst:
            if x.lower() not in seen:
                seen.add(x.lower())
                unique.append(x)
        return unique[:limit]

    result["headings"] = get_unique_elements(headings_list, 30)
    result["captions"] = get_unique_elements(captions_list, 30)
    result["footnotes"] = get_unique_elements(footnotes_list, 30)
    result["lists"] = get_unique_elements(lists_list, 50)
    result["pages_text"] = raw_text_list
    
    full_text = "\n\n".join(raw_text_list).strip()

    # 3. OCR Fallback if text is empty/very short (scanned PDF)
    char_count = len(full_text)
    if char_count < 200 and fitz:
        logger.info(f"Sparse text ({char_count} chars). Initiating OCR fallback...")
        ocr_text_list = []
        try:
            doc = fitz.open(filepath)
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                if pytesseract:
                    page_text = pytesseract.image_to_string(img)
                    if page_text:
                        ocr_text_list.append(page_text)
                else:
                    ocr_text_list.append(f"\n[OCR Error: Pytesseract is not available or configured. Cannot parse scanned page {page_num+1}]\n")
            
            if ocr_text_list:
                result["pages_text"] = ocr_text_list
                full_text = "\n\n".join(ocr_text_list).strip()
                result["metadata"]["ocr_performed"] = True
        except Exception as ocr_err:
            logger.error(f"OCR execution failed: {str(ocr_err)}")
            full_text += f"\n[OCR failure: {str(ocr_err)}]\n"

    result["text"] = full_text

    # Write cache to JSON file
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved extracted PDF content to cache: {cache_path}")
    except Exception as e:
        logger.error(f"Failed to write PDF cache file: {str(e)}")

    return result
