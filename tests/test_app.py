"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root URL redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that getting activities returns 200 OK"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that response contains expected activity names"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Soccer Team",
            "Basketball Club",
            "Art Workshop",
            "Drama Club",
            "Mathletes",
            "Science Club"
        ]
        
        for activity_name in expected_activities:
            assert activity_name in data
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_details in data.items():
            for field in required_fields:
                assert field in activity_details, f"{activity_name} missing {field}"
    
    def test_participants_is_list(self, client):
        """Test that participants field is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client):
        """Test successfully signing up a new participant"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds participant to the activity"""
        email = "teststudent@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up an already registered participant fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_requires_email_parameter(self, client):
        """Test that email parameter is required"""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # Unprocessable Entity


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_existing_participant_success(self, client):
        """Test successfully removing an existing participant"""
        # First, add a participant
        email = "toremove@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Then remove them
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
    
    def test_remove_participant_actually_removes(self, client):
        """Test that remove actually removes the participant from the activity"""
        email = "toremove2@mergington.edu"
        
        # Add participant
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Remove participant
        client.delete(f"/activities/Chess Club/participants/{email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]
    
    def test_remove_nonexistent_participant_fails(self, client):
        """Test that removing a non-existent participant fails"""
        response = client.delete(
            "/activities/Chess Club/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_remove_from_nonexistent_activity_fails(self, client):
        """Test that removing from a non-existent activity fails"""
        response = client.delete(
            "/activities/Fake Activity/participants/test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_remove_preexisting_participant(self, client):
        """Test removing a participant that was already in the initial data"""
        # Chess Club has michael@mergington.edu as a pre-existing participant
        email = "michael@mergington.edu"
        
        # Verify they exist
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
        
        # Remove them
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert response.status_code == 200
        
        # Verify they were removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]


class TestEndToEndScenarios:
    """End-to-end test scenarios"""
    
    def test_full_signup_and_removal_flow(self, client):
        """Test complete flow: get activities, signup, verify, remove, verify"""
        email = "flowtest@mergington.edu"
        activity = "Programming Class"
        
        # Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        assert len(data[activity]["participants"]) == initial_count + 1
        
        # Remove participant
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]
        assert len(data[activity]["participants"]) == initial_count
    
    def test_multiple_signups_different_activities(self, client):
        """Test signing up the same email for multiple different activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Chess Club", "Programming Class", "Art Workshop"]
        
        for activity in activities_to_join:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all signups
        response = client.get("/activities")
        data = response.json()
        
        for activity in activities_to_join:
            assert email in data[activity]["participants"]
