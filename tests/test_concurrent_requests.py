from fastapi.testclient import TestClient
from server.app import app
import threading

def test_concurrent_resets():
    """Two concurrent /reset calls should not interfere with each other."""
    client = TestClient(app)
    responses = []
    
    def make_request(session_id):
        r = client.post("/reset", params={"task": "triage_sprint", "session_id": session_id})
        responses.append((session_id, r))
        
    t1 = threading.Thread(target=make_request, args=("sess_1",))
    t2 = threading.Thread(target=make_request, args=("sess_2",))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    assert len(responses) == 2
    for sid, r in responses:
        assert r.status_code == 200
        assert "tickets" in r.json()
