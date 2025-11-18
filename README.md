# AWS CloudWatch Alarm Gap Detector

A fully automated tool that scans AWS resources, detects missing CloudWatch alarms, and reports gaps via Slack, SNS, and an optional HTML report stored in S3.

This project helps DevOps, SRE, and Cloud Engineers ensure complete monitoring coverage across EC2, RDS, ALB/NLB, and Lambda resources.

---

## 🚀 Features

- Detect missing CloudWatch alarms for:
  - **EC2**
  - **RDS**
  - **ALB/NLB**
  - **Lambda**
- Configurable required metrics via `config.yaml`
- Logical → real metric mapping (e.g., `HTTPCode_ELB_5XX` → multiple CloudWatch metric names)
- Resource-to-alarm matching using:
  - Alarm name
  - CloudWatch dimensions
  - ARN suffix (for ALB/NLB)
- Tag-based resource filtering (e.g., monitor only `Environment=prod`)
- Slack notifications
- Optional SNS notifications (email or messaging)
- HTML report uploaded to S3
- Unit tests (pytest)
- Terraform deployment
- Makefile for Lambda ZIP build


## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```
2. Install dependencies
```bash
pip install -r lambda_app/requirements.txt
```
3. Install test dependencies
```bash
pip install pytest
```
## Running Tests
```bash
pytest -q
```
or guaranteed:

```bash
python3 -m pytest -q
```

## Local Lambda Execution
```bash

cd lambda_app
python3 - << 'EOF'
import handler
print(handler.lambda_handler({}, {}))
EOF
```

## Configuration (config.yaml)
lambda_app/config.yaml defines required metrics and optional tag filters:

```bash 
required:
  EC2:
    - CPUUtilization
    - StatusCheckFailed
  RDS:
    - FreeStorageSpace
    - CPUUtilization
  ALB:
    - HTTPCode_ELB_5XX
  Lambda:
    - Errors
    - Throttles

filter:
  tag_key: "Environment"
  tag_value: "prod"
If no filter is provided, all resources are scanned.
```

## Building the Lambda ZIP

```
make build
```

This produces:

```bash
lambda.zip
```

Upload manually:

```bash
make upload BUCKET=my-bucket KEY=lambda.zip
```

## Deploying with Terraform

Fill required variables in terraform/variables.tf

Deploy:

```bash

cd terraform
terraform init
terraform apply
```

Minimum required variables:

lambda_s3_bucket

lambda_s3_key

slack_webhook_url

report_s3_bucket

Example:

```bash
terraform apply \
  -var="lambda_s3_bucket=my-bucket" \
  -var="lambda_s3_key=lambda.zip" \
  -var="slack_webhook_url=https://hooks.slack.com/services/AAA/BBB/CCC" \
  -var="report_s3_bucket=my-report-bucket"
```

## Slack Notifications
Set the environment variable:

SLACK_WEBHOOK_URL=<your webhook>

The Lambda posts a report message after every run.

## SNS / Email Notifications (Optional)
Set:

SNS_TOPIC_ARN=<your SNS Topic ARN>
A copy of the report will be sent to SNS.

## HTML Reports
Lambda generates a human-readable HTML report and uploads it to S3:

```bash
s3://<bucket>/<prefix>/report-YYYY-MM-DD-HH-MM-SS.html
```
The Slack message includes a link to the file.

## How the Detection Works
Collects EC2, RDS, ALB, and Lambda resources

Applies optional tag filtering

Collects all CloudWatch alarms

Matches alarms to resources using:

Name contains ID

CloudWatch dimensions

ARN suffix (for ALB/NLB)

Compares alarms to required metric set

Generates a text report

Sends Slack notification

Sends SNS notification (if configured)

Generates and uploads an HTML report to S3

## Requirements
Python 3.11 or 3.12

AWS IAM permissions:

ec2:DescribeInstances

rds:DescribeDBInstances

elasticloadbalancing:DescribeLoadBalancers

lambda:ListFunctions

cloudwatch:DescribeAlarms

s3:PutObject

sns:Publish (if used)

Terraform ≥ 1.0

## Makefile Commands
```bash
make build     # Build Lambda ZIP
make clean     # Remove ZIP
make upload    # Upload ZIP to S3
```

Example:

```bash
Copy code
make upload BUCKET=my-bucket KEY=lambda.zip
```

## Potential Enhancements
Add AWS mocks with moto

GitHub Actions CI/CD pipeline

More CloudWatch metric packs (SQS, DynamoDB, API Gateway)

Automatic alarm generation

Rich email/HTML templates with charts

## License
MCopyright <2025> <Gheorghi Ostapenco>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Support
If you want CI/CD automation, packaging, Docker support, or new AWS integrations — feel free to ask.