class OAuthStateError(Exception):
    pass


class InsufficientScopeError(Exception):
    pass


class StravaAPIError(Exception):
    pass


class TokenRefreshError(Exception):
    pass
