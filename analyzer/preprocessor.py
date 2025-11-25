"""
preprocessor.py

Text cleaning, clause segmentation and light anonymisation to reduce bias.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import re
import logging

import spacy

logger = logging.getLogger(__name__)


# Lazy load spaCy model once
_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not installed — using blank English model")
            _nlp = spacy.blank("en")
            # Add sentence segmentation if missing
            if "sentencizer" not in _nlp.pipe_names:
                _nlp.add_pipe("sentencizer")
    return _nlp


@dataclass
class AnonymisationResult:
    anonymised_text: str
    entity_map: Dict[str, str]  # placeholder -> original entity


def basic_clean(text: str) -> str:
    # Normalise whitespace
    text = text.replace("\xa0", " ")
    text = text.replace("•", "-").replace("·", "-")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    # Keep double newlines (paragraphs), compress others
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def segment_clauses(text: str, max_clause_len: int = 900) -> List[str]:
    """
    Heuristic clause segmentation:
    1. Split on numbered headings (1., 1.1, etc.)
    2. Further split long blocks on sentence boundaries.
    """

    # Split AND retain clause numbering so meaning isn't lost
    parts = re.split(
        r"(?:(?<=\n)|^)\s*(\d+(?:\.\d+)*\.?)\s+",
        text,
        flags=re.IGNORECASE,
    )

    # Reconstruct numbered clauses
    raw_parts = []
    for i in range(1, len(parts), 2):
        number = parts[i].strip()
        clause_body = parts[i + 1].strip()
        raw_parts.append(f"{number} {clause_body}")

    # Fallback: if splitting fails, split on paragraphs
    if not raw_parts:
        raw_parts = [p.strip() for p in text.split("\n\n") if p.strip()]

    nlp = get_nlp()
    clauses: List[str] = []

    for block in raw_parts:
        block = block.strip()
        if not block:
            continue

        if len(block) <= max_clause_len:
            clauses.append(block)
            continue

        # Too long – split into sentence chunks
        doc = nlp(block)
        buffer = ""
        for sent in doc.sents:
            s_text = sent.text.strip()
            if not s_text:
                continue
            if len(buffer) + len(s_text) < max_clause_len:
                buffer += " " + s_text
            else:
                clauses.append(buffer.strip())
                buffer = s_text
        if buffer.strip():
            clauses.append(buffer.strip())

    # Remove meaningless fragments — must be at least 15 words
    clauses = [c for c in clauses if len(c.split()) >= 15]
    clauses = [re.sub(r"\s+", " ", c).replace(" .", ".").strip() for c in clauses]
    return clauses


def anonymise_parties(text: str) -> AnonymisationResult:
    """
    Replace PERSON and ORG entities with neutral placeholders
    (PARTY_1, PARTY_2, ORG_1, ...).

    This helps reduce bias related to names, gender, etc.,
    while keeping the contractual structure intact.
    """
    nlp = get_nlp()
    doc = nlp(text)

    entity_map: Dict[str, str] = {}
    replaced_text = text

    # Build unique order-preserving list
    persons: List[str] = []
    orgs: List[str] = []

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if ent.text not in persons:
                persons.append(ent.text)
        elif ent.label_ == "ORG":
            if ent.text not in orgs:
                orgs.append(ent.text)

    # Create mappings
    for idx, name in enumerate(sorted(persons, key=len, reverse=True), start=1):
        placeholder = f"PARTY_{idx}"
        entity_map[placeholder] = name
        replaced_text = re.sub(rf"\b{re.escape(name)}\b", placeholder, replaced_text)

    for idx, name in enumerate(sorted(orgs, key=len, reverse=True), start=1):
        placeholder = f"ORG_{idx}"
        entity_map[placeholder] = name
        replaced_text = re.sub(rf"\b{re.escape(name)}\b", placeholder, replaced_text)

    return AnonymisationResult(anonymised_text=replaced_text, entity_map=entity_map)


def preprocess_contract(raw_text: str) -> Tuple[str, List[str], List[str], AnonymisationResult]:
    """
    High-level helper:
    - clean original text
    - segment into original clauses
    - anonymise
    - segment into anonymised clauses
    """
    cleaned = basic_clean(raw_text)

    # Original clause segmentation before anonymisation
    original_clauses = segment_clauses(cleaned)

    # Apply anonymisation
    anon = anonymise_parties(cleaned)

    # Clause segmentation after anonymisation
    anonymised_clauses = segment_clauses(anon.anonymised_text)

    logger.info(
        "Preprocessed contract into %d original clauses and %d anonymised clauses",
        len(original_clauses),
        len(anonymised_clauses),
    )

    return anon.anonymised_text, original_clauses, anonymised_clauses, anon