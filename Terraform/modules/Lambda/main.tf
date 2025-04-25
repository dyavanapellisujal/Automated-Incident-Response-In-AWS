data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda_code.py"
  output_path = "lambda_function_payload.zip"
}



resource "aws_lambda_function" "unauthorized_access_events_handler" {
    function_name = "unauthorized_access_events_handler"
    role = var.role_arn
    filename = "lambda_function_payload.zip"
    handler = "lambda_function.lambda_handler"
    runtime = "python3.13"
    source_code_hash = data.archive_file.lambda.output_base64sha256
    
  
}