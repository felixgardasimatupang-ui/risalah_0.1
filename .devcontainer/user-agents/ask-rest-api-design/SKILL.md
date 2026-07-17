---
name: ask-rest-api-design
description: Teaches RESTful API design principles, resource modeling, HTTP methods, status codes, and API versioning.
---

---
name: ask-rest-api-design
description: RESTful API design principles — resources, HTTP methods, status codes, naming conventions, versioning, and error handling.
triggers: ["design rest api", "api endpoint naming", "restful resource", "http status codes", "api versioning", "rest best practices"]
---

<critical_constraints>
❌ NO verbs in resource names (use /users, NOT /getUsers)
❌ NO returning 200 for errors
❌ NO mixing plural/singular resource names
❌ NO exposing internal DB structure in responses
✅ MUST use plural nouns for collection resources
✅ MUST use standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
✅ MUST use proper HTTP status codes
✅ MUST version APIs (e.g. /api/v1/)
</critical_constraints>

<resource_naming>
- Collections: plural nouns → /users, /orders, /products
- Single resource: /users/{id}
- Nested: /users/{id}/orders/{orderId}
- Actions as sub-resources: /orders/{id}/cancel (POST)
- Query: /users?role=admin&page=1&limit=20
</resource_naming>

<http_methods>
| Method | Purpose       | Status      | Idempotent |
|--------|--------------|-------------|------------|
| GET    | Read          | 200         | ✅         |
| POST   | Create        | 201         | ❌         |
| PUT    | Replace       | 200         | ✅         |
| PATCH  | Partial update| 200         | ❌         |
| DELETE | Remove        | 204         | ✅         |
</http_methods>

<status_codes>
- 200 OK — success
- 201 Created — resource created
- 204 No Content — delete success
- 400 Bad Request — invalid input
- 401 Unauthorized — no/invalid auth
- 403 Forbidden — valid auth, insufficient role
- 404 Not Found
- 409 Conflict — duplicate, state conflict
- 422 Unprocessable Entity — validation error
- 429 Too Many Requests — rate limited
- 500 Internal Server Error
</status_codes>

<error_response_format>
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": [
      { "field": "email", "reason": "required" }
    ]
  }
}
```
</error_response_format>

<pagination>
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 142,
    "totalPages": 8
  }
}
```
</pagination>

<heuristics>
- Nested resources > 2 levels deep → reconsider data model
- Frequent POST for reads → should be GET with query params
- Complex filtering → use query parameters, not body
- Client needs extra data → embedding (include=user.profile)
</heuristics>
