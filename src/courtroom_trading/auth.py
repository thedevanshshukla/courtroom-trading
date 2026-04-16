from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import Header, HTTPException

from courtroom_trading.contracts import AuthenticatedUser


@dataclass(slots=True)
class AuthConfig:
    google_client_id: str
    jwt_secret: str
    jwt_expiration_minutes: int
    auth_skip_google_verification: bool = False
    auth_mode: str = "demo"
    demo_user_email: str = "demo.trader@example.com"
    demo_user_name: str = "Demo Trader"


class _UrlLibResponse:
    def __init__(self, status: int, data: bytes, headers: dict[str, str]) -> None:
        self.status = status
        self.data = data
        self.headers = headers


class _UrlLibRequest:
    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> _UrlLibResponse:
        request = UrlRequest(url=url, data=body, headers=headers or {}, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
                response_headers = {key: value for key, value in response.headers.items()}
                return _UrlLibResponse(response.status, payload, response_headers)
        except HTTPError as exc:
            payload = exc.read() if hasattr(exc, "read") else b""
            response_headers = {key: value for key, value in getattr(exc, "headers", {}).items()}
            return _UrlLibResponse(exc.code, payload, response_headers)
        except URLError as exc:
            raise exc


class AuthService:
    def __init__(self, config: AuthConfig) -> None:
        self.config = config

    def verify_google_credential(self, credential: str) -> AuthenticatedUser:
        if self.config.auth_skip_google_verification:
            parts = credential.split("|")
            if len(parts) >= 3:
                sub, email, name = parts[:3]
                picture = parts[3] if len(parts) > 3 else ""
                return AuthenticatedUser(
                    user_id=f"google:{sub}",
                    email=email,
                    name=name,
                    picture=picture,
                    google_sub=sub,
                )

        try:
            from google.oauth2 import id_token
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise HTTPException(
                status_code=500,
                detail="Google auth dependencies are missing on the server. Install requirements and restart the backend.",
            ) from exc

        try:
            payload = id_token.verify_oauth2_token(
                credential,
                _UrlLibRequest(),
                self.config.google_client_id,
            )
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=401,
                detail="Invalid Google credential. Ensure frontend and backend GOOGLE_CLIENT_ID match.",
            ) from exc

        issuer = payload.get("iss", "")
        if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
            raise HTTPException(status_code=401, detail="Invalid token issuer.")

        sub = str(payload.get("sub", ""))
        if not sub:
            raise HTTPException(status_code=401, detail="Google account subject missing.")

        return AuthenticatedUser(
            user_id=f"google:{sub}",
            email=str(payload.get("email", "")),
            name=str(payload.get("name", payload.get("email", "Trader"))),
            picture=str(payload.get("picture", "")),
            google_sub=sub,
        )

    def build_demo_user(self) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id="demo:local-user",
            email=self.config.demo_user_email,
            name=self.config.demo_user_name,
        )

    def build_local_user(self, email: str, name: str) -> AuthenticatedUser:
        email_key = email.strip().lower()
        return AuthenticatedUser(
            user_id=f"local:{email_key}",
            email=email_key,
            name=name.strip() or email_key,
            picture="",
            google_sub="",
        )

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        normalized_salt = salt or base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            normalized_salt.encode("utf-8"),
            120000,
        )
        return base64.urlsafe_b64encode(digest).decode("utf-8"), normalized_salt

    def verify_password(self, password: str, expected_hash: str, salt: str) -> bool:
        computed_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, expected_hash)

    def issue_access_token(self, user: AuthenticatedUser) -> dict[str, str]:
        expires_at = datetime.now(UTC) + timedelta(minutes=self.config.jwt_expiration_minutes)
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "google_sub": user.google_sub,
            "exp": expires_at.isoformat().replace("+00:00", "Z"),
        }
        token = self._sign_payload(payload)
        return {
            "access_token": token,
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        }

    def authenticate_bearer_token(self, token: str) -> AuthenticatedUser:
        try:
            payload = self._verify_payload(token)
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=401, detail="Invalid or expired session token.") from exc

        return AuthenticatedUser(
            user_id=str(payload["sub"]),
            email=str(payload.get("email", "")),
            name=str(payload.get("name", "Trader")),
            picture=str(payload.get("picture", "")),
            google_sub=str(payload.get("google_sub", "")),
        )

    def _sign_payload(self, payload: dict[str, str]) -> str:
        serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self.config.jwt_secret.encode("utf-8"),
            serialized,
            hashlib.sha256,
        ).digest()
        return (
            base64.urlsafe_b64encode(serialized).decode("utf-8").rstrip("=")
            + "."
            + base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        )

    def _verify_payload(self, token: str) -> dict[str, str]:
        payload_part, dot, signature_part = token.partition(".")
        if not dot:
            raise ValueError("Malformed token")

        payload_bytes = base64.urlsafe_b64decode(_pad_base64(payload_part))
        signature_bytes = base64.urlsafe_b64decode(_pad_base64(signature_part))
        expected_signature = hmac.new(
            self.config.jwt_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature_bytes, expected_signature):
            raise ValueError("Invalid signature")

        payload = json.loads(payload_bytes.decode("utf-8"))
        expires_at = datetime.fromisoformat(payload["exp"].replace("Z", "+00:00"))
        if datetime.now(UTC) >= expires_at:
            raise ValueError("Expired token")
        return payload


def _pad_base64(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def extract_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing.")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise HTTPException(status_code=401, detail="Bearer token required.")
    return value
