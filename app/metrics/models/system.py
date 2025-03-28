from metrics.models import QuestionSuperSet, UserProfile
from django.conf import settings
from django.db.models import Q


class SystemSettings:
    def __init__(self, flags=None, user=None):
        self._flags = flags if flags else {}
        self._user = user

    def get_metrics_sets(self):
        return QuestionSuperSet.objects.filter(use_for_metrics=True).filter(self._get_node_query())
    
    def get_upload_sets(self):
        return QuestionSuperSet.objects.filter(use_for_upload=True).filter(self._get_node_query())
    
    def has_flag(self, flag):
        return flag in self._flags

    def _get_node_query(self):
        return Q(node__isnull=True) | (
            Q()
            if self._user is None
            else Q(node=UserProfile.get_node(self._user))
        )

    @staticmethod
    def get_settings(user=None):
        feature_flags = getattr(settings, "FEATURE_FLAGS", [])
        return SystemSettings(flags=set(feature_flags), user=user)
