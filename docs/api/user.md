# API User Specifications

**Version:** 1.0.0

REST API for Vibe Codebase — cover user management.

---

## User :lock:

> All user endpoints require `JWTBearer` except `/{username}` (GET).

### `POST /user/add`

Add a new user.

**Request Body** — `UserDTO`

| Field | Type | Required |
|---|---|---|
| `phone` | string | yes |
| `username` | string | no |
| `fullname` | string | no |
| `password` | string | no |
| `email` | string | no |
| `permissionId` | string | no |
| `groupId` | string | no |
| `about` | string | no |
| `dateOfBirth` | integer | no |
| `gender` | string | no |
| `lastActive` | integer | no |
| `expiredDate` | integer | no |
| `status` | string | no |
| `image` | string | no |
| `multiLogin` | boolean | no |
| `emailVerified` | boolean | no |
| `address` | object | no |
| `tags` | string[] | no |
| `additional` | object | no |
| `createdBy` | string | no |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "fullname": "string",
    "email": "string",
    "phone": "string",
    "permissionId": "string",
    "groupId": "string",
    "status": "string",
    "image": "string",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

> Email and password are censored in the response (original values are not returned).

**Responses**

| Status | Description |
|---|---|
| `200` | User added successfully |
| `400` | Failed to add user |

---

### `PUT /user/update`

Update a user (full update).

**Request Body** — `UpdateUserDTO` (extends `UserDTO` + `id`)

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| *(all UserDTO fields are optional)* | | |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "fullname": "string",
    "email": "string",
    "phone": "string",
    "status": "string",
    "updatedAt": "datetime"
  }
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | User updated successfully |
| `400` | Failed to update |

---

### `DELETE /user/delete`

Delete a user.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `id` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": "{id} has been deleted."
}
```

**Responses**

| Status | Description |
|---|---|
| `200` | User deleted successfully |
| `400` | Failed to delete |

---

### `POST /user/get-all`

List users with pagination & filter.

**Request Body** — `FindUserDTO` (extends `FindDTO`)

| Field | Type | Default |
|---|---|---|
| *(all FindDTO fields)* | | |
| `online` | boolean | `null` |

**Response `200`**

```json
{
  "metaData": {
    "status": true,
    "executionTime": 5,
    "responseCode": 200,
    "message": "Success",
    "pagination": { "size": 10, "totalElements": 100, "totalPages": 10, "scrollId": "" }
  },
  "data": [
    {
      "id": "string",
      "username": "string",
      "fullname": "string",
      "email": "string",
      "phone": "string",
      "status": "string",
      "createdAt": "datetime"
    }
  ]
}
```

---

### `GET /user/get-one`

Get user details by ID (includes group detail).

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `id` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "fullname": "string",
    "email": "string",
    "phone": "string",
    "status": "string",
    "groupDetail": { "id": "string", "name": "string" },
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
}
```

---

### `GET /user/{username}`

Get user details by username.

**Path Parameter:** `username` (string, required)

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "fullname": "string",
    "email": "string",
    "phone": "string",
    "status": "string",
    "createdAt": "datetime"
  }
}
```

---

### `GET /user/check-email`

Check email uniqueness.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `email` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "status": true }
}
```

> `status: true` = email is available (not in use), `false` = already taken.

---

### `GET /user/check-username`

Check username uniqueness.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `username` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "status": true }
}
```

> `status: true` = username is available, `false` = already taken.

---

### `GET /user/check-phone`

Check phone number uniqueness.

**Query Parameters**

| Parameter | Type | Required |
|---|---|---|
| `phone` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": { "status": true }
}
```

> `status: true` = phone is available, `false` = already taken.

---

### `POST /user/reset-password`

Reset a user's password (admin).

**Request Body** — `ResetPasswordDTO`

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `password` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "email": "string",
    "phone": "string",
    "status": "string"
  }
}
```

---

### `POST /user/settings/change-password` :lock:

Change own password.

**Auth:** `JWTBearer` (injects `current_user` via `JWTChangeUserId`)

**Request Body** — `ChangePasswordDTO`

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `oldPassword` | string | yes |
| `newPassword` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": "Password for id {id} has been changed"
}
```

---

### `PUT /user/settings/update-profile` :lock:

Update own profile.

**Auth:** `JWTBearer` (injects `current_user` via `JWTChangeUserId`)

**Request Body** — `UpdateUserDTO`

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| *(other UserDTO fields are optional)* | | |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 5, "responseCode": 200, "message": "Success" },
  "data": {
    "id": "string",
    "username": "string",
    "fullname": "string",
    "email": "string",
    "phone": "string",
    "image": "string",
    "updatedAt": "datetime"
  }
}
```

---

### `POST /user/import`

Import users from a file (CSV/Excel).

**Request:** `multipart/form-data`

| Field | Type | Required |
|---|---|---|
| `file` | file | yes |
| `createdBy` | string | yes |

**Response `200`**

```json
{
  "metaData": { "status": true, "executionTime": 50, "responseCode": 200, "message": "Success" },
  "data": {
    "username1": "success",
    "username2": "error: email already exists"
  }
}
```

> Returns per-user import status (username as key, success/error message as value).

---

## Schema

### User

| Field | Type | Required |
|---|---|---|
| `id` | string | auto |
| `username` | string | no |
| `fullname` | string | no |
| `email` | string | no |
| `phone` | string | yes |
| `password` | string | no |
| `permissionId` | string | no |
| `groupId` | string | no |
| `about` | string | no |
| `dateOfBirth` | integer | no |
| `gender` | string | no |
| `lastActive` | integer | no |
| `expiredDate` | integer | no |
| `status` | string | no |
| `image` | string | no |
| `multiLogin` | boolean | no |
| `emailVerified` | boolean | no |
| `address` | object | no |
| `tags` | string[] | no |
| `additional` | object | no |
| `createdBy` | string | no |
| `createdAt` | datetime | auto |
| `updatedAt` | datetime | auto |

> :lock: = Endpoint requires Bearer Token (JWT)