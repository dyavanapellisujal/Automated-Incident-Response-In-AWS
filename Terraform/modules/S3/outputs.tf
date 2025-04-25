output "ssrfflaskserver" {
    value = aws_s3_object.serverfile.key
  
}

output "ssrftestbucket" {
    value = aws_s3_bucket.ssrftestbucket.bucket
  
}