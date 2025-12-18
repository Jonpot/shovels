# BE-2: Google OAuth

## Goal
Implement user authentication via Google.

## Prerequisites
- [BE-1: Server Skeleton](file:///c:/Users/jonat/Desktop/Personal/shovels/Tickets/BE-1-Server-Skeleton.md)

## Description
- Integrate `authlib` or `fastapi-sso` for Google OAuth.
- Define endpoints:
  - `/auth/login`: Redirect to Google.
  - `/auth/callback`: Handle response, create JWT.
- Protect `/rooms` endpoints with JWT middleware.

## Definition of Done
- Successful login flow resulting in a JWT.
- Backend can identify users by their Google email/ID.
