# Schemas Directory

## Purpose

This directory contains **Pydantic models** for **request/response validation**, NOT database models.

## What These Schemas Do

- **Request Schemas** (`requests.py`): Validate incoming API request data
  - Ensures phone numbers are in E.164 format
  - Validates time formats (HH:MM)
  - Type checking and validation before processing

- **Response Schemas** (`responses.py`): Structure API response data
  - Ensures consistent response format
  - Type safety for API consumers

## Why Not Database Models?

- **Database models** (if needed) would go in `app/models/` or `app/db/models/`
- These schemas are for **API layer validation** only
- They define the contract between your API and clients

## Example

```python
# Request schema validates incoming data
class InitiateCallRequest(BaseModel):
    mobile_number: str  # Validated as E.164 format
    agent_id: str
    system_prompt: Optional[str]

# Response schema structures outgoing data
class CallInitiatedResponse(BaseModel):
    success: bool
    call_id: Optional[str]
    status: str
```

## Benefits

1. **Type Safety**: FastAPI uses these for automatic validation
2. **Documentation**: Auto-generated OpenAPI docs from schemas
3. **Error Handling**: Invalid data rejected before reaching business logic
4. **IDE Support**: Autocomplete and type hints

