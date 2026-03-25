# PetPark Backend API Spec

這份文件對齊目前前端實作，後端照這份開發即可直接接上 App。

目前前端固定使用：

- Base URL: `/api/v1`
- Auth header: `Authorization: Bearer <accessToken>`
- Content type: `application/json`

## 1. Domain Model

核心資料是 `Property`，不是只有餐廳。

支援類型：

- `cafe`
- `restaurant`
- `streetFood`
- `park`
- `hospital`

一個 `Property` 可以同時有多個類型，前端會用 `types[0]` 當主 icon 與主要分類。

## 2. Property JSON Format

### Required response shape

```json
{
  "id": "2f3ed8c2-4d97-4a77-8a6b-2d6abef74123",
  "name": "汪喵咖啡廳",
  "address": "台北市信義區忠孝東路 100 號",
  "latitude": 25.0415,
  "longitude": 121.5650,
  "types": ["cafe"],
  "parkingScore": 5,
  "rating": 4.8,
  "tags": ["寵物友善", "可推車"],
  "ai_summary": "適合帶寵物一起停留的咖啡廳，附近步行環境友善。",
  "isFavorite": false
}
```

### Field rules

- `id`: UUID string
- `name`: string
- `address`: string
- `latitude`: double
- `longitude`: double
- `types`: string array, at least one valid type
- `parkingScore`: integer, `0...5`
- `rating`: double, `0.0...5.0`
- `tags`: string array
- `ai_summary`: string
- `isFavorite`: boolean

`distance` 不需要由 backend 回傳，前端會自己依使用者位置計算。

## 3. APIs

### 3.1 Get Nearby Properties

首頁地圖與底部列表使用。

`GET /api/v1/properties/nearby`

#### Query params

- `lat`: double, optional but strongly recommended
- `lng`: double, optional but strongly recommended
- `radius`: integer, meter, required by current frontend
- `q`: string, optional
- `types`: string, optional, comma-separated

#### Example

`GET /api/v1/properties/nearby?lat=25.0330&lng=121.5654&radius=3000&q=桃園的下午茶&types=cafe,restaurant`

#### Response

```json
{
  "items": [
    {
      "id": "2f3ed8c2-4d97-4a77-8a6b-2d6abef74123",
      "name": "汪喵咖啡廳",
      "address": "台北市信義區忠孝東路 100 號",
      "latitude": 25.0415,
      "longitude": 121.5650,
      "types": ["cafe"],
      "parkingScore": 5,
      "rating": 4.8,
      "tags": ["寵物友善"],
      "ai_summary": "適合帶寵物一起停留的咖啡廳，附近步行環境友善。",
      "isFavorite": false
    }
  ]
}
```

### 3.2 Get Property Detail

詳細頁進入後會再打一次，取得最新內容與收藏狀態。

`GET /api/v1/properties/{propertyId}`

#### Response

```json
{
  "id": "2f3ed8c2-4d97-4a77-8a6b-2d6abef74123",
  "name": "汪喵咖啡廳",
  "address": "台北市信義區忠孝東路 100 號",
  "latitude": 25.0415,
  "longitude": 121.5650,
  "types": ["cafe"],
  "parkingScore": 5,
  "rating": 4.8,
  "tags": ["寵物友善"],
  "ai_summary": "適合帶寵物一起停留的咖啡廳，附近步行環境友善。",
  "isFavorite": true
}
```

### 3.3 Toggle Favorite

前端目前是 optimistic update，先改 UI，再送 API；API 失敗會回滾。

`POST /api/v1/properties/{propertyId}/favorite`

#### Headers

- `Authorization: Bearer <accessToken>`

#### Request

```json
{
  "isFavorite": true
}
```

#### Response

```json
{
  "id": "2f3ed8c2-4d97-4a77-8a6b-2d6abef74123",
  "isFavorite": true
}
```

### 3.4 Apple Sign In

`POST /api/v1/auth/apple`

#### Request

```json
{
  "identityToken": "APPLE_JWT",
  "authorizationCode": "APPLE_AUTH_CODE",
  "userIdentifier": "apple-user-id",
  "givenName": "Ben",
  "familyName": "Liu",
  "email": "user@example.com"
}
```

#### Response

```json
{
  "accessToken": "jwt-or-session-token",
  "refreshToken": "refresh-token",
  "user": {
    "id": "user_123",
    "name": "Ben Liu"
  }
}
```

### 3.5 Get Current User

前端已預留這支 API，用來驗證 token 與還原登入狀態。

`GET /api/v1/me`

#### Headers

- `Authorization: Bearer <accessToken>`

#### Response

```json
{
  "id": "user_123",
  "name": "Ben Liu"
}
```

## 4. Search Behavior Backend Must Support

前端搜尋框目前直接把整段文字當 `q` 傳給 nearby API。

例如：

- `幫我找附近的餐廳`
- `桃園的下午茶`
- `青埔的公園`
- `台北的醫院`

所以 backend 至少要能支援：

- 一般 keyword search
- 地區文字
- 類型文字或類型對應

如果後端暫時還沒做 NLP，最少也要讓 `q` 能做模糊搜尋與類型篩選。

## 5. Frontend Integration Notes

前端目前實作方式如下：

- `PropertyRepository`
  - `GET /properties/nearby`
  - `GET /properties/{id}`
  - `POST /properties/{id}/favorite`
- `AuthRepository`
  - `POST /auth/apple`
  - `GET /me`
- 未登入時，如果沒有 token：
  - nearby / detail 可不帶 `Authorization`
  - favorite / me 應回傳 401

## 6. Error Format

建議統一：

```json
{
  "error": {
    "code": "PROPERTY_NOT_FOUND",
    "message": "Property not found"
  }
}
```

建議至少包含：

- `UNAUTHORIZED`
- `PROPERTY_NOT_FOUND`
- `VALIDATION_ERROR`
- `INTERNAL_SERVER_ERROR`

## 7. Not Needed From Backend Yet

目前這些仍由前端本機或 MapKit 處理：

- 最近停車場搜尋
- 街景 Look Around
- Apple Maps / Google Maps 導航跳轉
- 距離計算
