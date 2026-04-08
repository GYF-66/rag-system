# -*- coding: utf-8 -*-
from pathlib import Path

import pytest


@pytest.mark.unit
def test_pdf_corpus_builder_attaches_quality_report(monkeypatch, tmp_path: Path):
    from backend.indexing.pdf_corpus_builder import PDFCorpusBuilder
    from backend.chunking.unified_chunker import UnifiedChunker

    pdf_path = tmp_path / '人工智能专业培养方案.pdf'
    pdf_path.write_bytes(b'%PDF-1.4 mock')

    builder = PDFCorpusBuilder(
        source_root=tmp_path,
        chunker=UnifiedChunker(chunk_size=120, chunk_overlap=20, min_chunk_size=40),
        min_section_length=20,
    )

    monkeypatch.setattr(
        builder,
        '_extract_lines',
        lambda _: [
            (1, ['安徽信息工程学院', '人工智能专业人才培养方案', '第一章 培养目标', '培养目标强调工程实践能力、创新能力和综合素养，要求学生具备扎实的理论基础、较强的问题分析能力以及良好的职业道德与团队协作能力。', '第1页']),
            (2, ['安徽信息工程学院', '第二章 课程体系', '课程体系包括通识课、专业基础课、专业核心课以及实践教学环节，突出机器学习、数据智能、工程实现和项目训练等能力培养。', '第2页']),
        ],
    )

    document = builder._extract_document(pdf_path)

    assert document is not None
    assert document['chunks']
    assert document['metadata']['document_type'] == 'program_spec'
    quality_report = document['metadata']['quality_report']
    assert quality_report['page_count'] == 2
    assert 'quality_status_counts' in quality_report
    assert document['chunks'][0]['metadata']['chunk_quality_status'] in ('pass', 'warn')
    assert 'chunk_quality_score' in document['chunks'][0]['metadata']
