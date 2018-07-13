from tastypie.authentication import ApiKeyAuthentication
from tastypie.compat import (get_user_model, get_username_field)
from tastypie.http import HttpUnauthorized


class ApiKeyPatch(ApiKeyAuthentication):
    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        try:
            username, api_key = self.extract_credentials(request)
        except ValueError:
            return self._unauthorized()

        if not username or not api_key:
            return self._unauthorized()

        username_field = get_username_field()
        User = get_user_model()

        lookup_kwargs = {username_field: username}
        try:
            user = User.objects.prefetch_related('api_key').get(
                **lookup_kwargs)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        if not self.check_active(user):
            return False

        key_auth_check = self.get_key(user, api_key)
        if key_auth_check and not isinstance(key_auth_check, HttpUnauthorized):
            request.user = user

        return key_auth_check
