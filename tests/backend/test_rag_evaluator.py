# -*- coding: utf-8 -*-
import pytest


class FakeRetriever:
    def __init__(self):
        self.keyword_backend = type('Backend', (), {})()
        self.keyword_backend.chunks = [
            {
                'id': 'program-1',
                'text': '人工智能专业培养目标强调德智体美劳全面发展与工程实践能力。',
                'section': '培养目标',
                'metadata': {
                    'document_id': 'c2022培养方案',
                    'title': '人工智能专业培养方案',
                    'source_path': '培养方案.pdf',
                    'section_path': ['人工智能专业培养方案', '培养目标'],
                    'section_path_text': '人工智能专业培养方案 > 培养目标',
                    'chunk_type': 'program_spec',
                },
            },
            {
                'id': 'manual-1',
                'text': '奖学金申请需要符合成绩条件并按要求提交申请材料。',
                'section': '奖学金',
                'metadata': {
                    'document_id': '学生手册',
                    'title': '2024版学生手册',
                    'source_path': '学生手册.pdf',
                    'section_path': ['学生手册', '奖学金'],
                    'section_path_text': '学生手册 > 奖学金',
                    'chunk_type': 'general',
                },
            },
        ]

    def search(self, query, top_k=5):
        if '培养目标' in query:
            return [self.keyword_backend.chunks[0], self.keyword_backend.chunks[1]][:top_k]
        return [self.keyword_backend.chunks[1], self.keyword_backend.chunks[0]][:top_k]


@pytest.mark.unit
def test_rag_evaluator_runs_against_search_interface():
    from backend.evaluation.rag_evaluator import RAGEvaluator

    cases = [
        {
            'id': 'case-1',
            'query': '人工智能专业培养目标是什么？',
            'relevant_document_keywords': ['培养方案'],
            'relevant_section_keywords': ['培养目标'],
            'relevant_chunk_types': ['program_spec'],
        },
        {
            'id': 'case-2',
            'query': '奖学金申请条件有哪些？',
            'relevant_document_keywords': ['学生手册'],
            'relevant_section_keywords': ['奖学金'],
            'must_include_terms': ['申请材料'],
        },
    ]

    evaluator = RAGEvaluator(retriever=FakeRetriever())
    results = evaluator.run_full_evaluation(test_cases=cases)

    assert results['retrieval']['num_test_cases'] == 2
    assert results['retrieval']['precision_at_1'] == pytest.approx(1.0)
    assert results['retrieval']['mrr'] == pytest.approx(1.0)
    assert 'context_duplication_rate' in results['retrieval']
    assert 'irrelevant_doc_rate' in results['retrieval']
    assert results['overall_score'] > 0.5
