output "ec2-id" {
    value = aws_instance.ssrfserver.id
  
}

output "ec2-publicip" {
    value = aws_instance.ssrfserver.public_ip
  
}