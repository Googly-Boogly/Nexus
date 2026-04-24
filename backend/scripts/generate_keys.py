#!/usr/bin/env python3
"""Generate a secure SECRET_KEY for .env"""
import secrets
print(secrets.token_urlsafe(48))
