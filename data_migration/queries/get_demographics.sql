WITH _Entity AS (SELECT entity_id,
                        e_title                                AS f_title,
                        FROM_UNIXTIME(e_created)               AS f_created,
                        FROM_UNIXTIME(e_changed)               AS f_changed,
                        field_event_target_id                  AS f_event,
                        field_where_you_hear_about_cours_value AS f_where_you_hear_about_cours,
                        field_employment_sector_value          AS f_employment_sector,
                        ttd1.name                              AS f_country,
                        field_gender_value                     AS f_gender,
                        field_career_stage_value               AS f_career_stage,
                        field_created_by_target_id             AS f_created_by
                 FROM (SELECT eck_custom_entities.id      AS entity_id,
                              'custom_entities'           AS entity_type,
                              'application'               AS bundle,
                              '0'                         AS deleted,
                              eck_custom_entities.title   AS e_title,
                              eck_custom_entities.created AS e_created,
                              eck_custom_entities.changed AS e_changed
                       FROM eck_custom_entities
                       WHERE type = 'application') _Entity_Local
                          LEFT JOIN field_data_field_event
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_where_you_hear_about_cours
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_employment_sector USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_country USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN taxonomy_term_data ttd1 ON ttd1.tid = field_country_tid
                          LEFT JOIN field_data_field_gender USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_career_stage USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_created_by USING (entity_id, entity_type, bundle, deleted))
SELECT *
FROM _Entity;
