# RDS storage encryption required

All RDS database instances must have storage encryption enabled
(`storage_encrypted = true`). Unencrypted database storage leaves data at rest
readable to anyone who gains access to the underlying volume or a snapshot of it,
which most compliance regimes treat as a reportable exposure.
