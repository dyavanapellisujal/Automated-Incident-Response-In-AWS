resource "aws_security_group" "allow_basic_ports" {
    name = "allow basic ports"
    description = "this will allow port provided by the below list variable "
   

    tags = {
        Name = "main-sg"
    }
}

resource "aws_vpc_security_group_ingress_rule" "allow_ports" {
    security_group_id = aws_security_group.allow_basic_ports.id
    cidr_ipv4 = "0.0.0.0/0"
    for_each = var.ports
    from_port         = tonumber(each.value)
    ip_protocol       = "tcp"
    to_port           = tonumber(each.value)
    
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_basic_ports.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}