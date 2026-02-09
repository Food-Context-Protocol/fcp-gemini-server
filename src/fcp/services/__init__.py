"""FCP Services - Infrastructure wrappers."""

from .firestore import firestore_client, get_firestore_client
from .gemini import gemini
from .maps import search_nearby_restaurants

__all__ = [
    "firestore_client",
    "get_firestore_client",
    "gemini",
    "search_nearby_restaurants",
]
