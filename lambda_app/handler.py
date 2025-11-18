import json
import boto3
import logging
import os
import yaml
import urllib.request
import urllib.error
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------

def load_config():
    """
    Load configuration file with thresholds and required alarm definitions.
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    if not os.path.exists(config_path):
        logger.warning("Config file 'config.yaml' not found, using defaults.")
        return {}

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------
# Metric name mapping (logical -> real CloudWatch metrics)
# ---------------------------------------------------------

METRIC_NAME_MAP = {
    "CPUUtilization": ["CPUUtilization"],
    "StatusCheckFailed": ["StatusCheckFailed"],
    "FreeStorageSpace": ["FreeStorageSpace"],
    "HTTPCode_ELB_5XX": ["HTTPCode_ELB_5XX_Count", "HTTPCode_ELB_5XX"],
    "Errors": ["Errors"],
    "Throttles": ["Throttles"],
}


# ---------------------------------------------------------
# Resource collectors
# ---------------------------------------------------------

def get_ec2_instances():
    ec2 = boto3.client("ec2")
    instances = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                instances.append({
                    "id": inst["InstanceId"],
                    "type": "EC2",
                    "tags": inst.get("Tags", []),
                })

    logger.info(f"Collected {len(instances)} EC2 instances.")
    return instances


def get_rds_instances():
    rds = boto3.client("rds")
    instances = []

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            instances.append({
                "id": db["DBInstanceIdentifier"],
                "arn": db["DBInstanceArn"],
                "type": "RDS",
                "tags": db.get("TagList", []),
            })

    logger.info(f"Collected {len(instances)} RDS instances.")
    return instances


def get_load_balancers():
    elb = boto3.client("elbv2")
    lbs = []

    paginator = elb.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for lb in page.get("LoadBalancers", []):
            lbs.append({
                "id": lb["LoadBalancerName"],
                "arn": lb["LoadBalancerArn"],
                "type": "ALB" if lb["Type"] == "application" else "NLB",
                "tags": [],
            })

    logger.info(f"Collected {len(lbs)} load balancers.")
    return lbs


def get_lambda_functions():
    lamb = boto3.client("lambda")
    functions = []

    paginator = lamb.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page.get("Functions", []):
            functions.append({
                "id": fn["FunctionName"],
                "arn": fn["FunctionArn"],
                "type": "Lambda",
                "tags": {},  
            })

    logger.info(f"Collected {len(functions)} Lambda functions.")
    return functions


# ---------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------

def resource_has_required_tags(resource, config):
    filter_cfg = config.get("filter", {})
    key = filter_cfg.get("tag_key")
    value = filter_cfg.get("tag_value")

    if not key or not value:
        return True

    tags = resource.get("tags")
    if not tags:
        return False

    for t in tags:
        if t.get("Key") == key and t.get("Value") == value:
            return True

    return False


# ---------------------------------------------------------
# CloudWatch alarm collector
# ---------------------------------------------------------

def get_all_cloudwatch_alarms():
    cw = boto3.client("cloudwatch")
    alarms = []

    paginator = cw.get_paginator("describe_alarms")
    for page in paginator.paginate():
        alarms.extend(page.get("MetricAlarms", []))

    logger.info(f"Collected {len(alarms)} CloudWatch alarms.")
    return alarms


# ---------------------------------------------------------
# Alarm/resource matching
# ---------------------------------------------------------

def find_alarms_for_resource(resource, alarms):
    resource_id = resource["id"]
    resource_type = resource["type"]
    resource_arn = resource.get("arn")

    related = []

    dimension_map = {
        "EC2": "InstanceId",
        "RDS": "DBInstanceIdentifier",
        "ALB": "LoadBalancer",
        "NLB": "LoadBalancer",
        "Lambda": "FunctionName"
    }

    expected_dim = dimension_map.get(resource_type)

    for alarm in alarms:
        alarm_name = alarm.get("AlarmName", "")

        if resource_id in alarm_name:
            related.append(alarm)
            continue

        for dim in alarm.get("Dimensions", []):
            dim_name = dim.get("Name")
            dim_value = dim.get("Value")

            if dim_name == expected_dim and dim_value == resource_id:
                related.append(alarm)
                break

            if resource_type in ["ALB", "NLB"]:
                if dim_name == expected_dim and resource_arn and resource_arn.endswith(dim_value):
                    related.append(alarm)
                    break

    return related


# ---------------------------------------------------------
# Gap detection logic
# ---------------------------------------------------------

def detect_gaps(resources, alarms, config):
    gaps = []
    required = config.get("required", {})

    for rtype, items in resources.items():
        required_metrics = required.get(rtype, [])

        for res in items:
            if not resource_has_required_tags(res, config):
                continue

            resource_id = res["id"]
            related_alarms = find_alarms_for_resource(res, alarms)

            existing_metric_names = set()
            for alarm in related_alarms:
                metric = alarm.get("MetricName")
                if metric:
                    existing_metric_names.add(metric)

            missing = []

            for logical_metric in required_metrics:
                real_names = METRIC_NAME_MAP.get(logical_metric, [])

                if not any(m in existing_metric_names for m in real_names):
                    missing.append(logical_metric)

            if missing:
                gaps.append({
                    "resource": resource_id,
                    "type": rtype,
                    "missing": missing
                })

    return gaps


# ---------------------------------------------------------
# Report formatting
# ---------------------------------------------------------

def format_report(gaps):
    if not gaps:
        return "All resources have required CloudWatch alarms."

    lines = ["CloudWatch Alarm Gap Report:\n"]

    for item in gaps:
        lines.append(f"{item['type']} {item['resource']} missing alarms:")
        for metric in item["missing"]:
            lines.append(f"  - {metric}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------
# HTML report generator
# ---------------------------------------------------------

def generate_html_report(gaps):
    html = []
    html.append("<html><head><style>")
    html.append("body{font-family:Arial;margin:20px;}")
    html.append("table{border-collapse:collapse;width:100%;}")
    html.append("th,td{border:1px solid #ccc;padding:8px;}")
    html.append("th{background:#f5f5f5;text-align:left;}")
    html.append("</style></head><body>")
    html.append("<h2>CloudWatch Alarm Gap Report</h2>")

    if not gaps:
        html.append("<p><b>All resources have required CloudWatch alarms.</b></p>")
        html.append("</body></html>")
        return "".join(html)

    html.append("<table>")
    html.append("<tr><th>Resource</th><th>Type</th><th>Missing Alarms</th></tr>")

    for item in gaps:
        missing = ", ".join(item["missing"])
        html.append(
            f"<tr><td>{item['resource']}</td>"
            f"<td>{item['type']}</td>"
            f"<td>{missing}</td></tr>"
        )

    html.append("</table></body></html>")
    return "".join(html)


# ---------------------------------------------------------
# S3 upload
# ---------------------------------------------------------

def context_timestamp():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")


def upload_report_to_s3(html_content):
    bucket = os.getenv("REPORT_S3_BUCKET")
    prefix = os.getenv("REPORT_S3_PREFIX", "reports")

    if not bucket:
        logger.warning("REPORT_S3_BUCKET is not set. Skipping S3 upload.")
        return None

    s3 = boto3.client("s3")

    key = f"{prefix}/report-{context_timestamp()}.html"

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=html_content.encode("utf-8"),
        ContentType="text/html"
    )

    return f"s3://{bucket}/{key}"


# ---------------------------------------------------------
# Slack notifications
# ---------------------------------------------------------

def send_report_slack(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL is not set. Skipping Slack notification.")
        return

    payload = {"text": message}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as response:
            logger.info(f"Slack message sent, status={response.getcode()}")
    except Exception as e:
        logger.error(f"Slack sending error: {str(e)}")


# ---------------------------------------------------------
# SNS notifications
# ---------------------------------------------------------

def send_report_sns(message):
    topic = os.getenv("SNS_TOPIC_ARN")
    if not topic:
        return

    sns = boto3.client("sns")
    sns.publish(
        TopicArn=topic,
        Message=message,
        Subject="CloudWatch Alarm Gap Report"
    )


# ---------------------------------------------------------
# Lambda entrypoint
# ---------------------------------------------------------

def lambda_handler(event, context):
    logger.info("Starting CloudWatch Alarm Gap Detector...")

    config = load_config()
    alarms = get_all_cloudwatch_alarms()

    resources = {
        "EC2": get_ec2_instances(),
        "RDS": get_rds_instances(),
        "ALB": get_load_balancers(),
        "Lambda": get_lambda_functions()
    }

    gaps = detect_gaps(resources, alarms, config)

    text_report = format_report(gaps)
    html_report = generate_html_report(gaps)
    s3_path = upload_report_to_s3(html_report)

    if s3_path:
        text_report += f"\nHTML report: {s3_path}"

    send_report_slack(text_report)
    send_report_sns(text_report)

    return {
        "status": "ok",
        "gaps_found": len(gaps),
        "report": text_report,
        "s3_report": s3_path
    }
