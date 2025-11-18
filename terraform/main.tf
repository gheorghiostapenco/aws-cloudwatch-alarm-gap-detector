provider "aws" {
  region = var.aws_region != "" ? var.aws_region : "us-east-1"
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "rds:DescribeDBInstances",
          "elasticloadbalancing:DescribeLoadBalancers",
          "lambda:ListFunctions",
          "cloudwatch:DescribeAlarms",
          "s3:PutObject",
          "sns:Publish"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "detector" {
  function_name = var.project_name
  role          = aws_iam_role.lambda_role.arn

  handler = "lambda_app.handler.lambda_handler"
  runtime = "python3.12"

  s3_bucket = var.lambda_s3_bucket
  s3_key    = var.lambda_s3_key

  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
      REPORT_S3_BUCKET  = var.report_s3_bucket
      REPORT_S3_PREFIX  = var.report_s3_prefix
      SNS_TOPIC_ARN     = var.sns_topic_arn
    }
  }
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.project_name}-schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "event_target" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "lambda"
  arn       = aws_lambda_function.detector.arn
}

resource "aws_lambda_permission" "eventbridge_permission" {
  statement_id  = "allow_eventbridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.detector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
