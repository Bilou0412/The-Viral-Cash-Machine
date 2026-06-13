"""Studio API services — orchestrate the existing pipeline/features brain.

These services reuse the Aventure brain (scripting, assets) WITHOUT rewriting it.
DB-independent helpers (cost estimation, the generation plan) live here so they
can be unit-tested offline with no network and no database.
"""
