# factory3

Generated factory runtime.

## Run

```bash
uvicorn factory_api:app --host 0.0.0.0 --port $PORT
```

## Structure

- `factory/engine`: runtime loaders and runners
- `factory/skills`: registered skills
- `factory/agents`: registered agents
- `factory/bots`: registered bots
