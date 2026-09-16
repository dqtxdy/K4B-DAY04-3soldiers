---
name: check_ticket_status
track: bonus
kind: local_status
provider: null
requires_env: []
inputs: [ticket_id]
outputs: [ticket_id, status, priority, updated_at, checked_at]
side_effect: false
requires_confirmation: false
---

# Check ticket status

Reads a fictional local snapshot by ticket ID. It returns only status metadata,
not ticket content, requester identity, credentials, or internal file paths.
