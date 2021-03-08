resource "aws_cloudwatch_log_group" "lamda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_event_rule" "health_events" {
  name        = var.function_name
  description = "Capture AWS platform health notifications"

  event_pattern = <<EOF
{
  "source": [
    "aws.health"
  ]
}
EOF
}

resource "aws_cloudwatch_event_target" "health_event_target" {
  arn  = aws_lambda_function.acp_health_notifier.arn
  rule = aws_cloudwatch_event_rule.health_events.id
}
