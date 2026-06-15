---
name: Clean UI（前端）
layer: frontend
description: TypeUI 简洁风格，适用于 React / Vue 前端页面
---

## Overview

Simplicity-focused design with ample whitespace, legible typography, and a limited color palette to reduce visual clutter.

## Style Foundations

- **Visual style:** minimal, clean
- **Typography scale:** 12/14/16/20/24/32
- **Spacing:** 8pt baseline grid
- **Components:** use `data-testid` on interactive elements for E2E

## Frontend Code Rules

- Prefer functional components and hooks
- Keep components small; extract shared UI to `components/`
- Match existing project lint/format conventions
- Do not modify `tests/generated/` in the spec repo
