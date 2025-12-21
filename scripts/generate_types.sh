#!/bin/bash
  echo "Generating API types"

  # Generate Python types
  datamodel-codegen \
    --input api_types.yaml \
    --output backend/api_types.py \
    --output-model-type pydantic_v2.BaseModel

  # Generate TypeScript types
  npx openapi-typescript api_types.yaml \
    --output client/src/api-types.ts

  echo "Types generated"