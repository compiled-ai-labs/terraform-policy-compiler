# Two buckets whose addresses share a prefix. `data` has no access block and must
# be denied; `data_backup` is fully protected. A policy that matches a bucket to
# its access block by address prefix instead of exact address would wrongly treat
# `data` as protected (because "aws_s3_bucket.data_backup" starts with
# "aws_s3_bucket.data") and miss the violation.
resource "aws_s3_bucket" "data" {
  bucket = "tpcompile-example-data"
}

resource "aws_s3_bucket" "data_backup" {
  bucket = "tpcompile-example-data-backup"
}

resource "aws_s3_bucket_public_access_block" "data_backup" {
  bucket                  = aws_s3_bucket.data_backup.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
