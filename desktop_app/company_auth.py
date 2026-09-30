"""Company-owned AD boundary. Replace these functions after internal review.

No LDAP dependency, endpoint, password, or permissive fallback is supplied here.
The implementation must use a bounded timeout and verified TLS, check the unit
allowlist, and return the documented identity contract (never credentials).
"""


def is_configured():
    return False


def authenticate(employee_id, password):
    raise RuntimeError('AD_NOT_CONFIGURED')
