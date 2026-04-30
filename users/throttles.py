from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Throttle for /auth/login/ — slows password-spray and credential-stuffing.

    Keyed by IP, so a single attacker cannot try more than `login` rate-limit
    POSTs per minute. Pairs with allauth's own rate limit on the HTML signup/login
    flows.
    """
    scope = 'login'
