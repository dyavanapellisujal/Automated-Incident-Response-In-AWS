resource "aws_s3_bucket" "ssrftestbucket" {
    bucket = "ssrftestbucket"
    tags = {
      Name = "ssrftestbucket" 
    }
  
}

resource "aws_s3_object" "serverfile" {
    bucket = aws_s3_bucket.ssrftestbucket.id
    key = "ssrfflaskserver.py"
    source = "${path.module}/server.py"
    


  
}
