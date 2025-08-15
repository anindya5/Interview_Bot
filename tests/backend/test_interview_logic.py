import pytest

from interview_logic import InterviewSession


def test_interview_sequence_levels_and_followups(stub_gemini):
    s = InterviewSession(topic='python', name='Alice', email='a@example.com')

    q1 = s.generate_initial_question()
    assert q1.startswith('Q[0-main]'), 'Initial should be level 0 main'
    assert s.level_index == 0
    assert s.phase == 'main'

    # Generate remaining 9 questions
    for i in range(9):
        q = s.generate_next_question(last_answer=f"ans{i}")
        assert isinstance(q, str)

    # Validate total questions
    assert len(s.questions_and_answers) == 10

    # Validate alternating phases across the run using stored Q text markers
    for idx, qa in enumerate(s.questions_and_answers):
        text = qa['question']
        level_expected = idx // 2  # two questions per level
        phase_expected = 'main' if idx % 2 == 0 else 'followup'
        assert f"Q[{level_expected}-{phase_expected}]" in text

    # Final internal state after 10 questions should be level 4
    assert s.level_index == 4
    assert s.phase in ('main', 'followup')


def test_interview_persistence_roundtrip(stub_gemini, monkeypatch):
    # Fake redis as simple dict
    store = {}

    class R:
        def hset(self, key, mapping):
            store[key] = mapping
        def hgetall(self, key):
            return store.get(key, {})

    s1 = InterviewSession(topic='ml', name='Bob', email='b@example.com')
    s1.generate_initial_question()
    s1.save(R())

    loaded = InterviewSession.load(R(), s1.session_id)
    assert loaded is not None
    assert loaded.topic == 'ml'
    assert loaded.level_index == 0
    assert loaded.phase == 'main'
    assert len(loaded.questions_and_answers) == 1


def test_scoring_fields_present_after_answers(stub_gemini):
    s = InterviewSession(topic='sql', name='C', email='c@x.com')
    s.generate_initial_question()
    # answer first 3 questions to ensure scoring runs multiple times
    for i in range(3):
        s.generate_next_question(last_answer=f"ans{i}")
    # each QA should have score and llm_answer filled
    for qa in s.questions_and_answers:
        assert 'score' in qa
        assert 'llm_answer' in qa
