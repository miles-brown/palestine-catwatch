"""
Seed script to populate the Equipment reference table with UK police equipment types.
Run with: python seed_equipment.py
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, Equipment

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Equipment data organized by category
EQUIPMENT_DATA = [
    # Defensive Equipment
    {"name": "Round Shield", "category": "defensive", "description": "Small circular riot shield for close quarters protection"},
    {"name": "Long Shield", "category": "defensive", "description": "Full-length rectangular riot shield providing maximum coverage"},
    {"name": "NATO Helmet", "category": "defensive", "description": "Military-style protective helmet with visor, used by specialist units"},
    {"name": "Standard Helmet", "category": "defensive", "description": "Standard police protective helmet"},
    {"name": "Riot Helmet", "category": "defensive", "description": "Helmet with full face visor for public order situations"},
    {"name": "Body Armor", "category": "defensive", "description": "Protective vest worn under or over uniform"},
    {"name": "Arm Guards", "category": "defensive", "description": "Forearm protection for public order situations"},
    {"name": "Leg Guards", "category": "defensive", "description": "Shin/leg protection for public order situations"},
    {"name": "Flame Retardant Overalls", "category": "defensive", "description": "Fire-resistant outer garment for high-risk situations"},

    # Offensive Equipment
    {"name": "Standard Baton", "category": "offensive", "description": "Fixed-length police baton"},
    {"name": "Extendable Baton", "category": "offensive", "description": "Collapsible ASP-style baton"},
    {"name": "Long Baton", "category": "offensive", "description": "Extended reach baton for public order situations"},
    {"name": "Taser", "category": "offensive", "description": "Conducted Energy Device (X26 or X2 model)"},
    {"name": "CS Spray", "category": "offensive", "description": "Incapacitant spray (PAVA or CS)"},
    {"name": "Firearm", "category": "offensive", "description": "Armed response officer weapon"},

    # Restraint Equipment
    {"name": "Handcuffs", "category": "restraint", "description": "Standard police handcuffs"},
    {"name": "Rigid Cuffs", "category": "restraint", "description": "Rigid bar handcuffs for enhanced control"},
    {"name": "Zip Ties", "category": "restraint", "description": "Plastic cable tie restraints for mass arrests"},
    {"name": "Leg Restraints", "category": "restraint", "description": "Ankle restraints for violent prisoners"},

    # Identification Equipment
    {"name": "Body Worn Camera", "category": "identification", "description": "Body-mounted video camera for evidence capture"},
    {"name": "Shoulder Number", "category": "identification", "description": "Epaulette displaying officer identification number"},
    {"name": "Force ID Badge", "category": "identification", "description": "Badge or crest identifying police force"},
    {"name": "Rank Insignia", "category": "identification", "description": "Chevrons, pips, or crown indicating rank"},
    {"name": "Hi-Vis Jacket", "category": "identification", "description": "High visibility jacket with POLICE marking"},
    {"name": "Evidence Gatherer Vest", "category": "identification", "description": "Blue vest worn by Forward Intelligence Team officers"},
    {"name": "Medic Marking", "category": "identification", "description": "Cross or medic identification on uniform"},

    # Communication Equipment
    {"name": "Radio", "category": "communication", "description": "Airwave/Tetra police radio"},
    {"name": "Earpiece", "category": "communication", "description": "Covert communication earpiece"},
    {"name": "Public Address System", "category": "communication", "description": "Loudspeaker/megaphone for crowd communication"},

    # Specialist Equipment
    {"name": "K9 Unit Gear", "category": "specialist", "description": "Dog handler equipment and leash"},
    {"name": "Mounted Unit Gear", "category": "specialist", "description": "Horse-mounted officer equipment"},
    {"name": "Drone Controller", "category": "specialist", "description": "UAV control equipment for aerial surveillance"},
    {"name": "ANPR Equipment", "category": "specialist", "description": "Automatic Number Plate Recognition device"},
    {"name": "Facial Recognition Device", "category": "specialist", "description": "Mobile facial recognition technology"},
]


def seed_equipment():
    """Seed the equipment table with reference data"""
    db = SessionLocal()
    try:
        # Check if equipment already exists
        existing_count = db.query(Equipment).count()
        if existing_count > 0:
            print(f"Equipment table already has {existing_count} entries. Skipping seed.")
            return

        # Insert all equipment
        for item in EQUIPMENT_DATA:
            equipment = Equipment(
                name=item["name"],
                category=item["category"],
                description=item["description"]
            )
            db.add(equipment)

        db.commit()
        print(f"Successfully seeded {len(EQUIPMENT_DATA)} equipment items.")

        # Print summary by category
        categories = {}
        for item in EQUIPMENT_DATA:
            cat = item["category"]
            categories[cat] = categories.get(cat, 0) + 1

        print("\nEquipment by category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding equipment: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_equipment()
