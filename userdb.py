# User database abstractions

import psycopg2
from common import tzPrint

class UserDatabase:
    def __init__(self, connstr):
        '''
        Sets up the PostgreSQL connection to be used by this instance.
        '''
        self.db = psycopg2.connect(connstr)
        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS userdata (
            guild_id BIGINT,
            user_id BIGINT,
            zone TEXT NOT NULL,
            last_active TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (guild_id, user_id)
            )""")
        self.db.commit()
        cur.close()

    def update_activity(self, serverid : str, authorid : str):
        '''
        If a user exists in the database, updates their last activity timestamp.
        '''
        c = self.db.cursor()
        c.execute("""
            UPDATE userdata SET last_active = now()
            WHERE guild_id = %s AND user_id = %s
        """, (serverid, authorid))
        self.db.commit()
        c.close()

    def delete_user(self, serverid : str, authorid : str):
        '''
        Deletes existing user from the database.
        '''
        c = self.db.cursor()
        c.execute("""
            DELETE FROM userdata
            WHERE guild_id = %s AND user_id = %s
        """, (serverid, authorid))
        self.db.commit()
        c.close()

    def update_user(self, serverid : str, authorid : str, zone : str):
        '''
        Insert or update user in the database.
        Does not do any sanitizing of incoming values, as only a small set of
        values are allowed anyway. This is enforced by the caller.
        '''
        self.delete_user(serverid, authorid)
        c = self.db.cursor()
        c.execute("""
            INSERT INTO userdata (guild_id, user_id, zone) VALUES
            (%s, %s, %s)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET zone = EXCLUDED.zone
        """, (serverid, authorid, zone))
        self.db.commit()
        c.close()

    def get_user(self, serverid, userid):
        '''
        Retrieves the time zone name of a single user.
        '''
        c = self.db.cursor()
        c.execute("""
        SELECT zone FROM userdata
        WHERE guild_id = %s and user_id = %s
        """, (serverid, userid))
        result = c.fetchone()
        c.close()
        if result is None: return None
        return result[0]

    def get_users(self, serverid):
        """
        Retrieves all user time zones for all recently active members.
        Users not present are not filtered here. Must be handled by the caller.
        Returns a dictionary of lists - Key is formatted zone, value is list of users represented.
        """
        c = self.db.cursor()
        c.execute("""
        SELECT zone, user_id
            FROM userdata
        WHERE
            last_active >= now() - INTERVAL '30 DAYS' -- only users active in the last 30 days
            AND guild_id = %(guild)s
            AND zone in (SELECT zone from (
                SELECT zone, count(*) as ct
                FROM userdata
                WHERE
                    guild_id = %(guild)s
                    AND last_active >= now() - INTERVAL '30 DAYS'
                GROUP BY zone
                LIMIT 20
            ) as pop_zones)
            ORDER BY RANDOM() -- Randomize display order (expected by consumer)
        """, {'guild': serverid})
        result = {}
        for row in c:
            resultrow = tzPrint(row[0])
            result[resultrow] = result.get(resultrow, list())
            result[resultrow].append(row[1])
        c.close()
        return result

    def get_unique_tz_count(self):
        '''
        Gets the number of unique time zones in the database.
        '''
        c = self.db.cursor()
        c.execute('SELECT COUNT(DISTINCT zone) FROM userdata')
        result = c.fetchall()
        c.close()
        return result[0][0]