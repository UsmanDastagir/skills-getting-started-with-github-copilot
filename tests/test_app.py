"""
Test suite for the High School Management System API

Uses FastAPI's TestClient to test all API endpoints without running a server.
Tests are structured using the AAA (Arrange-Act-Assert) pattern.
"""

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities as original_activities

# Create a TestClient instance for testing
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities data before each test to ensure isolation"""
    # Reset the global activities dict to its original state
    import app
    app.activities = copy.deepcopy(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirect(self):
        """Test that root path redirects to static/index.html"""
        # Arrange: No special setup needed
        # Act
        response = client.get("/", follow_redirects=False)
        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self):
        """Test successful retrieval of all activities"""
        # Arrange: Activities are already set up in fixture
        # Act
        response = client.get("/activities")
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # All activities present
        assert "Chess Club" in data

    def test_activities_have_required_fields(self):
        """Test that each activity has all required fields"""
        # Arrange: Activities are set up
        # Act
        response = client.get("/activities")
        data = response.json()
        # Assert
        required_fields = {"description", "schedule", "max_participants", "participants"}
        for activity_name, activity_data in data.items():
            assert required_fields.issubset(activity_data.keys()), \
                f"Activity '{activity_name}' missing required fields"
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self):
        """Test successful signup for an activity"""
        # Arrange
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        initial_count = len(original_activities[activity]["participants"])
        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        # Verify participant was added
        get_response = client.get("/activities")
        updated_activity = get_response.json()[activity]
        assert email in updated_activity["participants"]
        assert len(updated_activity["participants"]) == initial_count + 1

    def test_signup_duplicate_participant(self):
        """Test that duplicate signups are rejected"""
        # Arrange
        email = "duplicate@mergington.edu"
        activity = "Programming Class"
        # First signup
        client.post(f"/activities/{activity}/signup", params={"email": email})
        # Act: Try to signup again
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_invalid_activity(self):
        """Test signup for a non-existent activity"""
        # Arrange
        email = "student@mergington.edu"
        invalid_activity = "Nonexistent Club"
        # Act
        response = client.post(f"/activities/{invalid_activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_empty_email(self):
        """Test signup with empty email"""
        # Arrange
        email = ""
        activity = "Gym Class"
        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 200  # Currently no validation, so succeeds
        assert "Signed up" in response.json()["message"]

    def test_signup_special_characters_email(self):
        """Test signup with special characters in email"""
        # Arrange
        email = "test+special@mergington.edu"
        activity = "Soccer Team"
        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]

    def test_signup_activity_with_spaces(self):
        """Test signup for activity with spaces in name"""
        # Arrange
        email = "spacetest@mergington.edu"
        activity = "Art Studio"  # Has space
        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]

    def test_signup_over_max_participants(self):
        """Test signup when exceeding max participants (currently not enforced)"""
        # Arrange
        activity = "Chess Club"  # max_participants: 12, currently 2
        emails = [f"over{i}@mergington.edu" for i in range(15)]  # Add 15 more
        # Act: Add participants until over max
        for email in emails:
            response = client.post(f"/activities/{activity}/signup", params={"email": email})
            assert response.status_code == 200  # Should succeed as not enforced
        # Assert: Verify all were added
        get_response = client.get("/activities")
        updated_activity = get_response.json()[activity]
        assert len(updated_activity["participants"]) > updated_activity["max_participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        # Arrange
        email = "unregtest@mergington.edu"
        activity = "Swimming Club"
        # First signup
        client.post(f"/activities/{activity}/signup", params={"email": email})
        initial_count = len(client.get("/activities").json()[activity]["participants"])
        # Act
        response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        # Assert
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        # Verify participant was removed
        get_response = client.get("/activities")
        updated_activity = get_response.json()[activity]
        assert email not in updated_activity["participants"]
        assert len(updated_activity["participants"]) == initial_count - 1

    def test_unregister_not_signed_up(self):
        """Test unregistering when not signed up"""
        # Arrange
        email = "notsigned@mergington.edu"
        activity = "Drama Club"
        # Act
        response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        # Assert
        assert response.status_code == 404
        assert "not signed up" in response.json()["detail"]

    def test_unregister_invalid_activity(self):
        """Test unregistering from a non-existent activity"""
        # Arrange
        email = "student@mergington.edu"
        invalid_activity = "Fake Activity"
        # Act
        response = client.delete(f"/activities/{invalid_activity}/unregister", params={"email": email})
        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_empty_email(self):
        """Test unregister with empty email"""
        # Arrange
        email = ""
        activity = "Science Club"
        # Act
        response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        # Assert
        assert response.status_code == 404  # Not signed up
        assert "not signed up" in response.json()["detail"]

    def test_unregister_special_characters_email(self):
        """Test unregister with special characters in email"""
        # Arrange
        email = "special@unreg.com"
        activity = "Debate Team"
        # First signup
        client.post(f"/activities/{activity}/signup", params={"email": email})
        # Act
        response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        # Assert
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]


class TestEdgeCases:
    """Tests for edge cases and crash prevention"""

    def test_multiple_operations_same_activity(self):
        """Test multiple signups and unregisters on same activity"""
        # Arrange
        activity = "Gym Class"
        emails = [f"multi{i}@mergington.edu" for i in range(5)]
        # Act: Signup all
        for email in emails:
            response = client.post(f"/activities/{activity}/signup", params={"email": email})
            assert response.status_code == 200
        # Unregister some
        for email in emails[:3]:
            response = client.delete(f"/activities/{activity}/unregister", params={"email": email})
            assert response.status_code == 200
        # Assert: Check final state
        get_response = client.get("/activities")
        updated_activity = get_response.json()[activity]
        assert len(updated_activity["participants"]) == len(original_activities[activity]["participants"]) + 2

    def test_url_encoding_activity_name(self):
        """Test activity names that need URL encoding"""
        # Arrange
        activity = "Art Studio"  # Space in name
        email = "urltest@mergington.edu"
        # Act
        response = client.post(f"/activities/{activity}/signup", params={"email": email})
        # Assert
        assert response.status_code == 200

    def test_concurrent_like_operations(self):
        """Test rapid successive operations to check for race conditions"""
        # Arrange
        activity = "Programming Class"
        base_email = "rapid@mergington.edu"
        # Act: Quick signups and unregisters
        for i in range(10):
            email = f"{i}{base_email}"
            client.post(f"/activities/{activity}/signup", params={"email": email})
            client.delete(f"/activities/{activity}/unregister", params={"email": email})
        # Assert: Should not crash, final state should be original
        get_response = client.get("/activities")
        updated_activity = get_response.json()[activity]
        assert len(updated_activity["participants"]) == len(original_activities[activity]["participants"])