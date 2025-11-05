from copy import deepcopy

from flask import Flask, jsonify, request

app = Flask(__name__)


def _set_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response

app = Flask(__name__)


QUESTION_SETS = {
    "quality": [
        {
            "id": "quality-used_resources_before",
            "label": "Have you used the tool(s)/resource(s) covered in the course before?",
            "options": [
                {"label": "Occasionally (once in a while to monthly)", "id": "occasionally", "count": 5230},
                {"label": "Never - aware of them, but not used them", "id": "never-aware", "count": 2977},
                {"label": "Never - unaware of them", "id": "never-unaware", "count": 2875},
                {"label": "-", "id": "no-response", "count": 2661},
                {"label": "Never - used other services", "id": "never-other", "count": 1319},
                {"label": "Frequently (weekly to daily)", "id": "frequently", "count": 1248},
            ],
        },
        {
            "id": "quality-course_rating",
            "label": "Please tell us your overall rating for the entire course",
            "options": [
                {"label": "Very Good (4)", "id": "very-good-4", "count": 5771},
                {"label": "Excellent (5)", "id": "excellent-5", "count": 5410},
                {"label": "Good (3)", "id": "good-3", "count": 2804},
                {"label": "-", "id": "no-response", "count": 1424},
                {"label": "Satisfactory (2)", "id": "satisfactory-2", "count": 753},
                {"label": "Poor (1)", "id": "poor-1", "count": 148},
            ],
        },
    ],
    "impact": [
        {
            "id": "impact-followup_applied",
            "label": "Have you applied the knowledge from the training to your work?",
            "options": [
                {"label": "Yes", "id": "yes", "count": 312},
                {"label": "Partially", "id": "partially", "count": 198},
                {"label": "Not yet", "id": "not-yet", "count": 102},
                {"label": "No", "id": "no", "count": 55},
            ],
        },
        {
            "id": "impact-followup_shared",
            "label": "Have you shared the tools or resources covered in the course?",
            "options": [
                {"label": "Yes", "id": "yes", "count": 276},
                {"label": "Planning to", "id": "planning", "count": 184},
                {"label": "No", "id": "no", "count": 116},
            ],
        },
    ],
}


def _scaled_question(question, scale):
    question_copy = deepcopy(question)
    if scale != 1:
        for option in question_copy["options"]:
            option["count"] = max(0, int(option["count"] * scale))
    return question_copy


@app.route("/metrics", methods=["GET", "OPTIONS"])
def metrics():
    """
    Mock endpoint that mirrors the public TMD metrics API.
    Supports the following query parameters:
      - question_sets: comma separated list of question set slugs
      - questions: comma separated list of question slugs (ignored if question_sets is provided)
      - data_scope: either 'all' (default) or 'node' to simulate node-specific data
    """
    requested_question_sets = request.args.get("question_sets")
    requested_questions = request.args.get("questions")
    data_scope = request.args.get("data_scope", "all")

    if requested_question_sets:
        set_slugs = [
            slug.strip()
            for slug in requested_question_sets.split(",")
            if slug.strip()
        ]
    else:
        set_slugs = list(QUESTION_SETS.keys())

    question_filter = None
    if not requested_question_sets and requested_questions:
        question_filter = {
            slug.strip()
            for slug in requested_questions.split(",")
            if slug.strip()
        }

    scale = 0.5 if data_scope == "node" else 1

    values = []
    for set_slug in set_slugs:
        for question in QUESTION_SETS.get(set_slug, []):
            if question_filter and question["id"] not in question_filter:
                continue
            values.append(_scaled_question(question, scale))

    if not values:
        values = [
            {
                "id": "no-data",
                "label": "No metrics available for the requested configuration.",
                "options": [{"label": "-", "id": "empty", "count": 0}],
            }
        ]

    return _set_cors_headers(jsonify({"values": values}))


if __name__ == "__main__":
    app.run(port=8001, debug=True)
