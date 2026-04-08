# -*- coding: utf-8 -*-
import pytest


@pytest.mark.unit
def test_professional_cleaning_pipeline_removes_headers_footers_and_toc():
    from backend.indexing.professional_cleaning_pipeline import ProfessionalCleaningPipeline

    pipeline = ProfessionalCleaningPipeline()
    lines_by_page = [
        (1, ['安徽信息工程学院学生手册', '目录', '奖学金管理办法......12', '第1页']),
        (2, ['安徽信息工程学院学生手册', '第一章 奖学金评定办法', '奖学金申请应符合成绩条件。', '第2页']),
        (3, ['安徽信息工程学院学生手册', '第二章 申请材料', '申请人应提交申请表和证明材料。', '第3页']),
    ]

    cleaned_pages, report = pipeline.clean_pages(lines_by_page)

    assert report['header_footer_removed'] + report['noise_lines_removed'] >= 4
    assert report['toc_removed'] >= 1
    flattened = ' '.join(' '.join(lines) for _, lines in cleaned_pages)
    assert '目录' not in flattened
    assert '第1页' not in flattened
    assert '奖学金申请应符合成绩条件。' in flattened


@pytest.mark.unit
def test_professional_cleaning_pipeline_assesses_chunk_quality():
    from backend.indexing.professional_cleaning_pipeline import ProfessionalCleaningPipeline

    pipeline = ProfessionalCleaningPipeline()
    chunks = [
        {
            'id': 'good',
            'text': '奖学金申请应符合成绩条件，并提交规定的申请材料。',
            'char_count': 26,
            'metadata': {'section_path_text': '学生手册 > 奖学金'},
        },
        {
            'id': 'heading',
            'text': '第一章 奖学金评定办法',
            'char_count': 10,
            'metadata': {'section_path_text': '学生手册 > 奖学金'},
        },
        {
            'id': 'duplicate',
            'text': '奖学金申请应符合成绩条件，并提交规定的申请材料。',
            'char_count': 26,
            'metadata': {'section_path_text': '学生手册 > 奖学金'},
        },
    ]

    kept, report = pipeline.assess_chunks(chunks, document_metadata={'document_id': 'manual-1'})

    assert len(kept) == 1
    assert kept[0]['chunk_quality_status'] in ('pass', 'warn')
    assert report['quality_status_counts']['reject'] == 2
    assert report['kept_chunk_count'] == 1


@pytest.mark.unit
def test_professional_cleaning_pipeline_marks_warn_for_incomplete_text():
    from backend.indexing.professional_cleaning_pipeline import ProfessionalCleaningPipeline

    pipeline = ProfessionalCleaningPipeline()
    chunks = [
        {
            'id': 'warn-1',
            'text': '申请时需提交材料并经学院审核',
            'char_count': 14,
            'metadata': {'section_path_text': '学生手册 > 奖学金'},
        }
    ]

    kept, report = pipeline.assess_chunks(chunks, document_metadata={'document_id': 'manual-1'})

    assert len(kept) == 1
    assert kept[0]['chunk_quality_status'] == 'warn'
    assert 'incomplete_sentence' in kept[0]['cleaning_flags']
    assert report['quality_status_counts']['warn'] == 1
