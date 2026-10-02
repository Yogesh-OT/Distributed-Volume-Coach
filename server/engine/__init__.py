"""Training logic for Distributed Volume Coach.

Everything in this package is a pure function of its inputs: no database, no web
framework and no clock. Callers pass in "today" and local times explicitly, which
keeps every rule unit-testable and lets the phone port (Kotlin) be checked against
the same test vectors.
"""

ENGINE_VERSION = "0.1.0"
