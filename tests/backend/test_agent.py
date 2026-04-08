# -*- coding: utf-8 -*-
"""
Agent 妯″潡娴嬭瘯
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
def test_agent_creation():
    """娴嬭瘯 Agent 鍒涘缓"""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    assert agent.name == "瀹変俊宸I灏忓姪鎵?
    assert agent.role == "瀛︾敓鎵嬪唽鏅鸿兘闂瓟鍔╂墜"
    assert agent.description is not None
    assert len(agent.chapter_patterns) > 0


@pytest.mark.unit
def test_agent_query_analysis():
    """娴嬭瘯鏌ヨ鍒嗘瀽"""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    # 娴嬭瘯绠€鍗曟煡璇?    query = "璇峰亣娴佺▼鏄粈涔堬紵"
    keywords = agent._extract_keywords(query)

    assert isinstance(keywords, list)
    assert len(keywords) > 0


@pytest.mark.unit
def test_agent_extract_key_sentences():
    """娴嬭瘯鍏抽敭鍙ュ瓙鎻愬彇"""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    text = "杩欐槸绗竴鍙ヨ瘽锛屽寘鍚冻澶熼暱鐨勫唴瀹逛俊鎭€傝繖鏄浜屽彞璇濓紝涔熸湁瓒冲澶氱殑瀛楁暟锛佽繖鏄涓夊彞璇濓紝鍚屾牱鏈夎冻澶熺殑鍐呭锛?
    sentences = agent._extract_key_sentences(text, max_sentences=3)

    assert len(sentences) == 3
    assert "杩欐槸绗竴鍙ヨ瘽" in sentences[0]


@pytest.mark.unit
def test_agent_generate_response_no_sources():
    """娴嬭瘯鏃犳潵婧愭椂鐨勫洖澶嶇敓鎴?""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()
    response = agent._generate_fallback_response("娴嬭瘯鏌ヨ")

    assert "鎶辨瓑" in response
    assert "娴嬭瘯鏌ヨ" in response


@pytest.mark.unit
def test_agent_merge_continuous_chunks():
    """娴嬭瘯杩炵画鍧楀悎骞?""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    chunks = [
        {"id": "0", "text": "绗竴娈靛唴瀹?, "section": "绗竴绔?, "similarity": 0.9},
        {"id": "1", "text": "绗簩娈靛唴瀹?, "section": "绗竴绔?, "similarity": 0.85},
        {"id": "2", "text": "鍏朵粬绔犺妭鍐呭", "section": "绗簩绔?, "similarity": 0.8}
    ]

    merged = agent._merge_continuous_chunks(chunks)

    assert len(merged) <= len(chunks)  # 鍚堝苟鍚庢暟閲忓簲璇ュ噺灏戞垨涓嶅彉


@pytest.mark.unit
def test_agent_process_query_without_rag():
    """娴嬭瘯涓嶄娇鐢?RAG 鐨勬煡璇㈠鐞?""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    with patch.object(agent._response_gen, 'generate', return_value="娴嬭瘯鍥炲"):
        result = agent.process_query(
            query="娴嬭瘯闂",
            use_rag=False
        )

        assert result['response'] == "娴嬭瘯鍥炲"
        assert 'sources' in result


@pytest.mark.unit
def test_agent_detect_query_type():
    """娴嬭瘯鏌ヨ绫诲瀷妫€娴?""
    from backend.agent import AISpecialtyAgent

    agent = AISpecialtyAgent()

    # 娴嬭瘯"濡備綍"绫绘煡璇?    query1 = "濡備綍鐢宠濂栧閲戯紵"
    type1 = agent._detect_query_type(query1)
    assert type1 == "how_to"

    # 娴嬭瘯"鏄惁"绫绘煡璇?    query2 = "鍙互璇峰亣鍚楋紵"
    type2 = agent._detect_query_type(query2)
    assert type2 == "yes_no"

    # 娴嬭瘯"鍝簺"绫绘煡璇?    query3 = "鏈夊摢浜涘瀛﹂噾锛?
    type3 = agent._detect_query_type(query3)
    assert type3 == "quantity"
