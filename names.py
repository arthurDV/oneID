"""
Générateur de noms crédibles pour les agents.
"""
import random

FIRST_NAMES = [
    "Alex", "Jordan", "Morgan", "Taylor", "Casey", "Riley", "Jamie", "Avery",
    "Emma", "Liam", "Noah", "Olivia", "Lucas", "Mason", "Ethan", "Sophie",
    "Chloe", "Charlotte", "Amelia", "James", "Oliver", "William", "Benjamin",
    "Henry", "Alice", "Thomas", "Sarah", "Laura", "Paul", "Marie", "Lucas",
    "Hugo", "Camille", "Lea", "Nathan", "Mathis", "Manon", "Jade", "Tom"
]

LAST_NAMES = [
    "Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand",
    "Smith", "Johnson", "Williams", "Brown", "Garcia", "Miller", "Davis",
    "Wilson", "Anderson", "Moore", "Jackson", "White", "Harris", "Thompson",
    "Lewis", "Walker", "Hall", "Allen", "Clark", "Young", "King", "Wright",
    "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Nelson", "Carter"
]

def generate_name():
    """Retourne (prénom, nom) aléatoires."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return first, last
