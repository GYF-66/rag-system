# -*- coding: utf-8 -*-
"""Rebuild the enterprise RAG knowledge base from curated program PDFs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / 'backend'
DEFAULT_SOURCE_ROOT = ROOT_DIR / '人工智能专业培养方案+专业课教案材料'
DEFAULT_OUTPUT_PATH = ROOT_DIR / 'database' / 'rag_knowledge_base.json'

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from indexing.pdf_corpus_builder import PDFCorpusBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Rebuild enterprise RAG knowledge base from curated PDFs.')
    parser.add_argument('--source-root', default=str(DEFAULT_SOURCE_ROOT), help='Directory containing培养方案 and课程教案 PDFs.')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT_PATH), help='Output JSON knowledge base path.')
    parser.add_argument('--min-section-length', type=int, default=120, help='Minimum characters required for a section.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_root = Path(args.source_root).resolve()
    output_path = Path(args.output).resolve()

    builder = PDFCorpusBuilder(source_root=source_root, min_section_length=args.min_section_length)
    corpus = builder.build_corpus(output_path=output_path)

    summary = {
        'source_root': str(source_root),
        'output_path': str(output_path),
        'document_count': corpus['metadata'].get('document_count', 0),
        'total_chunks': corpus['metadata'].get('total_chunks', 0),
        'chunking_method': corpus['metadata'].get('chunking_method'),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
