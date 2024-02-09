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
                user_id INTEGER,
                challenge_id INTEGER,
                FOREIGN KEY(challenge_id) REFERENCES challenges(id),
                PRIMARY KEY (user_id, challenge_id)
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

        self.close()

    def get_user_points(self, user_id):
        self.connect()

        # Check if the user exists in the user_points table
        self.cursor.execute('SELECT COUNT(*) FROM user_points WHERE user_id = ?', (user_id,))
        user_exists = self.cursor.fetchone()[0] > 0

        # If the user doesn't exist, create a new user entry
        if not user_exists:
            self.cursor.execute('INSERT INTO user_points (user_id) VALUES (?)', (user_id,))
            print(f"User with ID {user_id} created in user_points table.")

        # Retrieve user points from the user_points table
        self.cursor.execute('SELECT challenge_id FROM user_points WHERE user_id = ?', (user_id,))
        user_points = self.cursor.fetchall()

        # Close the connection
        self.close()

        return user_points

    def add_user_points(self, user_id, challenge_id):
        self.connect()

        # Insert user points into the user_points table
        self.cursor.execute('INSERT INTO user_points (user_id, challenge_id) VALUES (?, ?)', (user_id, challenge_id))

        # Close the connection
        self.close()

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

    def get_completed_challenges(self, user_id):
        self.connect()
        # Retrieve completed challenges for a specific user
        self.cursor.execute('SELECT challenge_id FROM completed_challenges WHERE user_id = ?', (user_id,))
        completed_challenges = self.cursor.fetchall()
        self.close()
        return completed_challenges

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

            print(f"Challenge with ID {challenge_id} completed by user {user_id}.")
        except Exception as e:
            print(f"Error completing challenge: {e}")
        finally:
            self.close()