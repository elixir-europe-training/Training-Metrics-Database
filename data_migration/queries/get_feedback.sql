WITH _Entity AS (SELECT entity_id,
                        e_title                                AS f_title,
                        FROM_UNIXTIME(e_created)               AS f_created,
                        FROM_UNIXTIME(e_changed)               AS f_changed,
                        field_event_target_id                  AS f_event,
                        field_have_you_used_the_tools_re_value AS f_have_you_used_the_tools,
                        field_will_you_use_the_resources_value AS f_will_you_use_the_resources,
                        field_would_you_recommend_the_co_value AS f_would_you_recommend,
                        field_overall_rating_for_the_cou_value AS f_overall_rating,
                        field_was_the_balance_of_materia_value AS f_balance_of_the_material,
                        field_may_we_contact_you_email_value   AS f_may_we_contact_you_email,
                        field_created_by_target_id             AS f_created_by,
                        ttd1.name                              AS f_delegate_type,
                        field_demographic_link_target_id       AS f_demographic_link
                 FROM (SELECT eck_custom_entities.id      AS entity_id,
                              'custom_entities'           AS entity_type,
                              'event_feedback'            AS bundle,
                              '0'                         AS deleted,
                              eck_custom_entities.title   AS e_title,
                              eck_custom_entities.created AS e_created,
                              eck_custom_entities.changed AS e_changed
                       FROM eck_custom_entities
                       WHERE type = 'event_feedback') _Entity_Local
                          LEFT JOIN field_data_field_event
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_have_you_used_the_tools_re
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_will_you_use_the_resources
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_would_you_recommend_the_co
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_overall_rating_for_the_cou
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_was_the_balance_of_materia
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_may_we_contact_you_email
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_created_by USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_delegate_type USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_demographic_link USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN taxonomy_term_data ttd1 ON ttd1.tid = field_delegate_type_tid)
SELECT *
FROM _Entity;
