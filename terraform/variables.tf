variable "project_name" {
  description = "Name prefix for all created resources"
  type        = string
  default     = "cloudwatch-alarm-gap-detector"
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing Lambda deployment package"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key of Lambda deployment package (ZIP file)"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL"
  type        = string
  sensitive   = true
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (e.g. rate(1 day))"
  type        = string
  default     = "rate(1 day)"
}
