"""Vercel entry point: Vercel serves the FastAPI `app` defined here."""

from recipe_finder.web import app

__all__ = ["app"]
