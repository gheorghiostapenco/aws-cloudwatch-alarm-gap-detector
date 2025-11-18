from lambda_app.handler import detect_gaps

def test_missing_alarms_detected():
    resources = {
        "EC2": [
            {"id": "i-123", "type": "EC2", "tags": []}
        ]
    }

    alarms = []  # no alarms

    config = {
        "required": {
            "EC2": ["CPUUtilization", "StatusCheckFailed"]
        },
        "filter": {}
    }

    result = detect_gaps(resources, alarms, config)

    assert len(result) == 1
    assert result[0]["resource"] == "i-123"
    assert "CPUUtilization" in result[0]["missing"]
