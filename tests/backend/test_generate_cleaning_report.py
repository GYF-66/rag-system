# -*- coding: utf-8 -*-
from pathlib import Path

import pytest


@pytest.mark.unit
def test_generate_cleaning_report_builds_aggregate_report(monkeypatch, tmp_path: Path):
    from scripts import generate_cleaning_report as report_module

    class FakeBuilder:
        def __init__(self, source_root):
            self.source_root = source_root

        def discover_pdf_files(self):
            return [tmp_path / 'a.pdf', tmp_path / 'b.pdf']

        def _extract_document(self, pdf_path):
            return {
                'metadata': {
                    'document_id': pdf_path.stem,
                    'title': pdf_path.stem,
                    'document_type': 'program_spec',
                    'source_path': str(pdf_path),
                    'quality_report': {
                        'page_count': 2,
                        'cleaned_page_count': 2,
                        'section_count': 3,
                        'chunk_count': 5,
                        'kept_chunk_count': 4,
                        'header_footer_removed': 1,
                        'toc_removed': 1,
                        'noise_lines_removed': 2,
                        'quality_status_counts': {'pass': 3, 'warn': 1, 'reject': 1},
                    },
                },
                'chunks': [],
            }

    monkeypatch.setattr(report_module, 'PDFCorpusBuilder', FakeBuilder)

    report = report_module.build_report(tmp_path)
    markdown = report_module.render_markdown(report)

    assert report['totals']['document_count'] == 2
    assert report['totals']['chunk_count'] == 10
    assert report['totals']['kept_chunk_count'] == 8
    assert report['totals']['reject_count'] == 2
    assert '# 专业版清洗报告' in markdown
    assert '| 文档 | 类型 | chunk | 保留 | pass/warn/reject |' in markdown
