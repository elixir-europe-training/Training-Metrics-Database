import jwt
import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from metrics.models import User
import base64


def validate_token(token):
    try:
        with open(settings.AUTH_TOKEN_PUBLIC_KEY, "r") as key_file:
            public_key = key_file.read()

        token = base64.b64decode(token.encode("utf-8")).decode("utf-8")
        data = jwt.decode(token, public_key, options={"require": ["exp"]}, algorithms=["RS256"])
        username = data["username"]
        tick = data["tick"]
        user = User.objects.get(username=username)
        user_tick = user.profile.auth_ticker
        if (
            user.profile.allow_token_reset and
            tick == user_tick
        ):
            return user
    except:
        pass

    raise ValidationError("Token is not valid")


def get_content(token):
    token = base64.b64decode(token.encode("utf-8")).decode("utf-8")
    return jwt.decode(token, options={"verify_signature": False})


def create_signup_token(user):
    valid_to = (
        datetime.datetime.now(tz=datetime.timezone.utc) +
        datetime.timedelta(seconds=settings.AUTH_TOKEN_MAX_LIFE_TIME)
    )
    payload = {
        "username": user.username,
        "tick": user.profile.auth_ticker,
        "exp": valid_to,
    }

    with open(settings.AUTH_TOKEN_PRIVATE_KEY, "r") as key_file:
        private_key = key_file.read()

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256"
    )

    return base64.b64encode(token.encode("utf-8")).decode("utf-8")