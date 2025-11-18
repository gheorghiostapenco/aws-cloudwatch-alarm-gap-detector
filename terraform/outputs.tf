output "lambda_function_name" {
  value = aws_lambda_function.detector.function_name
}

output "event_rule_arn" {
  value = aws_cloudwatch_event_rule.schedule.arn
}

output "iam_role_arn" {
  value = aws_iam_role.lambda_role.arn
}
