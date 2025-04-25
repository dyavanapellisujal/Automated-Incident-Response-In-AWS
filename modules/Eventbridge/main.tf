

resource "aws_cloudwatch_event_rule" "unauthorizedaccessrule" {
  name        = "Unauthorized_access_IAM_rule"
  description = "Capture all unauthorized access guarddutyfindings"

  event_pattern = file("${path.module}/eventrulepattern.json")
}

resource "aws_lambda_permission" "resourcebasedpolicy_for_eventbridge" {
  statement_id = "Allowinvokefunctionfromeventbridge"
  action = "lambda:InvokeFunction"
  function_name = var.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.unauthorizedaccessrule.arn
  
}

resource "aws_cloudwatch_event_target" "lambdatarget" {
    rule = aws_cloudwatch_event_rule.unauthorizedaccessrule.name
    target_id = "Triggerlambda"
    arn = var.lambda_arn
    
  
}