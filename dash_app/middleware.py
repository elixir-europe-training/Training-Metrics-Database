


class Group():
    def __init__(self, fields):
        self.fields = fields

    def get_fields(self):
        return list(self.fields.keys())
    
    def get_filter_fields(self):
        return self.get_fields()
    
    def get_field_placeholder(self, field_id):
        return field_id
    
    def get_field_options(self,field_id):
        return self.fields[field_id]
    
    def get_field_title(self,field_id):
        return field_id
    
    def get_values(self, **params):
        return []


class Metrics():
    def __init__(self, groups):
        self.groups = groups

    def get_group(self, name):
        return self.groups[name]


current_metric = Metrics(
    {
        "impact": Group(
            {
                "event_type": ["A", "B", "C"], 
                "funding": ["A", "B", "C"], 
                "target_audience": ["A", "B", "C"]
            }
        )
    }
)

def metrics_middleware(get_response):
    def middleware(request):
        setattr(request, "metrics", current_metric)
        response = get_response(request)
        return response

    return middleware