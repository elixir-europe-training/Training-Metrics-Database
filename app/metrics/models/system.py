from metrics.models import QuestionSuperSet


class SystemSettings:
    def __init__(self, flags=None):
        self._flags = flags if flags else {}

    def get_metrics_sets(self):
        return QuestionSuperSet.objects.filter(use_for_metrics=True).all()
    
    def get_upload_sets(self):
        return QuestionSuperSet.objects.filter(user_for_upload=True).all()
    
    def has_flag(self, flag):
        return flag in self._flags

    @staticmethod
    def get_settings():
        return SystemSettings({
            #"use_new_model_upload",
            #"use_new_model_stats",
        })