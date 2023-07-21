WITH _Entity AS (SELECT entity_id,
                        e_title,
                        e_created,
                        e_changed,
                        e_uid,
                        field_elixir_node_target_id            AS field_elixir_node,
                        field_date_value                       AS field_date__start,
                        field_date_value2                      AS field_date__end,
                        field_duration_value                   AS field_duration,
                        field_event_type_tid                   AS field_event_type,
                        field_funding_tid                      AS field_funding,
                        field_organizing_institution_value     AS field_organizing_institution,
                        field_city_value                       AS field_city,
                        field_country_tid                      AS field_country,
                        field_excelerate_subtask_target__tid   AS field_excelerate_subtask_target,
                        field_target_audience_tid              AS field_target_audience,
                        field_elixir_service_platforms_r_tid   AS field_elixir_service_platforms_r,
                        field_communities_use_cases_rela_tid   AS field_communities_use_cases_rela,
                        field_delegates_value                  AS field_delegates,
                        field_number_of_trainers_facilit_value AS field_number_of_trainers_facilit,
                        field_url_to_event_page_agenda_url     AS field_url_to_event_page_agenda,
                        field_stf_no_of_completed_feedba_value AS field_stf_no_of_completed_feedba,
                        field_ltf_no_of_completed_feedba_value AS field_ltf_no_of_completed_feedba,
                        field_notes_value                      AS field_notes,
                        field_upload_status_value              AS field_upload_status,
                        field_no_of_demographic_entries_value  AS field_no_of_demographic_entries,
                        ttd1.name                              AS r_event_type,
                        ttd2.name                              AS r_funding,
                        ttd3.name                              AS r_country,
                        ttd4.name                              AS r_excelerate_subtask_target,
                        ttd5.name                              AS r_target_audience,
                        ttd6.name                              AS r_elixir_service_platforms_r,
                        ttd7.name                              AS r_communities_use_cases_rela,
                        g_node.title                           AS group_elixir_node,
                        g_user.title                           AS group_user
                 FROM (SELECT node.nid     AS entity_id,
                              'node'       AS entity_type,
                              'event'      AS bundle,
                              '0'          AS deleted,
                              node.title   AS e_title,
                              node.created AS e_created,
                              node.changed AS e_changed,
                              node.uid     AS e_uid
                       FROM node
                       WHERE type = 'event') _Entity_Local
                          LEFT JOIN field_data_field_elixir_node USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_date USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_duration USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_event_type USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_funding USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_organizing_institution
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_city USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_country USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_excelerate_subtask_target_
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_target_audience USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_elixir_service_platforms_r
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_communities_use_cases_rela
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_delegates USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_number_of_trainers_facilit
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_url_to_event_page_agenda
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_stf_no_of_completed_feedba
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_ltf_no_of_completed_feedba
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_notes USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_upload_status USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN field_data_field_no_of_demographic_entries
                                    USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN taxonomy_term_data ttd1 ON ttd1.tid = field_event_type_tid
                          LEFT JOIN taxonomy_term_data ttd2 ON ttd2.tid = field_funding_tid
                          LEFT JOIN taxonomy_term_data ttd3 ON ttd3.tid = field_country_tid
                          LEFT JOIN taxonomy_term_data ttd4 ON ttd4.tid = field_excelerate_subtask_target__tid
                          LEFT JOIN taxonomy_term_data ttd5 ON ttd5.tid = field_target_audience_tid
                          LEFT JOIN taxonomy_term_data ttd6 ON ttd6.tid = field_elixir_service_platforms_r_tid
                          LEFT JOIN taxonomy_term_data ttd7 ON ttd7.tid = field_communities_use_cases_rela_tid
                          LEFT JOIN `groups` g_node ON g_node.gid = field_elixir_node_target_id
                          LEFT JOIN group_membership gm_user ON gm_user.uid = e_uid AND gm_user.status = 'active'
                          LEFT JOIN `groups` g_user ON g_user.gid = gm_user.gid),
     _Full AS (SELECT entity_id,
                      FROM_UNIXTIME(e_created)                             AS f_created,
                      FROM_UNIXTIME(e_changed)                             AS f_changed,
                      e_uid                                                AS f_created_by,
                      e_title                                              AS f_title,
                      JSON_ARRAYAGG(DISTINCT group_elixir_node)            AS f_elixir_node,
                      JSON_ARRAYAGG(DISTINCT group_user)                   AS f_elixir_node_user,
                      field_date__start                                    AS f_date_start,
                      field_date__end                                      AS f_date_end,
                      field_duration                                       AS f_duration,
                      r_event_type                                         AS f_event_type,
                      JSON_ARRAYAGG(DISTINCT r_funding)                    AS f_funding,
                      field_organizing_institution                         AS f_organizing_institution,
                      field_city                                           AS f_city,
                      r_country                                            AS f_country,
                      JSON_ARRAYAGG(DISTINCT r_excelerate_subtask_target)  AS f_excelerate_subtask_target,
                      JSON_ARRAYAGG(DISTINCT r_target_audience)            AS f_target_audience,
                      JSON_ARRAYAGG(DISTINCT r_elixir_service_platforms_r) AS f_elixir_service_platforms_r,
                      JSON_ARRAYAGG(DISTINCT r_communities_use_cases_rela) AS f_communities_use_cases_rela,
                      field_delegates                                      AS f_delegates,
                      field_number_of_trainers_facilit                     AS f_number_of_trainers_facilit,
                      field_url_to_event_page_agenda                       AS f_url_to_event_page_agenda,
                      field_stf_no_of_completed_feedba                     AS f_stf_no_of_completed_feedba,
                      field_ltf_no_of_completed_feedba                     AS f_ltf_no_of_completed_feedba,
                      field_notes                                          AS f_notes,
                      field_upload_status                                  AS f_upload_status,
                      field_no_of_demographic_entries                      AS f_no_of_demographic_entries
               FROM _Entity
               GROUP BY entity_id)
SELECT *
FROM _Full;