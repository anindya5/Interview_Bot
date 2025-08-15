import pytest


def test_onboarding_routes_flow(client, stub_email):
    # start
    rv = client.post('/onboarding/start')
    assert rv.status_code == 200
    data = rv.get_json()
    sid = data['onboarding_session_id']
    assert data['finished'] is False

    # name
    rv = client.post('/onboarding/continue', json={
        'onboarding_session_id': sid,
        'message': 'Jane Doe'
    })
    assert rv.status_code == 200

    # email
    rv = client.post('/onboarding/continue', json={
        'onboarding_session_id': sid,
        'message': 'jane@example.com'
    })
    data = rv.get_json()
    assert data['stage'] == 'email_code'
    assert 'resend_available_in' in data
    assert 'expires_in' in data
    assert 'attempts_left' in data

    # resend right away (will likely be on cooldown)
    rv = client.post('/onboarding/resend', json={'onboarding_session_id': sid})
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'resend_available_in' in data


def test_start_interview_and_submit_to_completion(client, stub_gemini):
    # missing fields
    rv = client.post('/start-interview', json={'topic': 'python'})
    assert rv.status_code == 400

    # start interview
    rv = client.post('/start-interview', json={
        'topic': 'python', 'name': 'Alice', 'email': 'a@example.com'
    })
    assert rv.status_code == 200
    data = rv.get_json()
    sid = data['session_id']
    assert 'question' in data

    # Submit 9 answers that should yield next questions (not finished yet)
    for i in range(9):
        rv = client.post('/submit', json={'session_id': sid, 'answer': f'ans{i}'})
        assert rv.status_code == 200
        payload = rv.get_json()
        assert 'finished' in payload
        if i < 8:
            # first 8 submissions -> not finished
            assert payload['finished'] is False
            assert 'question' in payload
        else:
            # 9th submission should still not finish because finish triggers on the next call
            assert payload['finished'] is False

    # Final (10th) submission should finish and thank the user
    rv = client.post('/submit', json={'session_id': sid, 'answer': 'final'})
    assert rv.status_code == 200
    payload = rv.get_json()
    assert payload['finished'] is True
    assert 'Thank you' in payload['question']
