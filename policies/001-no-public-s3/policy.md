# No public S3 buckets

Every `aws_s3_bucket` must have a corresponding `aws_s3_bucket_public_access_block`
with all four flags — `block_public_acls`, `block_public_policy`,
`ignore_public_acls`, and `restrict_public_buckets` — set to `true`. A bucket
without this block can be made public by an ACL or policy, which is the most
common cause of large-scale data exposure.
