output "lambda_arn" {
    value = aws_lambda_function.unauthorized_access_events_handler.arn


  
}

output "lambda_id" {

    value = aws_lambda_function.unauthorized_access_events_handler.id
}

output "lambda_function_name" {
    value = aws_lambda_function.unauthorized_access_events_handler.function_name
  
}