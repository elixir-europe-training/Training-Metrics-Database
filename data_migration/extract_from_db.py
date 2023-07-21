#!/usr/bin/env python
import csv
import json
import sys
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, Self, Type, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    PlainSerializer,
    ValidationError,
    validate_call,
)
from sqlalchemy import TextClause, create_engine
from sqlalchemy.sql import text

T = TypeVar("T")


@validate_call
def validate_non_null_list(v: list[T]) -> list[T]:
    if v == [None]:
        return []
    return [x for x in v if x != "NA"]


def json_unarray(array_like: str) -> list[Any]:
    loaded = json.loads(array_like)
    return validate_non_null_list(loaded)


def json_unarray_v(v: Any):
    if isinstance(v, str):
        try:
            return json_unarray(v)
        except ValidationError:
            raise
        except Exception:
            raise ValidationError()
    elif isinstance(v, (list, tuple)):
        return validate_non_null_list(v)  # type: ignore
    else:
        return v


WithUnarray = Annotated[T, BeforeValidator(json_unarray_v)]


def nullable_to_array_v(v: Any):
    if v is None:
        return []
    if not isinstance(v, (list, tuple)):
        return [v]
    return v


WithNullableToArray = Annotated[T, BeforeValidator(nullable_to_array_v)]
ForgivingDate = Annotated[
    date,
    BeforeValidator(lambda v: v.date() if isinstance(v, datetime) else v),
]


def defaulting_validator(default: Any):
    def validator(v: Any):
        if v is None:
            return default
        return v

    return BeforeValidator(validator)


def remapping_validator(value_map: dict) -> BeforeValidator:
    def validator(v: Any):
        if v in value_map:
            return value_map[v]
        return v

    return BeforeValidator(validator)


TaxonomyEventType = Annotated[
    Literal[
        "Training - face to face",
        "Training - elearning",
        "Training - blended",
        "Knowledge Exchange Workshop",
        "Hackathon",
    ],
    remapping_validator({"Knowledge exchange workshop": "Knowledge Exchange Workshop"}),
]
TaxonomyFunding = Annotated[
    Literal[
        "Converge",
        "ELIXIR Converge",
        "EOSC Life",
        "EXCELLERATE",
        "ELIXIR Implementation Study",
        "ELIXIR Community / Use case",
        "ELIXIR Node",
        "ELIXIR Hub",
        "ELIXIR Platform",
        "Non-ELIXIR / Non-EXCELLERATE Funds",
    ],
    remapping_validator(
        {
            "CONVERGE": "Converge",
            "EOSC-Life": "EOSC Life",
            "EXCELERATE": "EXCELLERATE",
            "ELIXIR Community/ Use Case": "ELIXIR Community / Use case",
            "Non-ELIXIR/ Non-EXCELERATE funds": "Non-ELIXIR / Non-EXCELLERATE Funds",
        }
    ),
]
TaxonomyTargetAudience = Annotated[
    Literal[
        "Academia / Research Institution",
        "Industry",
        "Non-profit Organisation",
        "Healthcare",
    ],
    remapping_validator(
        {
            "Academia/ Research Institution": "Academia / Research Institution",
            "Non-Profit Organisation": "Non-profit Organisation",
        }
    ),
]
TaxonomyAdditionalPlatforms = Literal[
    "Compute",
    "Data",
    "Interoperability",
    "Tools",
]
TaxonomyCommunities = Literal[
    "Human Data",
    "Marine Metagenomics",
    "Rare Diseases",
    "Plant Sciences",
    "Proteomics",
    "Metabolomics",
    "Galaxy",
]
TaxonomyHeardFrom = Literal[
    "TeSS",
    "Host Institute Website",
    "Email",
    "Newsletter",
    "Colleague",
    "Internet search",
    "Other",
]
TaxonomyEmploymentSector = Literal[
    "Academia/ Research Institution",
    "Industry",
    "Non-Profit Organisation",
    "Healthcare",
    "Other",
]
TaxonomyGender = Literal[
    "Male",
    "Female",
    "Prefer not to say",
    "Other",
]
TaxonomyCareerStage = Literal[
    "Undergraduate student",
    "Masters student",
    "PhD candidate",
    "Postdoctoral researcher",
    "Senior scientist/ Principal investigator",
    "Research assistant/ Technician",
    "Other",
]
TaxonomyUsedResourcesBefore = Literal[
    "Frequently (weekly to daily)",
    "Occasionally (once in a while to monthly)",
    "Never - used other service",
    "Never - aware of them, but not used them",
    "Never - unaware of them",
]
TaxonomyYesNo = Literal["Yes", "No"]
TaxonomyYesNoMaybe = Literal["Yes", "No", "Maybe"]
TaxonomyCourseRating = Literal[
    "Excellent (5)",
    "Very Good (4)",
    "Good (3)",
    "Satisfactory (2)",
    "Poor (1)",
]
TaxonomyMaterialBalance = Literal[
    "About right",
    "Too theoretical",
    "Too practical",
]
TaxonomyWhenAttendTraining = Literal[
    "Less than 6 months",
    "6 months to a year",
    "Over a year",
]
TaxonomyAttendReason = Literal[
    "To learn something new to aid me in my current research/ work",
    "To learn something new for my own interests",
    "To build on existing knowledge to aid me in my current research/ work",
    "To build on existing knowledge for my own interests",
    "Other",
]
TaxonomHowOftenUseBefore = Literal[
    "Never - unaware of them",
    "Never - aware of them, but had not used them",
    "Never - used other service",
    "Occasionally (once in a while to monthly)",
    "Frequently (weekly to daily)",
]
TaxonomyHowOftenUseAfter = Literal[
    "Never - use other service",
    "Occasionally (once in a while to monthly)",
    "Frequently (weekly to daily)",
]
TaxonomyYesNoMaybeOther = Literal["Yes", "No", "Maybe", "Other"]
TaxonomyAbleUseNow = Literal[
    "Independently",
    "By using training materials/ notes from the training event",
    "With the help of an expert",
    "Other",
]
TaxonomyHelpWork = Literal[
    "It did not help as I do not use the tool(s)/ resource(s) covered in the training event",
    "It enabled me to complete certain tasks more quickly",
    "It has not helped yet but I anticipate a future impact",
    "It improved communication with the bioinformatician/ statistician analyzing my data",
    "It improved my ability to handle data",
    "Other",
]
TaxonomyAttendingLedTo = Literal[
    "Authoring of software",
    "Change in career",
    "Not applicable",
    "Other",
    "Publication of my work",
    "Submission of a grant application",
    "Submission of my dissertation/ thesis for degree purposes",
    "Useful collaboration(s) with other participants/ trainers from the training event",
]
TaxonomyPeopleShareKnowledge = Literal[
    "None",
    "None yet, but intend to do so in the future",
    "1-5",
    "6-15",
    "16-24",
    "25+",
]
TaxonomyRecommendOthers = Literal[
    "Yes, I already have",
    "Yes, I would",
    "Maybe",
    "No",
]

PositiveIntOrNone = Annotated[
    int | None, BeforeValidator(lambda v: None if v is None or v < 1 else v)
]


def dict_to_csv(obj, fields):
    ret = []
    for k in fields:
        v = obj[k]
        if v is None:
            v = ""
        elif isinstance(v, (list, tuple)):
            v = ",".join(str(x) for x in v)
        else:
            v = str(v)
        ret.append(v)
    return ret


def dict_to_json(obj, fields):
    ret = {}
    for k in fields:
        v = obj[k]
        if isinstance(v, list):
            pass
        elif isinstance(v, tuple):
            v = list(v)
        elif v is not None:
            v = str(v)
        ret[k] = v
    return ret


def query_raw_json(results: Any, keys: tuple[str, ...]) -> str:
    out = []
    for row in results:
        out_row = {k: getattr(row, k) for k in keys}
        out.append(dict_to_json(out_row, keys))
    return json.dumps(out, indent="    ")


def query_to_csv(results: Any, model: Type[BaseModel]) -> str:
    model_c: Any = model
    fields = list(model.model_fields.keys())
    with StringIO() as sio:
        csv_w = csv.writer(sio)
        csv_w.writerow(fields)
        for row in results:
            inst = model_c.from_query(row)
            inst_d = inst.model_dump(mode="json")
            inst_l = dict_to_csv(inst_d, fields)
            csv_w.writerow(inst_l)
        return sio.getvalue()


def query_to_json(results: Any, model: Type[BaseModel]) -> str:
    model_c: Any = model
    fields = list(model.model_fields.keys())
    out = []
    for row in results:
        inst = model_c.from_query(row)
        inst_d = inst.model_dump(mode="json")
        out.append(dict_to_json(inst_d, fields))
    return json.dumps(out, indent="    ")


class ModelEvent(BaseModel):
    id_event: int
    user: int
    created: datetime
    modified: datetime
    title: str
    node: WithUnarray[list[str]]
    node_main: str
    date_start: ForgivingDate
    date_end: ForgivingDate
    duration: Annotated[
        Decimal,
        PlainSerializer(lambda x: f"{x:.2f}", return_type=str, when_used="json"),
    ]
    type: TaxonomyEventType
    funding: WithUnarray[list[TaxonomyFunding]]
    organising_institution: WithNullableToArray[list[str]]
    location_city: str
    location_country: str
    target_audience: WithUnarray[list[TaxonomyTargetAudience]]
    additional_platforms: WithUnarray[list[TaxonomyAdditionalPlatforms]]
    communities: WithUnarray[list[TaxonomyCommunities]]
    number_participants: PositiveIntOrNone
    number_trainers: PositiveIntOrNone
    url: str
    status: Literal["Complete", "Incomplete"]

    @classmethod
    def from_query(cls, v: Any) -> Self:
        nodes = json_unarray(v.f_elixir_node)
        nodes_user = json_unarray(v.f_elixir_node_user)

        if len(nodes) == 1:
            node_main = nodes[0]
        elif len(nodes_user) == 1:
            node_main = nodes_user[0]
        else:
            s_nodes = {*nodes}
            s_nodes_user = {*nodes_user}
            nodes_intersect = s_nodes & s_nodes_user
            if len(nodes_intersect) > 1:
                node_main = next(iter(nodes_intersect))
            else:
                node_main = next(iter(s_nodes | s_nodes_user))

        return cls(
            id_event=v.entity_id,
            user=v.f_created_by,
            created=v.f_created,
            modified=v.f_changed,
            title=v.f_title,
            node=nodes,
            node_main=node_main,
            date_start=v.f_date_start,
            date_end=v.f_date_end,
            duration=v.f_duration,
            type=v.f_event_type,
            funding=v.f_funding,
            organising_institution=v.f_organizing_institution,
            location_city=v.f_city,
            location_country=v.f_country,
            target_audience=v.f_target_audience,
            additional_platforms=v.f_elixir_service_platforms_r,
            communities=v.f_communities_use_cases_rela,
            number_participants=v.f_delegates,
            number_trainers=v.f_number_of_trainers_facilit,
            url=v.f_url_to_event_page_agenda,
            status=v.f_upload_status,
        )


class ModelDemographic(BaseModel):
    id_demographic: int
    user: int
    created: datetime
    modified: datetime
    event: int | None
    heard_from: TaxonomyHeardFrom | None
    employment_sector: TaxonomyEmploymentSector | None
    employment_country: str | None
    gender: TaxonomyGender | None
    career_stage: TaxonomyCareerStage | None

    @classmethod
    def from_query(cls, v: Any) -> Self:
        return cls(
            id_demographic=v.entity_id,
            user=v.f_created_by,
            created=v.f_created,
            modified=v.f_changed,
            event=v.f_event,
            heard_from=v.f_where_you_hear_about_cours,
            employment_sector=v.f_employment_sector,
            employment_country=v.f_country,
            gender=v.f_gender,
            career_stage=v.f_career_stage,
        )


class ModelQuality(BaseModel):
    id_quality: int
    user: int
    created: datetime
    modified: datetime
    event: int
    used_resources_before: TaxonomyUsedResourcesBefore | None
    used_resources_future: TaxonomyYesNoMaybe | None
    recommended_course: TaxonomyYesNoMaybe | None
    course_rating: TaxonomyCourseRating | None
    balance: TaxonomyMaterialBalance | None
    email_contact: Annotated[TaxonomyYesNo, defaulting_validator("No")]

    @classmethod
    def from_query(cls, v: Any) -> Self:
        return cls(
            id_quality=v.entity_id,
            user=v.f_created_by,
            created=v.f_created,
            modified=v.f_changed,
            event=v.f_event,
            used_resources_before=v.f_have_you_used_the_tools,
            used_resources_future=v.f_will_you_use_the_resources,
            recommended_course=v.f_would_you_recommend,
            course_rating=v.f_overall_rating,
            balance=v.f_balance_of_the_material,
            email_contact=v.f_may_we_contact_you_email,
        )


class ModelImpact(BaseModel):
    id_impact: int
    user: int
    created: datetime
    modified: datetime
    event: int
    when_attend_training: TaxonomyWhenAttendTraining | None
    main_attend_reason: TaxonomyAttendReason | None
    how_often_use_before: TaxonomHowOftenUseBefore | None
    how_often_use_after: TaxonomyHowOftenUseAfter | None
    able_to_explain: TaxonomyYesNoMaybeOther | None
    able_use_now: TaxonomyAbleUseNow | None
    help_work: WithUnarray[list[TaxonomyHelpWork]]
    attending_led_to: WithUnarray[list[TaxonomyAttendingLedTo]]
    people_share_knowledge: TaxonomyPeopleShareKnowledge | None
    recommend_others: TaxonomyRecommendOthers | None

    @classmethod
    def from_query(cls, v: Any) -> Self:
        return ModelImpact(
            id_impact=v.entity_id,
            user=v.f_created_by,
            created=v.f_created,
            modified=v.f_changed,
            event=v.f_event,
            when_attend_training=v.f_how_long_ago,
            main_attend_reason=v.f_what_was_your_main_reason,
            how_often_use_before=v.f_how_often_did_you_use_tool,
            how_often_use_after=v.f_how_often_do_you_use_after,
            able_to_explain=v.f_do_you_feel_explain,
            able_use_now=v.f_are_you_now_able,
            help_work=v.f_how_did_it_help,
            attending_led_to=v.f_facilitated,
            people_share_knowledge=v.f_how_many_people_you_shared,
            recommend_others=v.f_would_you_recommend,
        )


def load_sql_file(filename: str) -> TextClause:
    with open(filename, "r") as f:
        lines = "\n".join(f.readlines())
        return text(lines)


def write_output_file(filename: str, get_content: Callable[[], str]):
    path_out = Path("out")
    path_out.mkdir(exist_ok=True)
    path = path_out / filename
    if path.exists():
        return
    print(f"Generating {filename}...")
    try:
        content = get_content()
    except Exception as e:
        print(f"Error while generating {filename}")
        print(traceback.format_exc())
        return
    with open(path, "w") as f:
        f.write(content)


def declare_output(
    filename: str,
    get_results: Callable[[], Any],
    model: Type[BaseModel] | None,
    *,
    enable_csv: bool,
    enable_json: bool,
    enable_json_raw: bool,
):
    @dataclass
    class CachedValue:
        results: list[Any]
        keys: tuple[str, ...]

    cache: CachedValue | None = None

    def cached_getter() -> CachedValue:
        nonlocal cache
        if cache is None:
            results = get_results()
            keys = results.keys()
            cache = CachedValue(results=list(results), keys=keys)
        return cache

    if enable_json_raw:
        write_output_file(
            f"{filename}.raw.json",
            lambda: query_raw_json(cached_getter().results, cached_getter().keys),
        )
    if enable_json and model is not None:
        write_output_file(
            f"{filename}.json",
            lambda: query_to_json(cached_getter().results, model),
        )
    if enable_csv and model is not None:
        write_output_file(
            f"{filename}.csv",
            lambda: query_to_csv(cached_getter().results, model),
        )


def main():
    if len(sys.argv) < 2:
        print(
            f"Usage: {sys.argv[0]} <connection_string>"
            f"Example: {sys.argv[0]} 'mysql+pymysql://user:pass@localhost/tmd?charset=utf8mb4'"
        )
        exit(1)
    engine = create_engine(sys.argv[1])
    output_types = {"enable_csv": True, "enable_json": True, "enable_json_raw": True}

    q_get_events = load_sql_file("queries/get_events.sql")
    q_get_demographics = load_sql_file("queries/get_demographics.sql")
    q_get_feedback = load_sql_file("queries/get_feedback.sql")
    q_get_impact = load_sql_file("queries/get_impact.sql")
    q_get_institutes = load_sql_file("queries/get_institutes.sql")
    q_get_users = load_sql_file("queries/get_users.sql")

    with engine.connect() as conn:
        declare_output(
            "event",
            lambda: conn.execute(q_get_events),
            ModelEvent,
            **output_types,
        )
        declare_output(
            "demographic",
            lambda: conn.execute(q_get_demographics),
            ModelDemographic,
            **output_types,
        )
        declare_output(
            "quality",
            lambda: conn.execute(q_get_feedback),
            ModelQuality,
            **output_types,
        )
        declare_output(
            "impact",
            lambda: conn.execute(q_get_impact),
            ModelImpact,
            **output_types,
        )
        declare_output(
            "institute", lambda: conn.execute(q_get_institutes), None, **output_types
        )
        declare_output("user", lambda: conn.execute(q_get_users), None, **output_types)


if __name__ == "__main__":
    main()
