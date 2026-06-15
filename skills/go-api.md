---
name: Go REST API（后端）
layer: backend
description: 标准 Go HTTP API 分层：handler / service / repo
---

## Overview

Generate backend API code following clean layering and explicit error handling.

## Backend Code Rules

- Handler: parse request, call service, return JSON
- Service: business logic, no HTTP details
- Repository: data access only
- Use meaningful route paths; document breaking changes in comments
- Add or update tests alongside handlers when the project has them
- Do not modify `tests/generated/` in the spec repo
