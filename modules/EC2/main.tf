locals {
  flask_file = "${tostring(var.s3_bucket)}/${tostring(var.s3_flaskfile_key)}"
}




data "aws_ami" "amazon_linux_2" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["137112412989"] # Official Amazon Linux AMI owner ID
}





resource "aws_key_pair" "ssrf_server_key_part" {
    key_name = "ssrf-server-key-pair"
    public_key = file("path_to_your_public_key")
  
}


resource "aws_instance" "ssrfserver" {
    ami = data.aws_ami.amazon_linux_2.id
    instance_type = "t2.micro"
    key_name = aws_key_pair.ssrf_server_key_part.id
   
    vpc_security_group_ids = [var.sg_id]
    iam_instance_profile = var.instanceprofile
    user_data = <<EOF
      #!/bin/bash
sudo yum update -y
sudo yum install -y python3 aws-cli coreutils

chown ec2-user:ec2-user /home/ec2-user

aws s3 cp s3://${local.flask_file} /home/ec2-user/script.py

cd /home/ec2-user
python3 -m venv ssrfvenv

/home/ec2-user/ssrfvenv/bin/pip install --upgrade pip
/home/ec2-user/ssrfvenv/bin/pip install flask requests "urllib3<2.0" "requests<2.31"

chmod +x /home/ec2-user/script.py

nohup /home/ec2-user/ssrfvenv/bin/python /home/ec2-user/script.py > /home/ec2-user/script.log 2>&1 &

    EOF

    tags = {
      Name = "ssrf-server"

    }
    associate_public_ip_address = true

}


    







