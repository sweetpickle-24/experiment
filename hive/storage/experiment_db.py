"""
SQLite storage for experiments, events, and evolutionary lineage.
Logs system behavior for analysis (not used as memory - that's wave-based).
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class ExperimentStorage:
    """
    SQLite database for logging experiments, events, and lineage.
    This is for ANALYSIS, not memory (memory is wave-based).
    """
    
    def __init__(self, db_path: str = "data/experiments.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create all tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_time REAL,
                end_time REAL,
                config_json TEXT,
                final_fitness REAL
            )
        ''')
        
        # System events (hive birth/death, state transitions, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                timestamp REAL,
                event_type TEXT,
                event_data_json TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Hive lifecycle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hive_lifecycle (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                hive_id INTEGER,
                event_type TEXT,
                timestamp REAL,
                size INTEGER,
                coherence REAL,
                lifespan REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Consciousness state transitions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consciousness_transitions (
                transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                timestamp REAL,
                from_state TEXT,
                to_state TEXT,
                duration_in_prev_state REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Mutation lineage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mutations (
                mutation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                generation INTEGER,
                mutation_type TEXT,
                target_count INTEGER,
                timestamp REAL,
                fitness_before REAL,
                fitness_after REAL,
                kept BOOLEAN,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Thought patterns discovered
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thought_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                pattern_type TEXT,
                complexity INTEGER,
                activation_count INTEGER,
                birth_time REAL,
                hive_sequence_json TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        # Performance metrics snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                timestamp REAL,
                global_coherence REAL,
                dominant_frequency REAL,
                num_hives INTEGER,
                total_energy REAL,
                consciousness_state TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
            )
        ''')
        
        self.conn.commit()
    
    def start_experiment(self, name: str, description: str, 
                        config: dict, start_time: float) -> int:
        """Start new experiment, return experiment_id."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO experiments (name, description, start_time, config_json)
            VALUES (?, ?, ?, ?)
        ''', (name, description, start_time, json.dumps(config)))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def end_experiment(self, experiment_id: int, end_time: float, 
                      final_fitness: float):
        """Mark experiment as complete."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE experiments 
            SET end_time = ?, final_fitness = ?
            WHERE experiment_id = ?
        ''', (end_time, final_fitness, experiment_id))
        
        self.conn.commit()
    
    def log_event(self, experiment_id: int, timestamp: float,
                 event_type: str, event_data: dict):
        """Log general system event."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO events (experiment_id, timestamp, event_type, event_data_json)
            VALUES (?, ?, ?, ?)
        ''', (experiment_id, timestamp, event_type, json.dumps(event_data)))
        
        self.conn.commit()
    
    def log_hive_event(self, experiment_id: int, hive_id: int,
                      event_type: str, timestamp: float,
                      size: int = 0, coherence: float = 0.0,
                      lifespan: float = 0.0):
        """Log hive lifecycle event (birth, death, merge, split)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO hive_lifecycle 
            (experiment_id, hive_id, event_type, timestamp, size, coherence, lifespan)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (experiment_id, hive_id, event_type, timestamp, size, coherence, lifespan))
        
        self.conn.commit()
    
    def log_consciousness_transition(self, experiment_id: int, timestamp: float,
                                    from_state: str, to_state: str,
                                    duration: float):
        """Log consciousness state transition."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO consciousness_transitions
            (experiment_id, timestamp, from_state, to_state, duration_in_prev_state)
            VALUES (?, ?, ?, ?, ?)
        ''', (experiment_id, timestamp, from_state, to_state, duration))
        
        self.conn.commit()
    
    def log_mutation(self, experiment_id: int, generation: int,
                    mutation_type: str, target_count: int,
                    timestamp: float, fitness_before: float,
                    fitness_after: float, kept: bool):
        """Log evolutionary mutation."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO mutations
            (experiment_id, generation, mutation_type, target_count, 
             timestamp, fitness_before, fitness_after, kept)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (experiment_id, generation, mutation_type, target_count,
              timestamp, fitness_before, fitness_after, kept))
        
        self.conn.commit()
    
    def log_thought_pattern(self, experiment_id: int, pattern_type: str,
                           complexity: int, activation_count: int,
                           birth_time: float, hive_sequence: List[int]):
        """Log discovered thought pattern."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO thought_patterns
            (experiment_id, pattern_type, complexity, activation_count, 
             birth_time, hive_sequence_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (experiment_id, pattern_type, complexity, activation_count,
              birth_time, json.dumps(hive_sequence)))
        
        self.conn.commit()
    
    def log_metrics_snapshot(self, experiment_id: int, timestamp: float,
                            metrics: dict):
        """Log performance metrics snapshot."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO metrics_snapshots
            (experiment_id, timestamp, global_coherence, dominant_frequency,
             num_hives, total_energy, consciousness_state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (experiment_id, timestamp, 
              metrics.get('global_coherence', 0.0),
              metrics.get('dominant_frequency', 0.0),
              metrics.get('num_hives', 0),
              metrics.get('energy', 0.0),
              metrics.get('consciousness_state', 'WAKE')))
        
        self.conn.commit()
    
    def get_experiment_summary(self, experiment_id: int) -> Optional[dict]:
        """Get summary of experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM experiments WHERE experiment_id = ?
        ''', (experiment_id,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        return dict(row)
    
    def get_mutation_lineage(self, experiment_id: int) -> List[dict]:
        """Get complete mutation history for experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM mutations 
            WHERE experiment_id = ?
            ORDER BY generation, timestamp
        ''', (experiment_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_thought_patterns_discovered(self, experiment_id: int) -> List[dict]:
        """Get all thought patterns discovered in experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM thought_patterns
            WHERE experiment_id = ?
            ORDER BY activation_count DESC
        ''', (experiment_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        self.conn.close()
