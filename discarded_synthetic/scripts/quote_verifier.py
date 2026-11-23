import re
import unicodedata
from typing import Tuple, Dict, Any

def normalize_text(text: str) -> str:
    """Normalize whitespace, quotes, dashes, and casing for robust text matching."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    # Replace smart quotes and special hyphens with standard ASCII
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    text = text.replace('—', '-').replace('–', '-').replace('…', '...')
    # Normalize multiple whitespace / newlines to single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

def verify_quote_in_text(quote: str, source_text: str) -> Tuple[bool, float, str]:
    """
    Checks if a quote exists verbatim or near-verbatim in the source text.
    Returns:
      (is_verified: bool, match_ratio: float, details: str)
    """
    if not quote or quote.lower() == "unknown":
        return True, 1.0, "Quote is marked unknown (no claim made)"
    if not source_text:
        return False, 0.0, "Source text is empty or unavailable"

    norm_quote = normalize_text(quote)
    norm_source = normalize_text(source_text)

    # 1. Exact verbatim substring check
    if norm_quote in norm_source:
        return True, 1.0, "Exact verbatim match confirmed"

    # 2. Check if a substantial subclause (>= 80% length) matches
    words = norm_quote.split()
    if len(words) >= 6:
        window_size = len(words)
        # Check consecutive 5-word chunks
        chunk_size = 5
        found_chunks = 0
        total_chunks = max(1, len(words) - chunk_size + 1)
        for i in range(total_chunks):
            sub = " ".join(words[i:i+chunk_size])
            if sub in norm_source:
                found_chunks += 1
        
        ratio = found_chunks / total_chunks
        if ratio >= 0.8:
            return True, ratio, f"Near-verbatim match ({ratio*100:.1f}% sequence overlap)"
        elif ratio > 0.3:
            return False, ratio, f"Partial fragment found ({ratio*100:.1f}%), potential paraphrase or hallucination"

    return False, 0.0, "Quote not found in source text (Planted or Hallucinated)"

def verify_record_evidence(record: Dict[str, Any], page_cache: Dict[str, str]) -> Dict[str, Any]:
    """
    Verifies all evidence quotes in a record against cached page text.
    """
    evidence = record.get("evidence", {})
    docs_url = evidence.get("docs_url", "")
    source_text = page_cache.get(docs_url, "")

    results = {}
    all_passed = True

    for field in ["auth_quote", "access_quote", "api_quote"]:
        quote = evidence.get(field, "")
        passed, score, msg = verify_quote_in_text(quote, source_text)
        results[field] = {
            "passed": passed,
            "score": score,
            "message": msg
        }
        if not passed:
            all_passed = False

    return {
        "record_id": record.get("name", "unknown"),
        "docs_url": docs_url,
        "all_passed": all_passed,
        "checks": results
    }

if __name__ == "__main__":
    # Self-test: Verifying standard and planted errors
    sample_page = """
    GitHub REST API authentication. To authenticate with the GitHub REST API, you must provide a token in the Authorization header of your HTTP request. 
    GitHub supports multiple types of tokens, primarily personal access tokens and OAuth tokens.
    """

    print("--- Running Quote Verifier Self-Test ---")
    
    # 1. Valid quote
    valid_q = "To authenticate with the GitHub REST API, you must provide a token in the Authorization header of your HTTP request."
    ok, score, msg = verify_quote_in_text(valid_q, sample_page)
    print(f"Test 1 (Valid Quote): Passed={ok}, Msg={msg}")
    assert ok, "Valid quote should pass"

    # 2. Adversarially planted fake quote
    planted_q = "GitHub requires a corporate credit card and $500 monthly fee to generate REST API tokens."
    ok, score, msg = verify_quote_in_text(planted_q, sample_page)
    print(f"Test 2 (Planted Fake Quote): Passed={ok}, Msg={msg}")
    assert not ok, "Planted fake quote must be flagged as false"

    # 3. Unknown quote
    ok, score, msg = verify_quote_in_text("unknown", sample_page)
    print(f"Test 3 (Unknown Quote): Passed={ok}, Msg={msg}")
    assert ok, "Unknown quote should pass"

    print("All Quote Verifier assertions passed successfully!")
