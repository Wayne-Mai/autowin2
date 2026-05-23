# Strategy Layout

Strategies are grouped by the data stream they consume:

- `paper/`: online paper-run agents that read current market snapshots.
- `replay/`: historical replay baselines that read public trade events.

The paper strategy package also owns target-agent presets:

- `paper/target/`: target-profit strategy family.
- `paper/target/profit.py`: target-profit strategy implementation.
- `paper/target/variants.py`: named target-agent presets and strategy
  factories used by CLI runs and tests.
- `paper/target/sweep.py`: target-agent parameter sweep helpers.
- `paper/baselines.py`: simple online paper baselines such as no-trade and
  random market taker.

Each strategy family exposes a stable package-level import. For example:

```python
from polypaper.strategies.paper import TargetProfitPaperStrategy
from polypaper.strategies.paper import target_variant_configs
from polypaper.strategies.replay import SingleTraderMirrorBaseline
```

Add new strategies in a narrow module under the matching family and export them
from that family's `__init__.py` when they should be available to CLI/tests.
