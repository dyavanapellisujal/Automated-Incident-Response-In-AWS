import json

import boto3
import ipaddress
iam_client=boto3.client("iam")
client = boto3.client("ec2")
ssm_client= boto3.client("ssm")
resp = "No remediation performed"



def lambda_handler(event, context):
    finding_type = event.get("Type", "Type field not found")
    description= event.get("Description", "Description field not found")
    severity = event.get("Severity", "Severity field not found")
    # Extract instance details
    instance_id = event.get("Resource", {}).get("InstanceDetails", {}).get("InstanceId", "InstanceId not found")

    # Extract attacker's IP
    attacker_ip = event.get("Service", {}).get("Action", {}).get("AwsApiCallAction", {}).get("RemoteIpDetails", {}).get("IpAddressV4", "IP Address not found")
    access_key_role = event.get("Resource", {}).get("AccessKeyDetails", {}).get("UserName","role name not found")

    if is_ipv4(attacker_ip):
        attacker_ip = attacker_ip + "/32"
    elif is_ipv6(attacker_ip):
        attacker_ip = attacker_ip + "/128"

    if finding_type == "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS":
        print(finding_type)
        resp = remediate_InstanceCredentialExfiltrationOutsideAWS(instance_id, attacker_ip,description,severity,finding_type,access_key_role)
    return {
        "statusCode": 200,
        "body": json.dumps({"resp": resp})
    }


def is_ipv4(ip):
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
    except ValueError:
        return False 

def is_ipv6(ip):
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except ValueError:
        return False  # Invalid IP format

def remediate_InstanceCredentialExfiltrationOutsideAWS(instance_id,attacker_ip,description,severity,finding_type,access_key_role):
    sns_client = boto3.client('sns')
    sns_topic_arn = 'arn:aws:sns:us-east-1:youraccountnumber:Unauthorized_Access_IAMUser'
     sns_client.publish(
        TopicArn=sns_topic_arn,
        Message="Lambda triggered",
        Subject='⚠️ IAM Role Credentials Compromised'
    )
    
    instance_id=instance_id
    response = client.describe_instances(InstanceIds=[instance_id])
    subnet_id = response['Reservations'][0]['Instances'][0]['SubnetId']

    

    response = client.describe_network_acls(
        Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}])

    for nacl in response['NetworkAcls']:
        parameter=f'/nacl/{nacl["NetworkAclId"]}'
        response = ssm_client.get_parameter(Name=parameter)
        rule_number = int(response['Parameter']['Value'])

        if add_nacl_rule_entry(nacl_id=nacl['NetworkAclId'],port_range=(0,65535),egress=False,cidr_block=attacker_ip,rule_number=rule_number):
            ingress_deny_rule=f"Successfully added a deny rule for {attacker_ip}"
        else:
            ingress_deny_rule=f"Could not add a deny rule for {attacker_ip}"
        
        if add_nacl_rule_entry(nacl_id=nacl['NetworkAclId'], port_range=(0, 65535), egress=True,cidr_block=attacker_ip,rule_number=rule_number):
            egress_deny_rule=f"Successfully added a deny rule for {attacker_ip}"
        else:
            egress_deny_rule=f"Could not add a deny rule for {attacker_ip}"
        next_rule_number = rule_number + 1

    # Save it back to SSM
        ssm_client.put_parameter(
            Name=parameter,
            Value=str(next_rule_number),
            Overwrite=True,
            Type='String'
        )

        


    

    if imds_modify(instance_id=instance_id): #This will modify the instance metadata service to V2.
        imds_modified = "Successfully modified IMDS to v2"
        
    else:
        imds_modified = "Could not modify IMDS to v2"
    

    #THe below code will detach the compromised role and then atTach the backup role created beforehand assuming this situation.

    if reattach_iam_policy(instance_id=instance_id, access_key_role=access_key_role):
        reattach_iam_policy_status = "Successfully reattached the IAM role to the instance"
    else:
        reattach_iam_policy_status = "Could not reattach the IAM role to the instance"


    #The below code is to send the alert via sns to security team : that is me in this case 
    sns_client = boto3.client('sns')
    sns_topic_arn = 'arn:aws:sns:us-east-1:youraccountnumber:Unauthorized_Access_IAMUser'

    message = ( 
        f"🔐 *IAM Role Credentials Compromised*\n\n"
        f"📌 *Finding Details:*\n"
        f"• Type: {finding_type}\n"
        f"• Description: {description}\n"
        f"• Severity: {severity}\n"
        f"• Attacker IP: {attacker_ip}\n\n"
        f"🖥️ *Affected Resources:*\n"
        f"• Instance ID: {instance_id}\n"
        f"• IAM Role: {access_key_role}\n\n"
        f"🛠️ *Remediation Status:*\n"
        f"• NACL Rule Update: Ingress = {ingress_deny_rule}, Egress = {egress_deny_rule}\n"
        f"• IMDS Version Update: {imds_modified}\n"
        f"• IAM Policy Reattachment: {reattach_iam_policy_status}\n"
    )

    sns_client.publish(
        TopicArn=sns_topic_arn,
        Message=message,
        Subject='⚠️ IAM Role Credentials Compromised'
    )

    return "Success"
def add_nacl_rule_entry(nacl_id,port_range,egress,cidr_block,rule_number):
     try : 
        response = client.create_network_acl_entry(
        NetworkAclId=nacl_id,
        RuleNumber=rule_number,
        Protocol='-1',  # -1 for all the Protocols, 6 for TCP, 17 for UDP
        RuleAction="deny",
        Egress=egress,  #if false it will add as an inbound rule, if true then it will add as an outbound rule
        CidrBlock=cidr_block,
        PortRange={
            'From': port_range[0],
            'To': port_range[1]
        },
     

     )
        return True
     except Exception as e:
        print(e)
        return False
         
''' This function will go through all instances using IMDSv1 and modify them to IMDSv2'''
def imds_modify(instance_id):
    
    try:
        updated_instances = []
        paginator = client.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    metadata_options = instance.get('MetadataOptions', {})
                    http_tokens = metadata_options.get('HttpTokens', 'optional')

                    if http_tokens == 'optional':  # IMDSv1 allowed
                        instance_id = instance['InstanceId']
                        client.modify_instance_metadata_options(
                            InstanceId=instance_id,
                            HttpTokens='required',         
                            HttpEndpoint='enabled'
                        )
                        updated_instances.append(instance_id)

        
        return True

    except Exception as e:
        print('imdserror',e)
        return False


'''This function will Creates new instance profile for the backup role if not exists and adds the role to that instance profile 
then will get the role and check the instances using the compromised role, adds them to a LisT and then iterates over the list to detach the role and attach the new one to the instances. ''' 
def reattach_iam_policy(instance_id,access_key_role):
   
    try:    
        backup_role = access_key_role + "-backup"
        profile_name = backup_role
        role_name = backup_role  # Assuming role and profile share name

        # Step 1: Ensure instance profile exists
        try:
            iam_client.create_instance_profile(InstanceProfileName=profile_name)
            print(f" Created instance profile: {profile_name}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            print(f"Instance profile {profile_name} already exists. Skipping creation.")

        # Step 2: Ensure role is attached to instance profile
        response = iam_client.get_instance_profile(InstanceProfileName=profile_name)
        roles = response['InstanceProfile']['Roles']
        role_already_added = any(role['RoleName'] == role_name for role in roles)

        if not role_already_added:
            try:
                iam_client.add_role_to_instance_profile(
                    InstanceProfileName=profile_name,
                    RoleName=role_name
                )
                print(f" Added role {role_name} to instance profile {profile_name}")
            except iam_client.exceptions.LimitExceededException:
                print(f" Cannot add more roles to instance profile {profile_name}")
        else:
            print(f"Role {role_name} is already attached to instance profile {profile_name}")

        # Step 3: Find instances using the original role
        matching_instances = []
        response = client.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                profile = instance.get('IamInstanceProfile')
                if profile:
                    attached_profile_name = profile['Arn'].split('/')[-1]
                    if attached_profile_name == access_key_role:
                        matching_instances.append(instance['InstanceId'])

        # Step 4: Reattach with backup role
        for instance_id in matching_instances:
            response = client.describe_iam_instance_profile_associations(
                Filters=[
                    {'Name': 'instance-id', 'Values': [instance_id]}
                ]
            )

            associations = response.get('IamInstanceProfileAssociations', [])
            if associations:
                association_id = associations[0]['AssociationId']

                client.disassociate_iam_instance_profile(
                    AssociationId=association_id
                )
                print(f" Disassociated profile from instance: {instance_id}")

                client.associate_iam_instance_profile(
                    IamInstanceProfile={'Name': profile_name},
                    InstanceId=instance_id
                )
                print(f"🔗 Associated backup profile to instance: {instance_id}")
            
        delete_iam_role(access_key_role)
        
        return True

        
    except Exception as e:
        print("function3",e)
        return False



def delete_iam_role(role_name):
    try:
        # Step 0: Detach from all instance profiles
        instance_profiles = iam_client.list_instance_profiles_for_role(RoleName=role_name)
        for profile in instance_profiles['InstanceProfiles']:
            profile_name = profile['InstanceProfileName']
            try:
                iam_client.remove_role_from_instance_profile(
                    InstanceProfileName=profile_name,
                    RoleName=role_name
                )
                print(f" Removed role {role_name} from instance profile: {profile_name}")
            except Exception as e:
                print(f" Failed to remove role from profile {profile_name}: {e}")

        # Step 1: Detach all managed policies
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies['AttachedPolicies']:
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy['PolicyArn']
            )
            print(f"Detached policy: {policy['PolicyArn']}")

        # Step 2: Delete all inline policies
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in inline_policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
            print(f" Deleted inline policy: {policy_name}")

        # Step 3: Delete the role
        iam_client.delete_role(RoleName=role_name)
        print(f"Deleted IAM role: {role_name}")

    except iam_client.exceptions.NoSuchEntityException:
        print(f" Role {role_name} does not exist.")
    except Exception as e:
        print(f" Failed to delete role {role_name}: {str(e)}")





