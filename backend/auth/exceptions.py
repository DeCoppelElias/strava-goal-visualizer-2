from backend.shared.exceptions import StravaAPIError as StravaAPIError


class OAuthStateError(Exception):
    pass


class InsufficientScopeError(Exception):
    pass


class TokenRefreshError(Exception):
    pass
