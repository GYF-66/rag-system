# -*- coding: utf-8 -*-
import pytest


class FakeBackend:
    def __init__(self, responses):
        self.responses = responses

    def is_loaded(self):
        return True

    def search(self, query, top_k=5, min_similarity=0.03):
        return self.responses.get(query, [])[:top_k]


@pytest.mark.unit
def test_hybrid_retriever_builds_query_variants():
    from backend.retrieval.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(enable_cache=False, vector_backend=FakeBackend({}), keyword_backend=FakeBackend({}))
    variants = retriever._build_query_variants('机器学习 API 接口要求是什么？')

    assert variants[0] == '机器学习 API 接口要求是什么?'
    assert len(variants) >= 2
    assert len(variants) <= 3


@pytest.mark.unit
def test_hybrid_retriever_fuses_vector_and_keyword_results():
    from backend.retrieval.hybrid_retriever import HybridRetriever

    vector_backend = FakeBackend(
        {
            '奖学金申请条件': [
                {'id': 'doc-1', 'text': '奖学金申请条件包括成绩与综合测评。', 'section': '奖学金', 'similarity': 0.82},
                {'id': 'doc-2', 'text': '宿舍管理办法。', 'section': '住宿', 'similarity': 0.35},
            ]
        }
    )
    keyword_backend = FakeBackend(
        {
            '奖学金申请条件': [
                {'id': 'doc-1', 'text': '奖学金申请条件包括成绩与综合测评。', 'section': '奖学金', 'similarity': 0.91},
                {'id': 'doc-3', 'text': '奖学金申请流程说明。', 'section': '奖学金', 'similarity': 0.76},
            ]
        }
    )

    retriever = HybridRetriever(
        enable_cache=False,
        vector_backend=vector_backend,
        keyword_backend=keyword_backend,
        enable_adaptive=False,
    )

    results = retriever.search('奖学金申请条件', top_k=3)

    assert results
    assert results[0]['id'] == 'doc-1'
    assert results[0]['retrieval_method'] == 'hybrid_rrf'
    assert 'vector' in results[0]['matched_channels']
    assert 'keyword' in results[0]['matched_channels']


@pytest.mark.unit
def test_hybrid_retriever_dedupes_near_identical_results():
    from backend.retrieval.hybrid_retriever import HybridRetriever

    duplicated = '毕业设计要求包括选题、开题、中期检查和答辩。'
    vector_backend = FakeBackend({'毕业设计要求': [{'id': 'doc-1', 'text': duplicated, 'section': '毕业设计', 'similarity': 0.8}]})
    keyword_backend = FakeBackend({'毕业设计要求': [{'id': 'doc-2', 'text': duplicated, 'section': '毕业设计', 'similarity': 0.78}]})

    retriever = HybridRetriever(enable_cache=False, vector_backend=vector_backend, keyword_backend=keyword_backend)
    results = retriever.search('毕业设计要求', top_k=5)

    assert len(results) == 1
    assert results[0]['section'] == '毕业设计'


@pytest.mark.unit
def test_hybrid_retriever_filters_low_quality_chunks_and_limits_single_section():
    from backend.retrieval.hybrid_retriever import HybridRetriever

    vector_backend = FakeBackend(
        {
            '奖学金申请条件': [
                {'id': 'doc-1', 'text': '奖学金申请条件包括成绩、综合测评以及材料审核。', 'section': '奖学金', 'similarity': 0.91},
                {'id': 'doc-2', 'text': '目录', 'section': '奖学金', 'similarity': 0.99},
                {'id': 'doc-3', 'text': '奖学金评审办法包括资格审核与评审流程。', 'section': '奖学金', 'similarity': 0.89},
                {'id': 'doc-4', 'text': '奖学金申请材料通常包括申请表和证明材料。', 'section': '奖学金', 'similarity': 0.88},
            ]
        }
    )
    keyword_backend = FakeBackend({'奖学金申请条件': []})

    retriever = HybridRetriever(enable_cache=False, vector_backend=vector_backend, keyword_backend=keyword_backend)
    results = retriever.search('奖学金申请条件', top_k=5)

    assert all(item['text'] != '目录' for item in results)
    assert len([item for item in results if item['section'] == '奖学金']) <= 2

