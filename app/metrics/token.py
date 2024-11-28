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
        data = jwt.decode(token, public_key, algorithms=["RS256"])
        username = data["username"]
        tick = data["tick"]
        valid_to = datetime.datetime.fromisoformat(data["valid_to"])
        last_valid_time = (
            datetime.datetime.now() +
            datetime.timedelta(seconds=settings.AUTH_TOKEN_MAX_LIFE_TIME)
        )
        user = User.objects.get(username=username)
        user_tick = user.profile.auth_ticker
        if (
            user.profile.allow_token_reset and
            valid_to <= last_valid_time and
            valid_to > datetime.datetime.now() and
            tick == user_tick
        ):
            return user
    except:
        pass

    raise ValidationError("Token is not valid")


def create_signup_token(user):
    valid_to = (
        datetime.datetime.now() +
        datetime.timedelta(seconds=settings.AUTH_TOKEN_MAX_LIFE_TIME)
    )
    payload = {
        "username": user.username,
        "tick": user.profile.auth_ticker,
        "valid_to": valid_to.isoformat(),
    }

    with open(settings.AUTH_TOKEN_PRIVATE_KEY, "r") as key_file:
        private_key = key_file.read()

    token = jwt.encode(payload, private_key, algorithm="RS256")

    return base64.b64encode(token.encode("utf-8")).decode("utf-8")