resource "aws_db_instance" "main" {
  identifier          = "tpcompile-example-db"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  username            = "admin"
  password            = "change-me-please"
  skip_final_snapshot = true
}
