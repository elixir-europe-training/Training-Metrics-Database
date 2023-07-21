SELECT uid                                           AS entity_id,
       IF(created = 0, NULL, FROM_UNIXTIME(created)) AS f_ts_created,
       IF(access = 0, NULL, FROM_UNIXTIME(access))   AS f_ts_access,
       IF(login = 0, NULL, FROM_UNIXTIME(login))     AS f_ts_login,
       name                                          AS f_name,
       mail                                          AS f_email,
       pass                                          AS f_hashed_password,
       COALESCE((SELECT JSON_ARRAYAGG(g.title)
                 FROM group_membership
                          INNER JOIN `groups` g ON group_membership.gid = g.gid
                 WHERE group_membership.status = 'active'
                   AND group_membership.uid = users.uid),
                JSON_ARRAY())                        AS f_nodes
FROM users
WHERE status = 1;