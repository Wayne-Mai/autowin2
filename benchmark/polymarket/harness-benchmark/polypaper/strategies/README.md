# Strategy Layout

Strategies are grouped by the data stream they consume:

- `paper/`: online paper-run agents that read current market snapshots.
- `replay/`: historical replay strategies that read public trade events.

The online paper strategy package is split by strategy family:

- `paper/baseline/`: simple online controls such as no-trade and random
  market taker.
- `paper/suites.py`: default online paper benchmark agent suite assembly.
- `paper/target/`: target-profit strategy family.
- `paper/target/profit.py`: target-profit strategy implementation.
- `paper/target/crypto.py`: online crypto up/down directional strategy using
  public spot momentum plus Polymarket books.
- `paper/target/variants.py`: named target-agent presets and strategy
  factories used by CLI runs and tests.
- `paper/target/sweep.py`: target-agent parameter sweep helpers.
- `paper/baselines.py`, `paper/target_profit.py`,
  `paper/target_variants.py`, and `paper/target_sweep.py`: compatibility
  imports for older scripts.
- `replay/baseline/`: historical replay controls that consume public trade
  events.
- `replay/suites.py`: default replay benchmark strategy suite assembly.
- `replay/baselines.py`: compatibility import for older replay scripts.

Each strategy family exposes a stable package-level import. For example:

```python
from polypaper.strategies.paper import TargetProfitPaperStrategy
from polypaper.strategies.paper import target_variant_configs
from polypaper.strategies.replay import SingleTraderMirrorBaseline
```

Add new strategies in a narrow module under the matching family and export them
from that family's `__init__.py` when they should be available to CLI/tests.
