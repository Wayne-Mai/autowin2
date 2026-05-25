# Online 6 Hour Paper Result

This repository snapshot excludes local SQLite databases and logs. The accepted online paper run evidence was produced locally with live public Polymarket data and local virtual execution only.

Final verifier line:

```text
PASS run_id=polymarket-online-6h-20260524T160400Z mode=online_target runtime=21652s required_runtime=21600s passed_strategies=72/272 required_strategies=2 passed_families=2/2 target_roi=10.0000% flat_required=True reason=online_goal_reached
```

Acceptance criteria:

- online target mode
- runtime at least 21600 seconds
- target ROI at least 10 percent
- final flat state required
- at least two passing strategies
- at least two passing strategy families

Important local artifact, not committed:

```text
data/polymarket_online_6h_20260524T160400Z.sqlite
```

To reproduce a fresh online paper run:

```bash
scripts/launch_online_goal_6h.sh
scripts/online_goal_status.sh --top 20
scripts/verify_online_goal.sh
```
