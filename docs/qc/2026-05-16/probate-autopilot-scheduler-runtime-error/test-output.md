# Test Output

## Focused adapter contracts

Command:

```bash
uv run pytest tests/services/test_probate_live_source_adapter_service.py -q
```

Result:

```text
.........                                                                [100%]
9 passed in 0.05s
```

## Full backend

Command:

```bash
uv run pytest -q
```

Result:

```text
948 passed in 20.43s
```

## Trigger typecheck

Command:

```bash
npm --prefix trigger run typecheck
```

Result:

```text
> typecheck
> tsc --noEmit -p tsconfig.json
```

## Whitespace

Command:

```bash
git diff --check
```

Result: passed with no output.
