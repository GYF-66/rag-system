# -*- coding: utf-8 -*-
"""Generate professional cleaning reports for curated PDF corpora."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.indexing.pdf_corpus_builder import PDFCorpusBuilder


def build_report(source_root: Path) -> Dict:
    builder = PDFCorpusBuilder(source_root=source_root)
    pdf_files = builder.discover_pdf_files()

    documents: List[Dict] = []
    totals = {
        'document_count': 0,
        'page_count': 0,
        'cleaned_page_count': 0,
        'section_count': 0,
        'chunk_count': 0,
        'kept_chunk_count': 0,
        'header_footer_removed': 0,
        'toc_removed': 0,
        'noise_lines_removed': 0,
        'reject_count': 0,
        'warn_count': 0,
        'pass_count': 0,
    }

    for pdf_path in pdf_files:
        document = builder._extract_document(pdf_path)
        if not document:
            continue
        metadata = dict(document.get('metadata') or {})
        quality_report = dict(metadata.get('quality_report') or {})
        status_counts = dict(quality_report.get('quality_status_counts') or {})
        documents.append(
            {
                'document_id': metadata.get('document_id'),
                'title': metadata.get('title'),
                'document_type': metadata.get('document_type'),
                'source_path': metadata.get('source_path'),
                'quality_report': quality_report,
            }
        )
        totals['document_count'] += 1
        totals['page_count'] += int(quality_report.get('page_count') or 0)
        totals['cleaned_page_count'] += int(quality_report.get('cleaned_page_count') or 0)
        totals['section_count'] += int(quality_report.get('section_count') or 0)
        totals['chunk_count'] += int(quality_report.get('chunk_count') or 0)
        totals['kept_chunk_count'] += int(quality_report.get('kept_chunk_count') or 0)
        totals['header_footer_removed'] += int(quality_report.get('header_footer_removed') or 0)
        totals['toc_removed'] += int(quality_report.get('toc_removed') or 0)
        totals['noise_lines_removed'] += int(quality_report.get('noise_lines_removed') or 0)
        totals['reject_count'] += int(status_counts.get('reject') or 0)
        totals['warn_count'] += int(status_counts.get('warn') or 0)
        totals['pass_count'] += int(status_counts.get('pass') or 0)

    totals['keep_rate'] = round(totals['kept_chunk_count'] / max(totals['chunk_count'], 1), 4)
    totals['clean_page_rate'] = round(totals['cleaned_page_count'] / max(totals['page_count'], 1), 4)

    return {
        'generated_at': datetime.now().isoformat(),
        'source_root': str(source_root),
        'totals': totals,
        'documents': documents,
    }


def render_markdown(report: Dict) -> str:
    totals = report['totals']
    lines = [
        '# 专业版清洗报告',
        '',
        f"- 生成时间：`{report['generated_at']}`",
        f"- 数据源目录：`{report['source_root']}`",
        f"- 文档数：`{totals['document_count']}`",
        f"- 页面数：`{totals['page_count']}`，清洗后页面数：`{totals['cleaned_page_count']}`",
        f"- Chunk 数：`{totals['chunk_count']}`，保留：`{totals['kept_chunk_count']}`，保留率：`{totals['keep_rate']}`",
        f"- pass/warn/reject：`{totals['pass_count']}` / `{totals['warn_count']}` / `{totals['reject_count']}`",
        f"- 页眉页脚剔除：`{totals['header_footer_removed']}`，目录剔除：`{totals['toc_removed']}`，噪声行剔除：`{totals['noise_lines_removed']}`",
        '',
        '## 文档明细',
        '',
        '| 文档 | 类型 | chunk | 保留 | pass/warn/reject |',
        '|---|---|---:|---:|---|',
    ]

    for document in report['documents']:
        quality = document['quality_report']
        status = quality.get('quality_status_counts') or {}
        lines.append(
            f"| {document['title']} | {document.get('document_type') or '-'} | {quality.get('chunk_count', 0)} | {quality.get('kept_chunk_count', 0)} | {status.get('pass', 0)}/{status.get('warn', 0)}/{status.get('reject', 0)} |"
        )
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate professional cleaning report for PDF RAG corpus.')
    parser.add_argument('--source-root', default=str(BASE_DIR / '人工智能专业培养方案+专业课教案材料'))
    parser.add_argument('--output-dir', default=str(BASE_DIR / 'evaluation_results'))
    parser.add_argument('--prefix', default='cleaning_report')
    args = parser.parse_args()

    source_root = Path(args.source_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(source_root)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = output_dir / f'{args.prefix}_{timestamp}.json'
    md_path = output_dir / f'{args.prefix}_{timestamp}.md'

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8-sig')
    md_path.write_text(render_markdown(report), encoding='utf-8')

    print(f'[OK] JSON report: {json_path}')
    print(f'[OK] Markdown report: {md_path}')
    print(f"[OK] Documents: {report['totals']['document_count']}, kept chunks: {report['totals']['kept_chunk_count']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
