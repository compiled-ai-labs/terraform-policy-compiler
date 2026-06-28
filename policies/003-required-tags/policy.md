# Required resource tags

Every taggable resource must carry both an `owner` tag and a `cost-center` tag.
Tags drive ownership routing for incidents and cost allocation; a resource missing
either tag cannot be attributed or charged back reliably. This policy checks EC2
instances as the representative taggable resource.
