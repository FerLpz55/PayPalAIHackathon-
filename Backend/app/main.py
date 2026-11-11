"""Expose the layered TallerClaro application to Vercel's FastAPI runtime."""

from tallerclaro.main import app

__all__ = ["app"]
