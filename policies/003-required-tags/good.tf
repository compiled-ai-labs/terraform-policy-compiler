resource "aws_instance" "app" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"

  tags = {
    Name          = "tpcompile-example-app"
    owner         = "platform-team"
    "cost-center" = "cc-1234"
  }
}
