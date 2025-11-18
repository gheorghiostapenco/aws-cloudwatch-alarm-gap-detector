from lambda_app import handler

def test_format_empty():
    assert handler.format_report([]) == "All resources have required CloudWatch alarms."
