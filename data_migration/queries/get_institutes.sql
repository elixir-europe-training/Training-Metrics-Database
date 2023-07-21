WITH _Entity AS (SELECT entity_id,
                        e_title                  AS f_title,
                        FROM_UNIXTIME(e_created) AS f_created,
                        FROM_UNIXTIME(e_changed) AS f_changed,
                        ttd1.name                AS f_location,
                        COALESCE((SELECT JSON_ARRAYAGG(g.title)
                                  FROM field_data_field_elixir_node n
                                           INNER JOIN
                                       `groups` g
                                       ON g.gid = n.field_elixir_node_target_id
                                  WHERE n.entity_id = _Entity_Local.entity_id
                                    AND n.entity_type = _Entity_Local.entity_type
                                    AND n.bundle = _Entity_Local.bundle
                                    AND n.deleted = _Entity_Local.deleted),
                                 JSON_ARRAY())   AS f_elixir_node
                 FROM (SELECT eck_custom_entities.id      AS entity_id,
                              'custom_entities'           AS entity_type,
                              'institute'                 AS bundle,
                              '0'                         AS deleted,
                              eck_custom_entities.title   AS e_title,
                              eck_custom_entities.created AS e_created,
                              eck_custom_entities.changed AS e_changed
                       FROM eck_custom_entities
                       WHERE type = 'institute') _Entity_Local
                          LEFT JOIN field_data_field_location USING (entity_id, entity_type, bundle, deleted)
                          LEFT JOIN taxonomy_term_data ttd1 ON ttd1.tid = field_location_tid
                 GROUP BY entity_id)
SELECT *
FROM _Entity;
