Serverless Incident Response Workflow on AWS Using GuardDuty, EventBridge, SNS & Lambda.
Hey everyone! In this blog, I'll walk you through how I built an automated incident response system in an AWS environment using native AWS services. This project demonstrates how to detect threats using Amazon GuardDuty and automatically respond to them using EventBridge, Lambda, and SNS.
If you're curious about how automated incident response can work in AWS using AWS native services or want to implement a similar setup yourself, follow along with this blog for a full breakdown.
Understanding Amazon GuardDuty
Amazon GuardDuty is a threat detection service that continuously monitors your AWS environment for malicious activity and unauthorized behavior. It's a fully managed service, which means you don't need to create custom rules or manage threat intelligence feeds - AWS takes care of that for you.
GuardDuty analyzes VPC Flow Logs, AWS CloudTrail logs, and Route 53 DNS query logs using machine learning, anomaly detection, and threat intel from AWS and other sources. When it detects suspicious activity - such as known attack patterns, credential misuse, or abnormal behavior - it generates a finding.
In this project, I focused on a specific GuardDuty finding:
 UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS
 This alert is triggered when AWS detects that IAM instance credentials have been potentially exfiltrated and used from outside the AWS network, which is a strong indicator of compromise.
You can explore the full list of GuardDuty findings and their descriptions here.
Understanding the Attack and GuardDuty Finding: UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS
In this project, I'll demonstrate how unauthorized exfiltration of EC2 instance credentials can occur, and how Amazon GuardDuty helps detect such suspicious activity through a specific finding.
Attack Scenario
Let's consider an EC2 instance running a web application vulnerable to Server-Side Request Forgery (SSRF). If the instance is using Instance Metadata Service Version 1 (IMDSv1), an attacker can exploit the SSRF vulnerability to make the application send HTTP requests to the EC2 Instance Metadata API. This allows the attacker to retrieve temporary IAM credentials associated with the instance.
Since the credentials are temporary and the SSRF vulnerability remains open, the attacker can continuously fetch new STS credentials, effectively maintaining persistent access.
Credential Extraction Methods
IMDSv1 (Less Secure - No Token Required):

curl http://169.254.169.254/latest/meta-data/iam/security-credentials/ec2rolle
IMDSv2 (More Secure - Requires a Token):

TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"` && \
curl -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/ec2rolle
Note: This is only possible if the application allows PUT requests, which are required to fetch the IMDSv2 token.
Why This Matters
If the IAM role assigned to the instance has access to sensitive S3 buckets, databases, or other critical AWS resources, these credentials can be used by the attacker to exfiltrate data or perform malicious actions in your AWS account.
Detection by AWS GuardDuty
Once the attacker obtains the instance credentials, they might attempt to use them from a different location - such as a personal computer or a remote VPS (Virtual Private Server) - outside the AWS environment where the credentials were originally issued.
Amazon GuardDuty is designed to detect exactly this kind of anomalous activity. It triggers the following finding:
UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS
This finding is based on the observation that API calls made using the instance credentials originate from a non-AWS IP address or gateway - which is unusual. Normally, credentials tied to an EC2 instance are only expected to be used within AWS infrastructure.
GuardDuty uses CloudTrail logs to identify this behavior. If it sees that API calls are coming from an external gateway rather than the typical AWS gateway, it flags it as suspicious - an indication that the credentials may have been stolen and are now being misused.
Diagram:
Enabling GuardDuty via AWS CLI
To enable GuardDuty in your AWS environment using the AWS CLI, you can run the following command:
aws guardduty create-detector --enable
This command creates and enables a GuardDuty detector in the default region configured in your AWS CLI profile. Once enabled, GuardDuty starts monitoring your AWS resources - such as VPC Flow Logs, CloudTrail, and DNS logs - for suspicious activity.
Simulating an Attack to Generate a GuardDuty Finding
Here's my current GuardDuty Dashboard, quietly watching over my AWS environment like a digital security guard. But it's a little too quiet - so let's stir things up (ethically, of course).
To properly test our automated incident response setup, we need to trigger a real GuardDuty finding, not just the synthetic ones AWS gives us.
Sure, you can run aws guardduty create-sample-findings and get instant alerts - but that's like running a fire drill without any smoke. Great for a demo, but not exactly helpful if you want to see your actual automation in action.
So, I rolled up my sleeves and built a Flask application with a deliberately introduced SSRF vulnerability. The flaw is tucked inside the /fetch endpoint, which accepts a URL from the user and fetches its contents using server-side logic.
Code for the SSRF-Vulnerable attack
from flask import Flask, request
import requests
app = Flask(__name__)
@app.route("/")
def home():
    return "SSRF Vulnerable App - Use /fetch?url=http://example.com"
# Vulnerable endpoint
@app.route("/fetch")
def fetch():
    target_url = request.args.get("url")
    if not target_url:
        return "URL parameter is required", 400
    try:
        response = requests.get(target_url)  # No validation, making it vulnerable
        return response.text
    except requests.exceptions.RequestException as e:
        return str(e), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
This design opens the door for an attacker to manipulate requests - and more dangerously, make the app reach into AWS internal services. The main target? The Instance Metadata Service (IMDS). If the instance is using IMDSv1, no authentication token is needed, making it easy pickings for extracting temporary IAM credentials.
⚠️ Disclaimer: This is a controlled simulation in a secure, test environment. Please don't test your luck by running vulnerable apps in production - unless you enjoy surprises on your AWS bill.
Exposing the Application and Extracting Credentials
For the simulation, I exposed port 80 of my EC2 instance to the internet so the vulnerable Flask application could be accessed externally.
Here's what the index page looks like (no fancy UI here - just straight to business):
Now, let's try accessing the EC2 Instance Metadata Service (IMDS) through the SSRF-vulnerable /fetch endpoint:
http://54.146.253.8/fetch?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/ec2rolle
As you can see, the application happily returned the temporary IAM credentials right to the client - which is exactly the kind of behavior GuardDuty keeps an eye out for.
To simulate a real-world exfiltration attempt, I took the stolen credentials and configured them on a VM running in my home network - i.e., outside the AWS environment. This mimics an attacker who has successfully stolen credentials and is now trying to use them from an external location.
Here's how I configured the credentials using the AWS CLI:
aws configure set aws_access_key_id <access_key> --profile actor
aws configure set aws_secret_access_key <secret_key> --profile actor
aws configure set aws_session_token --profile actor
At this point, any AWS API call made using the actor profile will originate from a non-AWS IP - which is exactly the signal GuardDuty needs to detect unauthorized credential use outside the AWS network.
Then, I ran a simple command to test their validity by listing IAM users, To take things a step further (and spice up the detection a bit), I routed my requests through Tor using proxychains. This mimics an attacker trying to stay anonymous while probing the environment - a common tactic in real-world attacks. Here's the effect:
UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS - triggered by the credential usage outside AWS.
Recon:IAMUser/TorIPCaller - triggered by IAM enumeration via a known Tor exit node.

proxychains aws iam list-users --profile actor
This type of activity helps highlight just how risky it is to assign overly permissive IAM roles. If the principle of least privilege (PoLP) isn't enforced, the blast radius increases significantly. For instance, a policy with "Action": "s3:*" and "Resource": "*" could allow an attacker to access or exfiltrate sensitive data from any S3 bucket in the account.
GuardDuty in Action: Detecting the Threat
Now that the attack has been carried out, it's time to check whether GuardDuty picked up on the activity.
According to AWS, GuardDuty provides near real-time detection. In my case, the finding UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS showed up in the GuardDuty console in under 5 minutes.
This validates that GuardDuty is actively monitoring API calls and can detect suspicious usage patterns - especially when credentials are used from outside AWS infrastructure.
Responding to the Incident
Once the GuardDuty finding appeared, it was time to kick off the automated incident response flow.
I configured an Amazon EventBridge rule to listen for findings related to UnauthorizedAccess. When such an event is detected, it triggers a Lambda function that performs the following remediation steps:
Automated Remediation Workflow
Identify the compromised EC2 instance: Inspect the IAM role associated with the temporary credentials used in the GuardDuty finding. This helps trace the specific EC2 instance involved in the incident.
Block the attacker's IP: Modify the Network ACL attached to the subnet to add a DENY rule for both ingress and egress traffic from the attacker's IP. (While a security group can also be used, it's limited to specific instances. NACLs operate at the subnet level and provide broader, quicker containment.)
Enforce IMDSv2: Switch the instance metadata service to IMDSv2 only. IMDSv2 requires a PUT request with a session token, and since the vulnerable endpoint only supports GET, this effectively blocks further access to metadata and prevents credential theft via SSRF.
Detach the compromised IAM role and attach a backup role: Detach the IAM role that was compromised. Attach a backup IAM role, named using the convention: original-role-name-backup, to all instances that were using the original role. This invalidates the STS credentials associated with the compromised role while ensuring minimal downtime and then delete the previous role.
Force credential invalidation :Instead of waiting for the temporary STS credentials to expire (which could take up to 6–12 hours), the role swap invalidates them immediately, reducing the attack window significantly.
Send an SNS alert: Notify the security team (aka me 😅) by publishing a message to an SNS topic indicating:

The instance involved
The remediation steps executed
The status of each action

⚠️ A Note on Application Behavior
This step assumes the application interacts with AWS services using SDKs (like boto3), which automatically refresh credentials from IMDS. So, detaching and reattaching the IAM role will briefly interrupt access - but the SDK handles it smoothly under the hood.
However, if the application is directly using static connection strings (e.g., connecting to RDS via something like
 postgresql://user:password@mydb-instance.rds.amazonaws.com:5432/mydb), then you're in for a bit of extra work.
 In such cases, you'd need to add retry logic or failure handling in your app code - because once the role is detached,
 credentials vanish momentarily. Without proper handling, the app could crash or hang, which is no fun in the middle of an incident.
An image from how sdk's handle credCreating the Automated Response Flow with Lambda and EventBridge
To kick off the response mechanism, I first created an AWS Lambda function.
Creating the EventBridge Rule
I use Amazon EventBridge to monitor for GuardDuty findings that signal high-severity unauthorized access attempts on IAM. Here's the command I used to create the rule:
aws events put-rule \
  --name GuardDutyFindings \
  --event-pattern file://event-pattern.json \
  --state ENABLED
Here's what event-pattern.json looks like:
{
  "source": ["aws.guardduty"],
  "detail": {
    "type": [{
      "prefix": "UnauthorizedAccess:IAMUser/"
    }],
    "severity": [{
      "numeric": [">=", 7.0]
    }]
  }
}
This pattern ensures the rule only triggers for UnauthorizedAccess events involving IAM users with a severity score of 7.0 or higher - in other words, only high severity findings.
Setting the Rule Target: Lambda
Next, I needed to wire the rule to the Lambda function. I had already created an IAM role named Invoke_Lambda_eventbridge with the following permissions:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:975688691050:function:UnauthorizedAccess-IAM-Handler"
    }
  ]
}
Then, I connected the rule to the Lambda using:
aws events put-targets \
  --rule GuardDutyFindings \
  --targets "Id"="Lambda","Arn"="arn:aws:lambda:us-east-1:975688691050:function:UnauthorizedAccess-IAM-Handler","RoleArn"="arn:aws:iam::975688691050:role/service-role/Lambda_Invoke_eventbridge"
Granting EventBridge Permission to Invoke Lambda
By default, AWS Lambda does not allow other AWS services to invoke it unless explicitly permitted. So, I added a resource-based policy to allow EventBridge to trigger this function:
aws lambda add-permission \
  --function-name UnauthorizedAccess-IAM-Handler \
  --statement-id Eventbridgepermission \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:975688691050:rule/GuardDutyFindings
And just like that, I've wired GuardDuty → EventBridge → Lambda into a sweet automated incident response pipeline.
Creating an SNS Topic for Notifications
To keep things alert and loud (because what's the point of automation if no one hears about it?), I set up an SNS topic that the Lambda function will use to send notifications.
Here's a simple bash script to do that:
#!/bin/bash
# Create SNS topic and capture the ARN
topic_arn=$(aws sns create-topic --name failed_login_attempts | jq -r .[])
# Subscribe an email address to the topic
aws sns subscribe \
  --topic-arn "$topic_arn" \
  --protocol email \
  --notification-endpoint "sujaldyavanapelli80@gmail.com"
After running this, I received a confirmation email - clicked "Confirm subscription" so that the alerts won't scream into the void!
Keeping Track of NACL Rule Numbers with Parameter Store
To avoid NACL rule number collisions (which can break things), I stored the current rule number in SSM Parameter Store under:
/nacl/<naclid>
This helps the Lambda keep track of what rule number it last used - no more overwriting or duplication!
Alternative Approach
Another way to manage rule numbers would be to:
Loop through the entire range of rule numbers supported by AWS NACLs (0–32766).
Check each one to find an unused number.
Add your rule using the first available slot.

But to keep things structured and priority-aware, I follow this approach:
Assign broad rules (like default allow/deny for internet access) higher rule numbers (i.e., lower priority),
 and give narrow, high-importance rules (like IP blocks) lower rule numbers (i.e., higher priority).
This ensures that the most critical rules - like blocking an attacker's IP - are processed first by the NACL engine.
Setting Up IAM Role for the Lambda Function
I created an IAM role named lambda_for_automated_response and attached the following policies:
AWSLambdaBasicExecutionRole (provided by AWS)
A custom policy (more on that in a sec - probably includes permissions to modify NACLs, detach roles, etc.)

Custom Policy:
I made sure that the policy follows the principle of "Least Privilege".
{
 "Version": "2012-10-17",
 "Statement": [
  {
   "Sid": "Modifyec2andSNSPublish",
   "Effect": "Allow",
   "Action": [
    "ec2:ModifyInstanceMetadataOptions",
    "sns:Publish",
    "ec2:DisassociateIamInstanceProfile",
    "ec2:ModifyInstanceAttribute",
    "ec2:AssociateIamInstanceProfile"
   ],
   "Resource": [
    "arn:aws:sns:us-east-1:975688691050:Unauthorized_Access_IAMUser",
    "arn:aws:ec2:us-east-1:975688691050:instance/*",
    "arn:aws:ec2:us-east-1:975688691050:security-group/*"
   ]
  },
  {
   "Sid": "Describeproperties",
   "Effect": "Allow",
   "Action": [
    "ec2:DescribeInstances",
    "ec2:DescribeIamInstanceProfileAssociations",
    "ec2:DescribeNetworkAcls",
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeInstanceStatus"
   ],
   "Resource": "*"
  },
  {
   "Sid": "SecurityGroupandNACL",
   "Effect": "Allow",
   "Action": [
    "ec2:RevokeSecurityGroupIngress",
    "ec2:AuthorizeSecurityGroupEgress",
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:RevokeSecurityGroupEgress",
    "ec2:CreateNetworkAclEntry",
    "ec2:DeleteNetworkAclEntry"
   ],
   "Resource": [
    "arn:aws:ec2:us-east-1:975688691050:security-group/*",
    "arn:aws:ec2:us-east-1:975688691050:network-acl/*",
    "arn:aws:ec2:us-east-1:975688691050:security-group-rule/*"
   ]
  },
  {
   "Sid": "Passrole",
   "Effect": "Allow",
   "Action": "iam:PassRole",
   "Resource": "arn:aws:iam::975688691050:role/*",
   "Condition": {
    "StringEquals": {
     "iam:PassedToService": "ec2.amazonaws.com"
    }
   }
  },
  {
   "Sid": "IAMandSSM",
   "Effect": "Allow",
   "Action": [
    "iam:CreateInstanceProfile",
    "iam:GetInstanceProfile",
    "iam:ListAttachedRolePolicies",
    "iam:ListRolePolicies",
    "iam:AddRoleToInstanceProfile",
    "iam:DetachRolePolicy",
    "iam:DeleteRolePolicy",
    "iam:DeleteRole",
    "iam:ListInstanceProfilesForRole",
    "iam:RemoveRoleFromInstanceProfile",
    "ssm:PutParameter",
    "ssm:GetParameter"
   ],
   "Resource": [
    "arn:aws:iam::975688691050:instance-profile/*",
    "arn:aws:iam::975688691050:role/*",
    "arn:aws:ssm:us-east-1:975688691050:parameter/nacl/*"
   ]
  }
 ]
}
Once the policies were in place, I attached this role to the Lambda function.
Creating a Backup Role
I created a backup IAM role named ec2rolle-backup, following the naming convention of appending -backup to the original role name (ec2rolle). This backup role will be used for reassignment during the remediation process.
✅ So everything is now set up - the EventBridge rule, SNS topic, IAM roles, and SSM Parameter Store are all in place. The final piece of the puzzle is wiring up the Lambda logic.
 The Lambda code that brings it all together can be found here. It reads the GuardDuty finding type, executes the appropriate remediation actions, and sends out an SNS alert summarizing the response status. Think of it as the conductor making sure every part of the automation orchestra hits the right note.
Testing the Full Pipeline
I re-executed the attack scenario to validate the complete automation workflow - from detection by GuardDuty to remediation via the Lambda function.
Configured the creds on to my terminal again with the profile - actor and executed commands.
As expected, the finding showed up in the GuardDuty dashboard. At this point, I should've also received an email notification via SNS.
Then I verified if remediation was actually successful on the infrastructure
IMDSv2 enforced ✅.
Role changed with backup role
NACL Updated ✅
Credentials Invalid✅
Wrapping-up
This project was a great exercise in automating cloud security responses using native AWS tools. It simulates a real-world attack and builds a robust pipeline to detect, contain, and notify - all within minutes.
I'll also be uploading the Terraform and Boto3 scripts used to set up this project on my GitHub repo, so stay tuned if you'd like to replicate it in your own environment.
Open to suggestions for improvements - would love to hear your thoughts!
Until then - secure all the things! 🔐
