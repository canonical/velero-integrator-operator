# Velero Integrator Operator

Integrator charm for managing scheduled backups with Velero on Kubernetes.

## Overview

The Velero Integrator Charm acts as middleware between target applications and the Velero Operator, enabling scheduled backup management. It receives backup specifications from target applications via the `k8s-backup-target` relation and forwards them to Velero Operator via the `velero-backup` relation, adding schedule configuration.

This charm simplifies backup orchestration by separating "what to backup" (defined by target apps) from "when to backup" (defined by operators).

## Usage

### Deploy

```bash
juju deploy velero-integrator
```

### Configure

Set a backup schedule using cron expression:

```bash
# Daily backup at 2 AM
juju config velero-integrator schedule="0 2 * * *"

# Weekly backup on Sundays at midnight
juju config velero-integrator schedule="0 0 * * 0"
```

Pause/resume scheduled backups:

```bash
juju config velero-integrator paused=true
juju config velero-integrator paused=false
```

### Relate

Connect to Velero Operator and target applications:

```bash
# Connect to Velero Operator
juju integrate velero-integrator velero-operator

# Connect to applications that need backup
juju integrate velero-integrator:k8s-backup-target my-database
```

## Relations

| Relation | Interface | Description |
|----------|-----------|-------------|
| `velero-backup` | `velero_backup_config` | Provides backup specs to Velero Operator |
| `k8s-backup-target` | `k8s_backup_target` | Receives backup specs from target applications |
| `status-peers` | `velero_integrator_peers` | Peer relation for status management |

## Resources

- [Charmhub](https://charmhub.io/velero-integrator)
- [Contributing](CONTRIBUTING.md)
- [Juju Documentation](https://documentation.ubuntu.com/juju/)
