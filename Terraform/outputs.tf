output "awsinstanceid" {
  value = module.ec2module.ec2-id

  
}

output "awsinstanceip" {
  value = module.ec2module.ec2-publicip
  
}

output "lambda_arn" {
  value = module.lambdamodule.lambda_arn
  
}

output "guardutydetectorid" {
  value = module.guardutymodule.detectionid

  
}

output "evenbridgerule_arn" {
  value = module.eventbridgemodule.arn
  
}

output "sns_topic_arn" {
  value = module.SNSmodule.topic_arn
  
}
output "iamroles_instance_profiles" {
  value = module.IAMmodule.instance_profile
  
}
