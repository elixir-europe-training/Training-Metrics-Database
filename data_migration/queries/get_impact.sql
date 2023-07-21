WITH _Entity AS (SELECT entity_id,
                        e_title                                AS f_title,
                        FROM_UNIXTIME(e_created)               AS f_created,
                        FROM_UNIXTIME(e_changed)               AS f_changed,
                        field_event_target_id                  AS f_event,
                        field_created_by_target_id             AS f_created_by,
                        field_how_long_ago_value               AS f_how_long_ago,
                        field_what_was_your_main_reason_value  AS f_what_was_your_main_reason,
                        field_how_often_did_you_use_tool_value AS f_how_often_did_you_use_tool,
                        field_how_often_do_you_use_after_value AS f_how_often_do_you_use_after,
                        field_do_you_feel_explain_value        AS f_do_you_feel_explain,
                        field_are_you_now_able_value           AS f_are_you_now_able,
                        JSON_ARRAYAGG(DISTINCT ttd1.name)      AS f_how_did_it_help,
                        JSON_ARRAYAGG(DISTINCT ttd2.name)      AS f_facilitated,
                        field_how_many_people_you_shared_value AS f_how_many_people_you_shared,
                        field_would_you_recommend_value        AS f_would_you_recommend
                 FROM (SELECT eck_custom_entities.id      AS entity_id,
                              'custom_entities'           AS entity_type,
                              'impact_metrics'            AS bundle,
                              '0'                         AS deleted,
                              eck_custom_entities.title   AS e_title,
                              eck_custom_entities.created AS e_created,
                              eck_custom_entities.changed AS e_changed
                       FROM eck_custom_entities
                       WHERE type = 'impact_metrics') _Entity_Local
                          LEFT JOIN field_data_field_event
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_created_by USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_how_long_ago USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_what_was_your_main_reason
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_how_often_did_you_use_tool
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_how_often_do_you_use_after
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_do_you_feel_explain USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_are_you_now_able USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_how_did_it_help USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_facilitated USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_how_many_people_you_shared
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_would_you_recommend USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN taxonomy_term_data ttd1 ON ttd1.tid = field_how_did_it_help_target_id
                          LEFT JOIN taxonomy_term_data ttd2 ON ttd2.tid = field_facilitated_target_id
                 GROUP BY entity_id)
SELECT *
FROM _Entity;
