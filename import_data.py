import json
from app import app, db
from models import Material

def import_materials(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        materials_data = json.load(f)
    
    with app.app_context():
        for item in materials_data:
            material = Material(
                name=item.get('name'),
                category=item.get('category'),
                quantity=str(item.get('quantity', '')),
                location=item.get('location'),
                price_per_unit=float(item.get('price_per_unit', 0)),
                available=bool(item.get('available', True)),
                seller=item.get('seller', 'Unknown')
            )
            db.session.add(material)
        db.session.commit()
    print(f"Imported {len(materials_data)} materials successfully.")

if __name__ == '__main__':
    import_materials('dataset/materials.json')
