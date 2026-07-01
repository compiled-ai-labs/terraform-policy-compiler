---
type: security-standard
source: Cloud Security Standard, section 2.1 "Object storage exposure"
---

# Object storage must not be publicly reachable

No S3 bucket may be readable or writable by the public. Our default posture is that all object storage is private and reachable only from within our accounts or through an explicit, reviewed access path such as a CloudFront origin access identity.

Public exposure of a bucket has been the single most common cause of data disclosure across the industry, and it almost always happens by accident. A bucket created for a quick test, a policy copied from a tutorial, an access block that was never enabled. Because the failure is silent, we enforce the control at provisioning time rather than relying on anyone to notice later.

Concretely, every bucket must have public access fully blocked. In Terraform this means each `aws_s3_bucket` is accompanied by an `aws_s3_bucket_public_access_block` that sets all four settings to true: block public ACLs, ignore public ACLs, block public policy, and restrict public buckets. A bucket declared without a corresponding, fully enabled public access block is a violation even when no public policy is attached, because the protection is simply absent and a later change could expose the data.

The only sanctioned exception is a bucket explicitly intended to serve public web content. Such a bucket must be tagged for that purpose and reviewed separately, and that exception is out of scope for this control.
