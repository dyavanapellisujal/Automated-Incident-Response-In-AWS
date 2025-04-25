resource "aws_iam_role" "ec2rolle" {
    for_each = toset(var.rolenames)
    assume_role_policy = file("${path.module}/assume_role_policy_for_ec2.json")
    
    name = each.value
    

    
}

resource "aws_iam_role" "lambda_role" {
    
    assume_role_policy = file("${path.module}/assume_role_policy_for_lambda.json")
    
    name = "lambda_for_automated_incident_response"


}

resource "aws_iam_role" "eventbridge_role" {
    assume_role_policy = file("${path.module}/assume_role_policy_for_eventbridge.json")
    name = "eventbridge_role_for_lambda"
}

resource "aws_iam_policy" "eventbridgepolicy_for_lambda" {
    name = "eventbridge_policy_to_access_lambda"
    policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": [
                "arn:aws:lambda:us-east-1:975688691050:function:unauthorized_access_events_handler"
            ]
        }
    ]
})
  
}

resource "aws_iam_policy" "lambda_for_automated_incident_response_policy" {
  name = "lambda_for_automated_incident_response_policy"
  policy = file("${path.module}/iam_policyrole_for_lambda.json")
  

}

resource "aws_iam_role_policy_attachment" "lambda_role_policy_attachment" {
    role = aws_iam_role.lambda_role.name
    policy_arn = aws_iam_policy.lambda_for_automated_incident_response_policy.arn
  
}

resource "aws_iam_role_policy_attachment" "admin_policy" {
    for_each = toset(var.rolenames)
    role       = aws_iam_role.ec2rolle[each.value].name
    policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

  
}



resource "aws_iam_instance_profile" "ec2rolle_instance_profile" {
    
    name = aws_iam_role.ec2rolle[var.rolenames[0]].name
    role = aws_iam_role.ec2rolle[var.rolenames[0]].name

  
}





