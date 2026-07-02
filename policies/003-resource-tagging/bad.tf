# A taggable resource declared with no tags at all. It violates the standard
# (both required tags absent), but a policy that only inspects resources whose
# planned `tags` is non-null skips it entirely and misses the violation.
resource "aws_instance" "app" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"
}
