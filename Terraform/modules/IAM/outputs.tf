output "instance_profile" {
    value = aws_iam_instance_profile.ec2rolle_instance_profile.name


  
}

output "lambda_role_arn" {
    value = aws_iam_role.lambda_role.arn
  
}