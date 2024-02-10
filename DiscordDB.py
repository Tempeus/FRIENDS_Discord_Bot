import sqlite3

class DiscordDatabase:
    def __init__(self, db_name='discord.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def create_tables(self):
        self.connect()

        # Create challenges table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                points INTEGER NOT NULL,
                unique_challenge BOOLEAN NOT NULL
            )
        ''')

        # Create user_points table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_points (
                user_id INTEGER PRIMARY KEY,
                total_points INTEGER DEFAULT 0
            )
        ''')

        # Create completed_challenges table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS completed_challenges (
                user_id INTEGER,
                challenge_id INTEGER,
                completion_count INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES user_points(user_id),
                FOREIGN KEY(challenge_id) REFERENCES challenges(id),
                PRIMARY KEY (user_id, challenge_id, completion_count)
            )
        ''')

                # Create betting_events table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS betting_events (
                guild_id INTEGER,
                event_id INTEGER,
                team1 TEXT,
                team2 TEXT,
                PRIMARY KEY (guild_id, event_id)
            )
        ''')

        # Create bets table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                guild_id INTEGER,
                event_id INTEGER,
                user_id INTEGER,
                team TEXT,
                amount INTEGER,
                FOREIGN KEY (guild_id, event_id) REFERENCES betting_events(guild_id, event_id),
                PRIMARY KEY (guild_id, event_id, user_id)
            )
        ''')

        self.close()

    def get_user_points(self, user_id):
        self.connect()

        # Check if the user exists in the user_points table
        self.cursor.execute('SELECT total_points FROM user_points WHERE user_id = ?', (user_id,))
        user_points = self.cursor.fetchone()

        # If the user doesn't exist, create a new user entry with points initialized to 0
        if not user_points:
            self.cursor.execute('INSERT INTO user_points (user_id, total_points) VALUES (?, ?)', (user_id, 0))
            print(f"User with ID {user_id} created in user_points table with 0 points.")
            user_points = (0,)  # Set user_points to (0,) to avoid NoneType issues

        # Close the connection
        self.close()

        return user_points[0]  # Return total_points as a single value

    def add_user_points(self, user_id, challenge_id):
        self.connect()

        # Insert user points into the user_points table
        self.cursor.execute('INSERT INTO user_points (user_id, challenge_id) VALUES (?, ?)', (user_id, challenge_id))

        # Close the connection
        self.close()

    def update_user_points(self, user_id, points_change):
        self.connect()

        # Retrieve the current points of the user
        current_points = self.get_user_points(user_id)

        # Calculate the new points after the change
        new_points = max(0, current_points + points_change)  # Ensure the user cannot have negative points

        # Update the user's points in the user_points table
        self.cursor.execute('''
            REPLACE INTO user_points (user_id, points)
            VALUES (?, ?)
        ''', (user_id, new_points))

        # Commit the changes and close the connection
        self.close()

    def get_top_users(self, limit=10):
        self.connect()

        # Retrieve top users based on points
        self.cursor.execute('''
            SELECT user_id, total_points
            FROM user_points
            ORDER BY total_points DESC
            LIMIT ?
        ''', (limit,))

        top_users = self.cursor.fetchall()

        # Close the connection
        self.close()

        return top_users

    def add_challenge(self, name, points, unique_challenge=True):
        self.connect()
        try:
            # Insert a new challenge into the challenges table
            self.cursor.execute('INSERT INTO challenges (name, points, unique_challenge) VALUES (?, ?, ?)', (name, points, unique_challenge))
            print(f"Challenge '{name}' with {points} points added successfully.")
        except Exception as e:
            print(f"Error adding challenge: {e}")
        finally:
            self.close()

    def get_challenges(self):
        self.connect()
        # Retrieve challenges from the challenges table
        self.cursor.execute('SELECT id, name, points, unique_challenge FROM challenges')
        challenges = self.cursor.fetchall()
        self.close()
        return challenges
    
    def get_completed_challenges(self):
        self.connect()

        # Retrieve completed challenges with user IDs, challenge IDs, and completion counts
        self.cursor.execute('''
            SELECT user_id, challenge_id, completion_count
            FROM completed_challenges
        ''')

        completed_challenges_list = self.cursor.fetchall()

        # Close the connection
        self.close()

        return completed_challenges_list
    
    def get_challenge_info(self, challenge_id):
        self.connect()

        # Retrieve challenge information based on the challenge ID
        self.cursor.execute('''
            SELECT name, points, unique_challenge
            FROM challenges
            WHERE id = ?
        ''', (challenge_id,))

        challenge_info = self.cursor.fetchone()

        # Close the connection
        self.close()

        if challenge_info:
            return {'name': challenge_info[0], 'points': challenge_info[1], 'unique_challenge': bool(challenge_info[2])}
        else:
            return None

    def complete_challenge(self, user_id, challenge_id):
        self.connect()
        try:
            # Check if the challenge is unique or can be completed multiple times
            self.cursor.execute('SELECT unique_challenge FROM challenges WHERE id = ?', (challenge_id,))
            unique_challenge = self.cursor.fetchone()[0]

            # Update completion count for unique challenges or insert a new record for non-unique challenges
            if unique_challenge:
                self.cursor.execute('UPDATE completed_challenges SET completion_count = completion_count + 1 WHERE user_id = ? AND challenge_id = ?', (user_id, challenge_id))
            else:
                self.cursor.execute('INSERT INTO completed_challenges (user_id, challenge_id) VALUES (?, ?)', (user_id, challenge_id))

            # Update user points based on the challenge points
            self.cursor.execute('SELECT points FROM challenges WHERE id = ?', (challenge_id,))
            challenge_points = self.cursor.fetchone()[0]
            self.cursor.execute('UPDATE user_points SET total_points = total_points + ? WHERE user_id = ?', (challenge_points, user_id))

            print(f"Challenge with ID {challenge_id} completed by user {user_id}.")
        except Exception as e:
            print(f"Error completing challenge: {e}")
        finally:
            self.close()

    # BETTING AND EVENTS #
    
    def create_event(self, guild_id, event_id, team1, team2):
        self.connect()

        # Insert a new betting event into the betting_events table
        self.cursor.execute('''
            INSERT INTO betting_events (guild_id, event_id, team1, team2)
            VALUES (?, ?, ?, ?)
        ''', (guild_id, event_id, team1, team2))

        self.close()

    def place_bet(self, guild_id, event_id, user_id, team, amount):
        self.connect()

        # Insert a new bet into the bets table
        self.cursor.execute('''
            INSERT INTO bets (guild_id, event_id, user_id, team, amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, event_id, user_id, team, amount))

        self.close()