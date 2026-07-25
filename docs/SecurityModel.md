# Security Model

## Core Principles

1. **Local First** - No data leaves the device
2. **Explicit Authorization** - Every target must be whitelisted
3. **Least Privilege** - Users get minimum required permissions
4. **Audit Everything** - All actions are logged
5. **Zero Trust** - Verify at every step

## Authentication Flow

```
Person detected (camera)
  -> Face verification (local embeddings)
  -> Voice verification (speaker recognition)
  -> Permission evaluation
  -> Access granted/denied
```

## User Roles

| Role | Permissions |
|------|------------|
| Owner | Full control: admin, read, write, execute, network, voice, vision, plan, analyze, research, code, document, knowledge_search |
| Approved | Limited: read, voice, knowledge_search |
| Unknown | No access |

## Target Whitelist

Before any system interaction, ELIOT checks:

1. Is the target address in `security/targets.yaml`?
2. Is the target marked as `approved: true`?
3. Was it approved by an authorized user?

If not, ELIOT asks: "Do you want to authorize this target?"

## Permission System

Files:
- `security/users.yaml` - Registered users
- `security/targets.yaml` - Approved targets
- `security/permissions.yaml` - Role-permission mappings
- `security/audit.log` - Action audit trail

## Tool Execution Security

Every tool execution goes through:

1. **Permission Check** - Does the user have the required permission?
2. **Target Whitelist** - If the tool requires a target, is it approved?
3. **Audit Logging** - Action recorded with user, tool, target, result

## Audit Log Format

```yaml
- audit_id: uuid
  timestamp: unix
  user_id: string
  action: string
  target: string
  tool: string
  result: "allowed" | "denied"
  details: {}
```

## Data Encryption

- Face embeddings: stored locally with AES-256
- Voice profiles: encrypted at rest
- Audit logs: append-only, tamper-evident
- Model weights: stored in encrypted volume
