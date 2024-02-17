import sqlite3
import datetime

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
                points INTEGER DEFAULT 0
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

        # Create the betting_events table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS betting_events (
                guild_id INTEGER,
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team1 TEXT,
                team2 TEXT,
                odds1 REAL,
                odds2 REAL,
                winner TEXT,
                betting_end_time TEXT,
                FOREIGN KEY (guild_id) REFERENCES user_points (user_id)
            )
        ''')

        # Create the bets table (formerly user_bets)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bets (
                guild_id INTEGER,
                event_id INTEGER,
                user_id INTEGER,
                chosen_team TEXT,
                amount INTEGER,
                PRIMARY KEY (guild_id, event_id, user_id),
                FOREIGN KEY (guild_id, event_id) REFERENCES betting_events (guild_id, event_id),
                FOREIGN KEY (user_id) REFERENCES user_points (user_id)
            )
        ''')
        
        self.close()

    def get_user_points(self, user_id):
        self.connect()

        # Check if the user exists in the user_points table
        self.cursor.execute('SELECT points FROM user_points WHERE user_id = ?', (user_id,))
        user_points = self.cursor.fetchone()

        # If the user doesn't exist, create a new user entry with points initialized to 0
        if not user_points:
            self.cursor.execute('INSERT INTO user_points (user_id, points) VALUES (?, ?)', (user_id, 100))
            print(f"User with ID {user_id} created in user_points table with 100 points.")
            user_points = (100,)  # Set user_points to (0,) to avoid NoneType issues

        # Close the connection
        self.close()

        return user_points[0]  # Return points as a single value

    def add_user_points(self, user_id, challenge_id):
        self.connect()

        # Insert user points into the user_points table
        self.cursor.execute('INSERT INTO user_points (user_id, challenge_id) VALUES (?, ?)', (user_id, challenge_id))

        # Close the connection
        self.close()

    def update_user_points(self, user_id, points_change):
        # Retrieve the current points of the user
        current_points = self.get_user_points(user_id)

        self.connect()
        # Calculate the new points after the change
        new_points = max(0, current_points + points_change)  # Ensure the user cannot have negative points

        # Update the user's points in the user_points table
        self.cursor.execute('''
            REPLACE INTO user_points (user_id, points)
            VALUES (?, ?)
        ''', (user_id, new_points))

        # Commit the changes and close the connection
        self.close()

    def get_top_users(self, limit=20):
        self.connect()

        # Retrieve top users based on points
        self.cursor.execute('''
            SELECT user_id, points
            FROM user_points
            ORDER BY points DESC
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
            self.cursor.execute('UPDATE user_points SET points = points + ? WHERE user_id = ?', (challenge_points, user_id))

            print(f"Challenge with ID {challenge_id} completed by user {user_id}.")
        except Exception as e:
            print(f"Error completing challenge: {e}")
        finally:
            self.close()

    # BETTING AND EVENTS #
    
    def create_event(self, guild_id, team1, team2, odds1, odds2, betting_end_time):
        self.connect()

        # Insert the new event into the betting_events table
        self.cursor.execute('''
            INSERT INTO betting_events (guild_id, team1, team2, odds1, odds2, winner, betting_end_time)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
        ''', (guild_id, team1, team2, odds1, odds2, betting_end_time))

        # Get the last inserted row ID, which is the auto-incremented event_id
        event_id = self.cursor.lastrowid

        # Commit the changes and close the connection
        self.close()

        return event_id

    def place_bet(self, guild_id, event_id, user_id, team, amount):
        self.connect()

        # Insert a new bet into the bets table
        self.cursor.execute('''
            INSERT INTO bets (guild_id, event_id, user_id, chosen_team, amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, event_id, user_id, team, amount))

        self.close()

    def get_betting_end_time(self, guild_id, event_id):
        self.connect()

        # Retrieve the betting end time for the specified event
        self.cursor.execute('''
            SELECT betting_end_time
            FROM betting_events
            WHERE guild_id = ? AND event_id = ?
        ''', (guild_id, event_id))

        betting_end_time = self.cursor.fetchone()[0]

        # Close the connection
        self.close()
        return datetime.datetime.strptime(betting_end_time, "%Y-%m-%d %H:%M:%S.%f")
    
    def get_event_details(self, guild_id, event_id):
        self.connect()

        # Retrieve event details from the betting_events table
        self.cursor.execute('''
            SELECT team1, team2, odds1, odds2, betting_end_time
            FROM betting_events
            WHERE guild_id = ? AND event_id = ?
        ''', (guild_id, event_id))

        event_details = self.cursor.fetchone()

        # Close the connection
        self.close()

        if event_details:
            # Convert the betting_end_time to a formatted string
            event_details = {
                'team1': event_details[0],
                'team2': event_details[1],
                'odds1': event_details[2],
                'odds2': event_details[3],
                'betting_end_time': int(datetime.datetime.strptime(event_details[4], "%Y-%m-%d %H:%M:%S.%f").timestamp())
            }
            return event_details
        else:
            return None

    def is_event_id_unique(self, guild_id, event_id):
        self.connect()

        # Check if the event ID is unique for the guild
        self.cursor.execute('''
            SELECT 1
            FROM betting_events
            WHERE guild_id = ? AND event_id = ?
        ''', (guild_id, event_id))

        is_unique = not bool(self.cursor.fetchone())

        # Close the connection
        self.close()

        return is_unique

    def is_event_active(self, guild_id, event_id):
        self.connect()

        # Check if the event is still active based on the betting_events table
        self.cursor.execute('''
            SELECT 1
            FROM betting_events
            WHERE guild_id = ? AND event_id = ? AND winner IS NULL
        ''', (guild_id, event_id))

        is_active = bool(self.cursor.fetchone())

        # Close the connection
        self.close()

        return is_active
    
    def get_active_events(self, guild_id):
        self.connect()

        # Retrieve active events from the betting_events table
        self.cursor.execute('''
            SELECT event_id, team1, team2, odds1, odds2, betting_end_time
            FROM betting_events
            WHERE guild_id = ? AND winner IS NULL
        ''', (guild_id,))

        active_events = self.cursor.fetchall()

        # Close the connection
        self.close()

        return active_events

    def is_valid_team(self, guild_id, event_id, chosen_team):
        self.connect()

        # Check if the chosen team is valid for the given event
        self.cursor.execute('''
            SELECT 1
            FROM betting_events
            WHERE guild_id = ? AND event_id = ? AND (team1 COLLATE NOCASE = ? OR team2 COLLATE NOCASE = ?)
        ''', (guild_id, event_id, chosen_team, chosen_team))

        is_valid = bool(self.cursor.fetchone())

        # Close the connection
        self.close()

        return is_valid
    
    # Inside the ChallengesDatabase class
    def is_event_ended(self, guild_id, event_id):
        self.connect()

        # Check if the event is already marked as ended in the betting_events table
        self.cursor.execute('''
            SELECT 1
            FROM betting_events
            WHERE guild_id = ? AND event_id = ? AND winner IS NOT NULL
        ''', (guild_id, event_id))

        is_ended = bool(self.cursor.fetchone())

        # Close the connection
        self.close()

        return is_ended

    def calculate_payouts(self, guild_id, event_id, winner_team):
        self.connect()

        # Retrieve winning odds from the betting_events table
        self.cursor.execute('''
            SELECT odds1,odds2, team1
            FROM betting_events
            WHERE guild_id = ? AND event_id = ?
        ''', (guild_id, event_id))

        query_result = self.cursor.fetchone()
        winning_odds = query_result[0] if winner_team.lower() == query_result[2].lower() else query_result[1]

        print("winning odds", winning_odds)

        # Get bets for the winning team from the bets table
        self.cursor.execute('''
            SELECT user_id, amount
            FROM bets
            WHERE guild_id = ? AND event_id = ? AND chosen_team COLLATE NOCASE = ?
        ''', (guild_id, event_id, winner_team))

        winning_bets = {user_id: amount for user_id, amount in self.cursor.fetchall()}
        print(winning_bets)

        # Close the connection
        self.close()

        return winning_odds, winning_bets

    def mark_event_as_ended(self, guild_id, event_id, winner_team):
        self.connect()

        # Update the winner column in the betting_events table
        self.cursor.execute('''
            UPDATE betting_events
            SET winner = ?
            WHERE guild_id = ? AND event_id = ?
        ''', (winner_team, guild_id, event_id))

        # Commit the changes and close the connection
        self.close()

    def get_bets_for_team(self, guild_id, event_id, chosen_team):
        self.connect()

        # Retrieve user bets for the chosen team from the bets table
        self.cursor.execute('''
            SELECT user_id, amount
            FROM bets
            WHERE guild_id = ? AND event_id = ? AND chosen_team COLLATE NOCASE = ?
        ''', (guild_id, event_id, chosen_team))

        team_bets = self.cursor.fetchall()

        # Close the connection
        self.close()

        return team_bets
    
    def get_all_events(self, guild_id):
        self.connect()

        # Retrieve all events from the betting_events table
        self.cursor.execute('''
            SELECT event_id, team1, team2, odds1, odds2
            FROM betting_events
            WHERE guild_id = ?
        ''', (guild_id,))

        events = self.cursor.fetchall()

        # Close the connection
        self.close()

        return events