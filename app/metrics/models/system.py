from metrics.models import QuestionSuperSet


class SystemSettings:
    def __init__(self, flags=None):
        self._flags = flags if flags else {}

    def get_current_super_set(self):
        return QuestionSuperSet.objects.get(slug="tmd-core-questions")
    
    def has_flag(self, flag):
        return flag in self._flags

    @staticmethod
    def get_settings():
        return SystemSettings({})