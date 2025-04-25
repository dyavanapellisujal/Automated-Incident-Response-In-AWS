module "s3module" {
    source = "./modules/S3"
    bucketname = var.bucket_name
    
    
}

module "networkingmodule" {
    source = "./modules/Networking"
    
}

module "IAMmodule" {
    source = "./modules/IAM"
  
}

module "ec2module" {
    depends_on = [ module.IAMmodule ]
    source = "./modules/EC2"
    s3_bucket = module.s3module.ssrftestbucket
    s3_flaskfile_key = module.s3module.ssrfflaskserver
    sg_id = module.networkingmodule.sgid
    instanceprofile = module.IAMmodule.instance_profile
  
}
module "SNSmodule" {
    depends_on = [ module.IAMmodule ]
    source = "./modules/SNS"
    account-id = var.account-id
  
}
module "lambdamodule" {
    depends_on = [ module.IAMmodule  ]
    source = "./modules/Lambda"
    role_arn = module.IAMmodule.lambda_role_arn
    sns_topic_arn = module.SNSmodule.topic_arn

}

module "guardutymodule" {
    source = "./modules/GuardDuty"
  
}

module "eventbridgemodule" {
    depends_on = [ module.IAMmodule , module.guardutymodule , module.lambdamodule ]
    source = "./modules/Eventbridge"
    lambda_arn = module.lambdamodule.lambda_arn
    function_name = module.lambdamodule.lambda_function_name

  
}