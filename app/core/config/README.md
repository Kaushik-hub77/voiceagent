# Configuration Directory

## Overview

This directory contains the **source of truth** for all LLM model configurations in the application.

## Files

### `model_config.yaml` ⭐ **Primary Configuration File**

This is the central configuration file that defines:

- **Default Model**: The fallback model used across the application
- **Pipeline Models**: Which models to use for specific pipelines
- **Pipeline Configs**: LLM parameters (temperature, max_tokens, etc.) for each pipeline
- **Model Definitions**: All available models and their capabilities
- **Provider Settings**: Configuration for LLM providers (OpenAI, Anthropic, etc.)

### `settings.py`

Application settings loaded from environment variables. Contains:

- API keys (sensitive data only)
- Server configuration
- Security settings
- Feature flags

**Note:** Model selection and LLM parameters should **NOT** be in environment variables. Use `model_config.yaml` instead.

## Configuration Philosophy

### ✅ DO: Use `model_config.yaml`

For all non-sensitive configuration:
- Model selection
- Pipeline configurations
- LLM parameters
- Provider settings

### ✅ DO: Use Environment Variables (`.env`)

For sensitive data only:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- Database credentials
- Secret keys

### ❌ DON'T: Mix Configuration Sources

Don't put model selection or LLM parameters in:
- Environment variables
- Hardcoded in code
- Database

## Quick Examples

### Check Current Configuration

```python
from app.core.llm.model_registry import ModelRegistry

registry = ModelRegistry()

# What's the default model?
print(registry.get_default_model())

# What model is used for a pipeline?
print(registry.get_model_for_pipeline("review_summarizer"))

# What are the LLM parameters?
print(registry.get_pipeline_config("review_summarizer"))
```

### Change Default Model

Edit `model_config.yaml`:
```yaml
default_model: "gpt-4-turbo"  # Change this line
```

### Add New Pipeline

Edit `model_config.yaml`:
```yaml
pipeline_models:
  my_new_pipeline:
    primary: "gpt-4"
    fallback: "gpt-3.5-turbo"
    reason: "Why this model?"

pipeline_configs:
  my_new_pipeline:
    temperature: 0.3
    max_tokens: 2000
    top_p: 0.9
```

## Environment-Specific Configs

You can maintain different configs for different environments:

```bash
# Development
MODEL_CONFIG_PATH=app/core/config/model_config.dev.yaml

# Production
MODEL_CONFIG_PATH=app/core/config/model_config.prod.yaml
```

## Documentation

See comprehensive documentation:
- [MODEL_CONFIGURATION_GUIDE.md](../../../docs/MODEL_CONFIGURATION_GUIDE.md) - Full guide
- [QUICK_START_CONFIG.md](../../../docs/QUICK_START_CONFIG.md) - Quick reference
- [MIGRATION_SUMMARY.md](../../../docs/MIGRATION_SUMMARY.md) - What changed and why

## Important Notes

1. **Version Control**: Always commit `model_config.yaml` changes
2. **Documentation**: Add `reason` and `description` fields to explain choices
3. **Testing**: Test configuration changes in dev/staging before production
4. **Validation**: The ModelRegistry validates configuration on startup

## Architecture

```
model_config.yaml (this file)
    ↓
ModelRegistry (loads and validates)
    ↓
LLMOrchestrator (uses for pipelines)
    ↓
Application Code (gets config through registry)
```

## Contact

For questions about configuration management, see the documentation or ask the team.

---

**Remember:** This directory is the **single source of truth** for LLM configuration. Keep it clean, documented, and version-controlled! ✨

